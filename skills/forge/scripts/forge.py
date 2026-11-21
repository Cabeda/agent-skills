#!/usr/bin/env python3
"""
One command for GitHub and Codeberg, with the code factory's rules enforced in code.

The factory skills call this instead of `gh` and curl, so the rules that must not
depend on a prompt live here: writes are a dry run until a repo opts in, only
trusted people's issues are returned for work, and a pull request merges only
when every gate passes.

    forge.py [--root DIR] repos
    forge.py [--root DIR] issues  TARGET
    forge.py [--root DIR] issue   TARGET NUMBER
    forge.py [--root DIR] prs     TARGET
    forge.py [--root DIR] check   TARGET NUMBER
    forge.py [--root DIR] comment TARGET NUMBER --body-file FILE
    forge.py [--root DIR] label   TARGET NUMBER NAME
    forge.py [--root DIR] open-pr TARGET --head BRANCH --base BRANCH --title T --body-file FILE
    forge.py [--root DIR] ready   TARGET NUMBER
    forge.py [--root DIR] merge   TARGET NUMBER --sha SHA
    forge.py [--root DIR] mark-reviewed TARGET NUMBER --sha SHA
    forge.py [--root DIR] push    TARGET --branch factory/NAME
    forge.py [--root DIR] find    TARGET --fingerprint TEXT
    forge.py [--root DIR] file    TARGET --title T --body-file FILE --fingerprint TEXT [--label L]...

TARGET is a path under the root, or github:owner/name, or codeberg:owner/name.
Every verb prints JSON. Exit 0 is success (a dry run included), 1 an error, 3 a
refusal by a rule.
"""

import argparse
import hashlib
import http.client
import json
import os
import re
import subprocess
import sys
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

SUPPORTED_HOSTS = {"github.com": "github", "codeberg.org": "codeberg"}
FACTORY_PREFIX = "factory/"
TRUSTED_PERMISSIONS = {"admin", "owner", "maintain", "write"}
WIP_PREFIXES = ("WIP:", "[WIP]")
NEW_LABEL_COLOR = "ededed"
FACTORY_LABEL = "factory"
HUMAN_LABEL = "needs-human"
REVIEW_MARK = "factory-reviewed:"
EXAMINE_LIMIT = 50
GH_TIMEOUT = 120
GIT_TIMEOUT = 30
PUSH_TIMEOUT = 600
HTTP_TIMEOUT = 30
EXIT_ERROR = 1
EXIT_REFUSED = 3

# A pull request touching any of these is a one-way door: it is never merged
# automatically, because reverting it does not undo what it changed.
DEFAULT_ONE_WAY_PATHS = [
    ".github/**",
    ".forgejo/**",
    ".gitea/**",
    ".woodpecker/**",
    ".gitlab-ci.yml",
    "**/migrations/**",
    "**/migration/**",
    "**/*.sql",
    "db/**",
    "schema/**",
    "**/Dockerfile*",
    "docker-compose*.yml",
    "infra/**",
    "terraform/**",
    "**/*.tf",
    "helm/**",
    "k8s/**",
    "**/iam/**",
    "**/*policy*.json",
    "**/.env*",
    "**/secrets/**",
    "**/package.json",
    "**/package-lock.json",
    "**/pnpm-lock.yaml",
    "**/yarn.lock",
    "**/pyproject.toml",
    "**/uv.lock",
    "**/poetry.lock",
    "**/requirements*.txt",
    "**/Cargo.toml",
    "**/Cargo.lock",
    "**/go.mod",
    "**/go.sum",
    "**/*.proto",
    "**/openapi*",
    "LICENSE*",
    "SECURITY.md",
    "**/CODEOWNERS",
]

DEFAULTS = {
    "dry-run": True,
    "auto-merge": False,
    "skip": False,
    "max-open-prs": 3,
    "max-open-issues": 10,
    "max-merge-lines": 300,
    "max-merge-files": 12,
    "trusted-authors": [],
    "skip-labels": ["needs-info", "needs-human", "wontfix"],
    "extra-one-way-paths": [],
    "experts": [],
}
CLOSES = re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(\d+)", re.IGNORECASE)
FACTORY_ISSUE_BRANCH = re.compile(rf"^{re.escape(FACTORY_PREFIX)}issue-(\d+)")


class ForgeError(Exception):
    """A forge call or a configuration problem the caller should see."""


class Refused(Exception):
    """A rule stopped the action. ``reasons`` lists every rule that did."""

    def __init__(self, reasons):
        super().__init__("; ".join(reasons))
        self.reasons = reasons


# --- configuration -----------------------------------------------------------


def load_config(root):
    """
    Read ``factory.toml`` under the root, or return an empty config when absent.

    :param root: The folder the factory runs in.
    :return: A dict with ``defaults`` and ``repos`` tables.
    :raises ForgeError: On a malformed file, an unknown key or a wrong type.
    """
    path = Path(root) / "factory.toml"
    if not path.exists():
        return {"defaults": {}, "repos": {}}
    try:
        data = tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as exc:
        raise ForgeError(f"factory.toml is not valid TOML: {exc}") from exc
    extra = set(data) - {"defaults", "repos"}
    if extra:
        raise ForgeError(f"factory.toml: unknown top-level keys {sorted(extra)}")
    cfg = {"defaults": data.get("defaults", {}), "repos": data.get("repos", {})}
    for where, table in [("defaults", cfg["defaults"]), *cfg["repos"].items()]:
        for key, value in table.items():
            if key not in DEFAULTS:
                raise ForgeError(f"factory.toml [{where}]: unknown key '{key}'")
            if type(value) is not type(DEFAULTS[key]):
                raise ForgeError(f"factory.toml [{where}] {key}: expected {type(DEFAULTS[key]).__name__}")
    return cfg


def settings_for(cfg, name):
    """
    Merge built-in defaults, ``[defaults]`` and ``[repos.<name>]``, later winning.

    :param cfg: The config from :func:`load_config`.
    :param name: The repo's folder name.
    :return: The effective settings. ``one-way`` holds the built-in patterns plus the
        repo's extras, and a repo cannot remove a built-in one.
    """
    merged = {**DEFAULTS, **cfg["defaults"], **cfg["repos"].get(name, {})}
    merged["one-way"] = [*DEFAULT_ONE_WAY_PATHS, *merged["extra-one-way-paths"]]
    return merged


# --- discovery ---------------------------------------------------------------

REMOTE = re.compile(r"^(?:[a-z+]+://)?(?:[^@/]+@)?([^/:]+)(?::\d+)?[:/]+(.+?)(?:\.git)?/?$", re.IGNORECASE)


def parse_remote(url):
    """
    Split a git remote into host and ``owner/name``.

    :param url: An https, ssh or scp-style remote URL.
    :return: ``(host, slug)``, or ``(None, None)`` when it does not parse.
    """
    match = REMOTE.match(url.strip())
    if not match:
        return None, None
    return match.group(1).lower(), match.group(2)


def _git(path, *args):
    try:
        out = subprocess.run(
            ["git", "-C", str(path), *args], capture_output=True, text=True, check=False, timeout=GIT_TIMEOUT
        )
    except subprocess.TimeoutExpired:
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def inspect_repo(entry, cfg):
    """
    Decide whether one folder is a repo the factory may work on.

    A folder counts when it has a ``.git`` directory and an ``origin`` on GitHub
    or Codeberg. Worktrees, repos on other hosts and repos the config skips are
    not usable, and say why.

    :param entry: A folder directly under the root.
    :param cfg: The config from :func:`load_config`.
    :return: ``(repo, None)`` when usable, ``(None, reason)`` when not,
        and ``(None, None)`` when the folder is not a repo at all.
    """
    git_dir = entry / ".git"
    if git_dir.is_file():
        return None, "a worktree, not a clone"
    if not git_dir.is_dir():
        return None, None
    settings = settings_for(cfg, entry.name)
    if settings["skip"]:
        return None, "skip = true in factory.toml"
    url = _git(entry, "remote", "get-url", "origin")
    if not url:
        return None, "no origin remote"
    host, slug = parse_remote(url)
    if host not in SUPPORTED_HOSTS:
        return None, f"unsupported host {host}"
    head = _git(entry, "symbolic-ref", "--short", "refs/remotes/origin/HEAD") or "origin/main"
    listed = {k: v for k, v in settings.items() if k != "one-way"}
    return {
        "name": entry.name,
        "path": str(entry),
        "forge": SUPPORTED_HOSTS[host],
        "slug": slug,
        "default_branch": head.removeprefix("origin/"),
        "settings": listed,
    }, None


def discover(root, cfg):
    """
    Find the repos the factory may work on, directly under the root.

    :param root: The folder the factory runs in.
    :param cfg: The config from :func:`load_config`.
    :return: ``{"root", "repos", "skipped"}``. Hidden folders and folders that
        are not repos are left out of both lists.
    """
    repos, skipped = [], []
    for entry in sorted(Path(root).iterdir(), key=lambda p: p.name):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        repo, reason = inspect_repo(entry, cfg)
        if repo:
            repos.append(repo)
        elif reason:
            skipped.append({"name": entry.name, "reason": reason})
    return {"root": str(root), "repos": repos, "skipped": skipped}


@dataclass
class Target:
    """The repo a verb acts on."""

    name: str
    forge: str
    slug: str
    path: str = ""


def resolve_target(root, cfg, text):
    """
    Turn a path or ``forge:owner/name`` into a :class:`Target`.

    :param root: The folder the factory runs in.
    :param cfg: The config from :func:`load_config`.
    :param text: The TARGET argument.
    :return: The target.
    :raises ForgeError: When the target is not a supported repo.
    """
    prefix, _, rest = text.partition(":")
    if prefix in SUPPORTED_HOSTS.values() and "/" in rest:
        return Target(rest.rsplit("/", 1)[1], prefix, rest)
    path = Path(text) if Path(text).is_absolute() else Path(root) / text
    repo, reason = inspect_repo(path, {"defaults": {}, "repos": {}})
    if not repo:
        raise ForgeError(f"{text}: not a usable repo ({reason or 'not a git clone'})")
    return Target(repo["name"], repo["forge"], repo["slug"], repo["path"])


# --- forges ------------------------------------------------------------------


class Forge:
    """What the rules below need from a forge. Implementations are GitHub and Codeberg."""

    def whoami(self):
        """:return: The login of the authenticated user, or an empty string."""
        raise NotImplementedError

    def permission(self, login):
        """:return: ``login``'s permission on the repo, or an empty string when unknown."""
        raise NotImplementedError

    def issues(self):
        """:return: Open issues as normalised dicts."""
        raise NotImplementedError

    def issue(self, number):
        """:return: One issue with its comments."""
        raise NotImplementedError

    def all_issues(self):
        """:return: Issues in every state, newest first, as normalised dicts."""
        raise NotImplementedError

    def create_issue(self, title, body):
        """:return: ``{"number", "url"}`` of a new issue."""
        raise NotImplementedError

    def prs(self, state):
        """:return: Pull requests (``open`` or ``all``) as normalised dicts."""
        raise NotImplementedError

    def pr_detail(self, number):
        """:return: One pull request with its files, checks and review state."""
        raise NotImplementedError

    def comment(self, number, body):
        """Add a comment to an issue or pull request."""
        raise NotImplementedError

    def add_label(self, number, name):
        """Add a label, creating it when the repo has none by that name."""
        raise NotImplementedError

    def open_pr(self, head, base, title, body):
        """:return: ``{"number", "url"}`` of a new draft pull request."""
        raise NotImplementedError

    def ready(self, number):
        """Take a pull request out of draft."""
        raise NotImplementedError

    def merge(self, number, sha, head_ref):
        """Squash-merge a pull request that is still at ``sha``."""
        raise NotImplementedError


def _verdict_github(check):
    if "status" not in check and "state" in check:
        state = (check.get("state") or "").upper()
        return {"SUCCESS": "pass", "FAILURE": "fail", "ERROR": "fail"}.get(state, "pending")
    if (check.get("status") or "").upper() != "COMPLETED":
        return "pending"
    conclusion = (check.get("conclusion") or "").upper()
    if conclusion == "SUCCESS":
        return "pass"
    return "skip" if conclusion in ("NEUTRAL", "SKIPPED") else "fail"


def _verdict_codeberg(status):
    return {"success": "pass", "failure": "fail", "error": "fail", "skipped": "skip"}.get(
        (status or "").lower(), "pending"
    )


def summarise_checks(items):
    """
    Reduce ``(name, verdict)`` pairs to one state.

    Success needs at least one passing check and none failing or pending, so a
    repo with no CI is ``none``, never green.

    :param items: Pairs of check name and ``pass``, ``fail``, ``pending`` or ``skip``.
    :return: ``{"state", "passed", "failing", "pending"}``.
    """
    failing = [n for n, v in items if v == "fail"]
    pending = [n for n, v in items if v == "pending"]
    passed = sum(1 for _, v in items if v == "pass")
    if failing:
        state = "failure"
    elif pending:
        state = "pending"
    else:
        state = "success" if passed else "none"
    return {"state": state, "passed": passed, "failing": failing, "pending": pending}


class GitHub(Forge):
    """GitHub through the ``gh`` CLI, which carries its own login."""

    def __init__(self, slug, run=None):
        self.slug = slug
        self._run = run or self._subprocess

    @staticmethod
    def _subprocess(args, stdin=None):
        try:
            out = subprocess.run(
                ["gh", *args], input=stdin, capture_output=True, text=True, check=False, timeout=GH_TIMEOUT
            )
        except subprocess.TimeoutExpired as exc:
            raise ForgeError(f"gh {' '.join(args[:3])}: timed out after {GH_TIMEOUT}s") from exc
        except FileNotFoundError as exc:
            raise ForgeError("gh is not installed") from exc
        if out.returncode != 0:
            raise ForgeError(f"gh {' '.join(args[:3])}: {out.stderr.strip()[:300]}")
        return out.stdout

    def _json(self, args):
        text = self._run(args).strip()
        return json.loads(text) if text else None

    def whoami(self):
        try:
            return self._run(["api", "user", "--jq", ".login"]).strip()
        except ForgeError:
            return ""

    def permission(self, login):
        try:
            args = ["api", f"repos/{self.slug}/collaborators/{login}/permission", "--jq", ".permission"]
            return self._run(args).strip().lower()
        except ForgeError:
            return ""

    @staticmethod
    def _issue(raw):
        return {
            "number": raw["number"],
            "title": raw["title"],
            "body": raw.get("body") or "",
            "state": "closed" if (raw.get("state") or "").upper() == "CLOSED" else "open",
            "author": (raw.get("author") or {}).get("login", ""),
            "labels": [x["name"] for x in raw.get("labels", [])],
            "assignees": [x["login"] for x in raw.get("assignees", [])],
            "created_at": raw.get("createdAt", ""),
            "updated_at": raw.get("updatedAt", ""),
        }

    ISSUE_FIELDS = "number,title,body,state,author,assignees,labels,createdAt,updatedAt"

    def issues(self):
        raw = self._json(
            ["issue", "list", "--repo", self.slug, "--state", "open", "--limit", "200", "--json", self.ISSUE_FIELDS]
        )
        return [self._issue(x) for x in raw or []]

    def all_issues(self):
        raw = self._json(
            ["issue", "list", "--repo", self.slug, "--state", "all", "--limit", "500", "--json", self.ISSUE_FIELDS]
        )
        return [self._issue(x) for x in raw or []]

    def create_issue(self, title, body):
        url = (
            self._run(["issue", "create", "--repo", self.slug, "--title", title, "--body-file", "-"], stdin=body)
            .strip()
            .splitlines()[-1]
        )
        return {"number": int(url.rstrip("/").rsplit("/", 1)[1]), "url": url}

    def issue(self, number):
        raw = self._json(["issue", "view", str(number), "--repo", self.slug, "--json", self.ISSUE_FIELDS + ",comments"])
        found = self._issue(raw)
        found["comments"] = [
            {
                "author": (c.get("author") or {}).get("login", ""),
                "body": c.get("body", ""),
                "created_at": c.get("createdAt", ""),
            }
            for c in raw.get("comments", [])
        ]
        return found

    PR_FIELDS = (
        "number,title,body,state,isDraft,headRefName,headRefOid,baseRefName,author,labels,"
        "mergeable,additions,deletions,changedFiles,closingIssuesReferences"
    )

    @staticmethod
    def _pr(raw):
        return {
            "number": raw["number"],
            "title": raw["title"],
            "body": raw.get("body") or "",
            "state": "open" if raw["state"] == "OPEN" else "closed",
            "merged": raw["state"] == "MERGED",
            "draft": bool(raw.get("isDraft")),
            "head_ref": raw["headRefName"],
            "head_sha": raw.get("headRefOid", ""),
            "base_ref": raw.get("baseRefName", ""),
            "author": (raw.get("author") or {}).get("login", ""),
            "labels": [x["name"] for x in raw.get("labels", [])],
            "mergeable": {"MERGEABLE": True, "CONFLICTING": False}.get(raw.get("mergeable")),
            "additions": raw.get("additions", 0),
            "deletions": raw.get("deletions", 0),
            "changed_files": raw.get("changedFiles", 0),
            "closes": [x["number"] for x in raw.get("closingIssuesReferences", [])],
        }

    def prs(self, state):
        raw = self._json(
            ["pr", "list", "--repo", self.slug, "--state", state, "--limit", "200", "--json", self.PR_FIELDS]
        )
        return [self._pr(x) for x in raw or []]

    def pr_detail(self, number):
        raw = self._json(
            [
                "pr",
                "view",
                str(number),
                "--repo",
                self.slug,
                "--json",
                self.PR_FIELDS + ",files,statusCheckRollup,reviewDecision,comments",
            ]
        )
        found = self._pr(raw)
        found["files"] = [f["path"] for f in raw.get("files", [])]
        found["checks"] = summarise_checks(
            [(c.get("name") or c.get("context") or "?", _verdict_github(c)) for c in raw.get("statusCheckRollup", [])]
        )
        found["review_blocked"] = raw.get("reviewDecision") == "CHANGES_REQUESTED"
        comments = [
            {"author": (c.get("author") or {}).get("login", ""), "body": c.get("body", "")}
            for c in raw.get("comments", [])
        ]
        found["reviewed_shas"] = marked_shas(comments, self.whoami())
        return found

    def comment(self, number, body):
        self._run(["api", "-X", "POST", f"repos/{self.slug}/issues/{number}/comments", "-f", f"body={body}"])

    def add_label(self, number, name):
        known = self._run(
            ["api", f"repos/{self.slug}/labels?per_page=100", "--paginate", "--jq", ".[].name"]
        ).splitlines()
        if name not in known:
            self._run(
                [
                    "api",
                    "-X",
                    "POST",
                    f"repos/{self.slug}/labels",
                    "-f",
                    f"name={name}",
                    "-f",
                    f"color={NEW_LABEL_COLOR}",
                ]
            )
        self._run(["api", "-X", "POST", f"repos/{self.slug}/issues/{number}/labels", "-f", f"labels[]={name}"])

    def open_pr(self, head, base, title, body):
        url = (
            self._run(
                [
                    "pr",
                    "create",
                    "--repo",
                    self.slug,
                    "--draft",
                    "--head",
                    head,
                    "--base",
                    base,
                    "--title",
                    title,
                    "--body-file",
                    "-",
                ],
                stdin=body,
            )
            .strip()
            .splitlines()[-1]
        )
        return {"number": int(url.rstrip("/").rsplit("/", 1)[1]), "url": url}

    def ready(self, number):
        self._run(["pr", "ready", str(number), "--repo", self.slug])

    def merge(self, number, sha, head_ref):
        self._run(["pr", "merge", str(number), "--repo", self.slug, "--squash", "--match-head-commit", sha])
        try:
            self._run(["api", "-X", "DELETE", f"repos/{self.slug}/git/refs/heads/{head_ref}"])
        except ForgeError:
            pass  # the repo may delete merged branches itself


class Codeberg(Forge):
    """Codeberg (Forgejo) through its REST API. The token comes from ``CODEBERG_TOKEN``."""

    API = "https://codeberg.org/api/v1"

    def __init__(self, slug, token=None, http=None):
        self.slug = slug
        self.token = token if token is not None else os.environ.get("CODEBERG_TOKEN", "")
        self._http = http or self._urlopen

    def _urlopen(self, method, url, body):
        """
        Send one request. Network failures and bad bodies become :class:`ForgeError`.

        Only GET is retried, once, on a network failure or a 5xx. A write is never
        retried, because a repeated comment or merge cannot be undone.
        """
        headers = {"User-Agent": "forge.py", "Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        attempts = 2 if method == "GET" else 1
        for attempt in range(attempts):
            request = urllib.request.Request(url, data=data, headers=headers, method=method)
            last = attempt + 1 == attempts
            try:
                with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
                    text = response.read().decode()
                    return response.status, (json.loads(text) if text else None)
            except urllib.error.HTTPError as exc:
                text = exc.read().decode(errors="replace")[:300]
                if exc.code >= 500 and not last:
                    continue
                return exc.code, text
            except (OSError, http.client.HTTPException, ValueError) as exc:  # URLError, timeouts, resets, bad JSON
                if not last:
                    continue
                raise ForgeError(
                    f"codeberg {method} {url.split('/api/v1', 1)[-1].split('?')[0]}: {type(exc).__name__}: {exc}"
                ) from exc
        raise AssertionError("unreachable")

    def _call(self, method, path, body=None, query=None):
        url = f"{self.API}/repos/{self.slug}{path}"
        if query:
            url += "?" + urllib.parse.urlencode(query)
        status, data = self._http(method, url, body)
        if status >= 400:
            raise ForgeError(f"codeberg {method} {path}: HTTP {status} {data}")
        return data

    def _pages(self, path, query=None, limit=50, max_pages=8):
        out = []
        for page in range(1, max_pages + 1):
            chunk = self._call("GET", path, query={**(query or {}), "limit": limit, "page": page}) or []
            out += chunk
            if len(chunk) < limit:
                break
        return out

    def whoami(self):
        if not self.token:
            return ""
        status, data = self._http("GET", f"{self.API}/user", None)
        return data.get("login", "") if status == 200 and isinstance(data, dict) else ""

    def permission(self, login):
        try:
            data = self._call("GET", f"/collaborators/{urllib.parse.quote(login)}/permission")
        except ForgeError:
            return ""
        return (data or {}).get("permission", "").lower()

    @staticmethod
    def _issue(raw):
        return {
            "number": raw["number"],
            "title": raw["title"],
            "body": raw.get("body") or "",
            "state": raw.get("state", "open"),
            "author": (raw.get("user") or {}).get("login", ""),
            "labels": [x["name"] for x in raw.get("labels") or []],
            "assignees": [x["login"] for x in raw.get("assignees") or []],
            "created_at": raw.get("created_at", ""),
            "updated_at": raw.get("updated_at", ""),
        }

    def issues(self):
        return [self._issue(x) for x in self._pages("/issues", {"state": "open", "type": "issues"})]

    def all_issues(self):
        return [self._issue(x) for x in self._pages("/issues", {"state": "all", "type": "issues"}, max_pages=10)]

    def create_issue(self, title, body):
        made = self._call("POST", "/issues", {"title": title, "body": body})
        return {"number": made["number"], "url": made.get("html_url", "")}

    def issue(self, number):
        found = self._issue(self._call("GET", f"/issues/{number}"))
        comments = self._pages(f"/issues/{number}/comments")
        found["comments"] = [
            {
                "author": (c.get("user") or {}).get("login", ""),
                "body": c.get("body", ""),
                "created_at": c.get("created_at", ""),
            }
            for c in comments
        ]
        return found

    @staticmethod
    def _pr(raw):
        return {
            "number": raw["number"],
            "title": raw["title"],
            "body": raw.get("body") or "",
            "state": raw.get("state", "open"),
            "merged": bool(raw.get("merged")),
            "draft": bool(raw.get("draft")),
            "head_ref": (raw.get("head") or {}).get("ref", ""),
            "head_sha": (raw.get("head") or {}).get("sha", ""),
            "base_ref": (raw.get("base") or {}).get("ref", ""),
            "author": (raw.get("user") or {}).get("login", ""),
            "labels": [x["name"] for x in raw.get("labels") or []],
            "mergeable": raw.get("mergeable"),
            "additions": raw.get("additions", 0),
            "deletions": raw.get("deletions", 0),
            "changed_files": raw.get("changed_files", 0),
            "closes": [],
        }

    def prs(self, state):
        return [self._pr(x) for x in self._pages("/pulls", {"state": state, "sort": "recentupdate"})]

    def pr_detail(self, number):
        found = self._pr(self._call("GET", f"/pulls/{number}"))
        found["files"] = [f["filename"] for f in self._pages(f"/pulls/{number}/files")]
        status = self._call("GET", f"/commits/{found['head_sha']}/status") or {}
        found["checks"] = summarise_checks(
            [(s.get("context", "?"), _verdict_codeberg(s.get("status"))) for s in status.get("statuses") or []]
        )
        latest = {}
        for review in self._pages(f"/pulls/{number}/reviews"):
            if not review.get("dismissed") and not review.get("stale"):
                latest[(review.get("user") or {}).get("id")] = review.get("state")
        found["review_blocked"] = "REQUEST_CHANGES" in latest.values()
        comments = [
            {"author": (c.get("user") or {}).get("login", ""), "body": c.get("body", "")}
            for c in self._pages(f"/issues/{number}/comments")
        ]
        found["reviewed_shas"] = marked_shas(comments, self.whoami())
        return found

    def comment(self, number, body):
        self._call("POST", f"/issues/{number}/comments", {"body": body})

    def add_label(self, number, name):
        known = {x["name"]: x["id"] for x in self._pages("/labels")}
        if name not in known:
            created = self._call("POST", "/labels", {"name": name, "color": "#" + NEW_LABEL_COLOR})
            known[name] = created["id"]
        self._call("POST", f"/issues/{number}/labels", {"labels": [known[name]]})

    def open_pr(self, head, base, title, body):
        made = self._call("POST", "/pulls", {"head": head, "base": base, "title": f"WIP: {title}", "body": body})
        return {"number": made["number"], "url": made.get("html_url", "")}

    def ready(self, number):
        current = self._call("GET", f"/pulls/{number}")["title"]
        title = current
        for prefix in WIP_PREFIXES:
            if title.upper().startswith(prefix.upper()):
                title = title[len(prefix) :].lstrip()
        if title != current:
            self._call("PATCH", f"/pulls/{number}", {"title": title})

    def merge(self, number, sha, head_ref):
        self._call(
            "POST",
            f"/pulls/{number}/merge",
            {"Do": "squash", "head_commit_id": sha, "delete_branch_after_merge": True},
        )


def make_forge(target):
    """
    Build the adapter for a target.

    :param target: A :class:`Target`.
    :return: A :class:`GitHub` or :class:`Codeberg`.
    """
    return GitHub(target.slug) if target.forge == "github" else Codeberg(target.slug)


# --- rules -------------------------------------------------------------------


def glob_match(pattern, path):
    """
    Match a path against a glob where ``**`` crosses folders and ``*`` does not.

    :param pattern: A glob such as ``**/migrations/**`` or ``infra/**``.
    :param path: A repo-relative path with forward slashes.
    :return: Whether the whole path matches.
    """
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif pattern.startswith("**", i):
            out, i = out + ".*", i + 2
        elif pattern[i] == "*":
            out, i = out + "[^/]*", i + 1
        elif pattern[i] == "?":
            out, i = out + "[^/]", i + 1
        else:
            out, i = out + re.escape(pattern[i]), i + 1
    return re.fullmatch(out, path) is not None


def one_way_files(files, patterns):
    """
    :param files: Repo-relative paths a pull request changes.
    :param patterns: One-way globs.
    :return: The files that match at least one pattern.
    """
    return [f for f in files if any(glob_match(p, f) for p in patterns)]


def gate_detail(pr, expected_sha, cfg):
    """
    Check every rule that decides whether a pull request may merge on its own.

    Every rule is checked, so a refusal lists everything that stands in the way.
    Draft is allowed here: ``merge`` takes the pull request out of draft once
    this passes.

    :param pr: A normalised pull request from ``pr_detail``.
    :param expected_sha: The head the caller reviewed.
    :param cfg: Effective repo settings.
    :return: ``(kind, reason)`` pairs, empty when it may merge. ``kind`` is ``off``
        (this repo or branch is not set up for automatic merges), ``wait`` (try
        again on a later run) or ``human`` (a person has to decide).
    """
    found = []
    if not cfg["auto-merge"]:
        found.append(("off", "auto-merge is off for this repo"))
    if not pr["head_ref"].startswith(FACTORY_PREFIX):
        found.append(("off", f"branch '{pr['head_ref']}' is not a factory branch"))
    if pr["state"] != "open" or pr["merged"]:
        found.append(("off", "pull request is not open"))
    if pr["head_sha"] != expected_sha:
        found.append(("wait", f"head moved: reviewed {expected_sha[:8]}, now {pr['head_sha'][:8]}"))
    if expected_sha not in pr["reviewed_shas"]:
        found.append(("wait", "no clean review recorded for this head"))
    checks = pr["checks"]
    if checks["state"] == "none":
        found.append(("human", "no passing checks: a repo with no CI is not green"))
    elif checks["state"] == "failure":
        found.append(("human", f"checks failing: {', '.join(checks['failing'])}"))
    elif checks["state"] == "pending":
        found.append(("wait", f"checks pending: {', '.join(checks['pending'])}"))
    if pr["mergeable"] is False:
        found.append(("human", "has merge conflicts"))
    elif pr["mergeable"] is None:
        found.append(("wait", "mergeability unknown"))
    if pr["review_blocked"]:
        found.append(("human", "a reviewer requested changes"))
    lines = pr["additions"] + pr["deletions"]
    if lines > cfg["max-merge-lines"]:
        found.append(("human", f"too large: {lines} lines (limit {cfg['max-merge-lines']})"))
    if pr["changed_files"] > cfg["max-merge-files"]:
        found.append(("human", f"too many files: {pr['changed_files']} (limit {cfg['max-merge-files']})"))
    risky = one_way_files(pr["files"], cfg["one-way"])
    if risky:
        shown = ", ".join(risky[:5]) + (f" and {len(risky) - 5} more" if len(risky) > 5 else "")
        found.append(("human", f"one-way door, touches: {shown}"))
    return found


def gate(pr, expected_sha, cfg):
    """
    :param pr: A normalised pull request from ``pr_detail``.
    :param expected_sha: The head the caller reviewed.
    :param cfg: Effective repo settings.
    :return: The reasons the pull request may not merge. Empty means it may.
    """
    return [reason for _, reason in gate_detail(pr, expected_sha, cfg)]


def verdict(details):
    """
    :param details: ``(kind, reason)`` pairs from :func:`gate_detail`.
    :return: ``merge`` when nothing stands in the way. Otherwise the strongest
        kind: ``off`` over ``human`` over ``wait``, so a person is only asked
        when nothing else rules the pull request out.
    """
    kinds = {kind for kind, _ in details}
    if not kinds:
        return "merge"
    for kind in ("off", "human"):
        if kind in kinds:
            return kind
    return "wait"


def marked_shas(comments, me):
    """
    Collect the heads the authenticated user recorded as cleanly reviewed.

    :param comments: Dicts with ``author`` and ``body``.
    :param me: The authenticated user's login. Empty means signed out.
    :return: Commit SHAs from ``factory-reviewed: <sha>`` lines the user wrote.
    """
    if not me:
        return []
    found = []
    for comment in comments:
        if comment["author"] != me:
            continue
        for line in comment["body"].splitlines():
            line = line.strip()
            if line.startswith(REVIEW_MARK):
                found.append(line[len(REVIEW_MARK) :].strip())
    return found


def linked_issues(pr):
    """
    :param pr: A normalised pull request.
    :return: Issue numbers it is linked to, by branch name, closing keyword or the forge's own link.
    """
    found = set(pr.get("closes", []))
    branch = FACTORY_ISSUE_BRANCH.match(pr["head_ref"])
    if branch:
        found.add(int(branch.group(1)))
    found.update(int(n) for n in CLOSES.findall(pr["body"]))
    return found


def is_trusted(forge, cfg, login, me, cache):
    """
    Decide whether to act on an issue this person wrote.

    Anyone can open an issue on a public repo, and an issue is instructions to an
    agent that runs unattended. Only the authenticated user, listed authors and
    people with write access count. A missing author or an unknown permission
    counts as not trusted.

    :param forge: The adapter.
    :param cfg: Effective repo settings.
    :param login: The issue author.
    :param me: The authenticated user's login, or an empty string.
    :param cache: A dict of earlier answers for this repo, keyed by login.
    :return: Whether the author is trusted.
    """
    if not login:
        return False  # guards the comparison below: "" == "" must never count as a match
    if login not in cache:
        cache[login] = login == me or login in cfg["trusted-authors"] or forge.permission(login) in TRUSTED_PERMISSIONS
    return cache[login]


def select_issues(forge, cfg):
    """
    Pick the issues the factory may work on now.

    An issue is skipped when a pull request already covers it (open, merged, or
    closed unmerged, because a closed one means a person said no), when someone
    is assigned, or when it carries a skip label. The rest are checked oldest
    first, and an author without trust is reported, not worked on. Checking
    stops once the free slots under ``max-open-prs`` are filled, or after
    ``EXAMINE_LIMIT`` issues, so ``untrusted`` and ``skipped`` cover only the
    issues examined up to then.

    :param forge: The adapter.
    :param cfg: Effective repo settings.
    :return: ``{"slots", "issues", "untrusted", "skipped", "truncated"}``. ``truncated``
        is true when the limit stopped the examination.
    """
    prs = forge.prs("all")
    covered = {n for pr in prs for n in linked_issues(pr)}
    open_factory = sum(1 for pr in prs if pr["state"] == "open" and pr["head_ref"].startswith(FACTORY_PREFIX))
    slots = max(0, cfg["max-open-prs"] - open_factory)
    skip_labels = {x.lower() for x in cfg["skip-labels"]}
    ready, untrusted, skipped, cache, truncated = [], [], [], {}, False
    me = forge.whoami() if slots else ""
    oldest_first = sorted(forge.issues(), key=lambda i: i["created_at"]) if slots else []
    for examined, issue in enumerate(oldest_first):
        if len(ready) == slots:
            break
        if examined == EXAMINE_LIMIT:
            truncated = True
            break
        labels = {x.lower() for x in issue["labels"]}
        if issue["number"] in covered:
            skipped.append({"number": issue["number"], "reason": "a pull request already covers it"})
        elif issue["assignees"]:
            skipped.append({"number": issue["number"], "reason": f"assigned to {', '.join(issue['assignees'])}"})
        elif labels & skip_labels:
            skipped.append({"number": issue["number"], "reason": f"labelled {', '.join(sorted(labels & skip_labels))}"})
        elif not is_trusted(forge, cfg, issue["author"], me, cache):
            untrusted.append({"number": issue["number"], "author": issue["author"]})
        else:
            ready.append(issue)
    return {"slots": slots, "issues": ready, "untrusted": untrusted, "skipped": skipped, "truncated": truncated}


def fingerprint_id(raw):
    """
    Turn a finding's fingerprint into a short token that survives search and wrapping.

    :param raw: The fingerprint text, ``<path>|<lens>|<claim>``.
    :return: ``fp`` and twelve hex characters. Case and spacing do not change it.
    """
    return "fp" + hashlib.sha1(" ".join(raw.lower().split()).encode()).hexdigest()[:12]


def find_by_fingerprint(forge, raw):
    """
    List the issues, open or closed, that were filed for this fingerprint.

    :param forge: The adapter.
    :param raw: The fingerprint text.
    :return: ``{"fingerprint", "matches"}``, each match with number, state and title.
    """
    token = fingerprint_id(raw)
    matches = [
        {"number": i["number"], "state": i["state"], "title": i["title"]}
        for i in forge.all_issues()
        if token in i["body"]
    ]
    return {"fingerprint": token, "matches": matches}


def check_pushable(branch, default_branch):
    """
    :param branch: The branch to push.
    :param default_branch: The repo's default branch.
    :raises Refused: When the branch is not a factory branch, or is the default one.
    """
    reasons = []
    if not branch.startswith(FACTORY_PREFIX):
        reasons.append(f"'{branch}' is not a factory branch: pushes are limited to {FACTORY_PREFIX}*")
    if branch == default_branch:
        reasons.append(f"'{branch}' is the default branch")
    if reasons:
        raise Refused(reasons)


def push_branch(path, branch, default_branch, run=subprocess.run):
    """
    Push a factory branch, and nothing else, to origin.

    :param path: The local clone.
    :param branch: The branch to push.
    :param default_branch: The repo's default branch.
    :param run: Runs the command. Tests replace it.
    :raises Refused: When the branch is not pushable.
    :raises ForgeError: When git fails.
    """
    check_pushable(branch, default_branch)
    try:
        done = run(
            ["git", "-C", path, "push", "--set-upstream", "origin", f"{branch}:{branch}"],
            capture_output=True,
            text=True,
            check=False,
            timeout=PUSH_TIMEOUT,
        )
    except subprocess.TimeoutExpired as exc:
        raise ForgeError(f"git push {branch}: timed out after {PUSH_TIMEOUT}s") from exc
    if done.returncode != 0:
        raise ForgeError(f"git push {branch}: {done.stderr.strip()[:300]}")


# --- verbs -------------------------------------------------------------------


def _write(cfg, action, details, do):
    """Run ``do`` unless the repo is in dry-run mode, which reports instead."""
    if cfg["dry-run"]:
        return {"dry_run": True, "would": action, **details}
    return {"dry_run": False, "done": action, **details, **(do() or {})}


def run_verb(args, root, cfg, forge, target):
    """
    Run one verb against one repo.

    :param args: The parsed arguments.
    :param root: The folder the factory runs in.
    :param cfg: Effective settings for the target.
    :param forge: The adapter for the target.
    :param target: The :class:`Target`.
    :return: The JSON-serialisable result.
    :raises Refused: When a rule stops a write.
    """
    verb = args.verb
    if verb == "issues":
        return {"repo": target.slug, "dry_run": cfg["dry-run"], **select_issues(forge, cfg)}
    if verb == "issue":
        found = forge.issue(args.number)
        me, cache = forge.whoami(), {}
        found["author_trusted"] = is_trusted(forge, cfg, found["author"], me, cache)
        for comment in found["comments"]:
            comment["trusted"] = is_trusted(forge, cfg, comment["author"], me, cache)
        return found
    if verb == "prs":
        return {"repo": target.slug, "prs": [p for p in forge.prs("open")]}
    if verb == "check":
        pr = forge.pr_detail(args.number)
        detail = gate_detail(pr, args.sha or pr["head_sha"], cfg)
        return {
            "number": args.number,
            "allowed": not detail,
            "verdict": verdict(detail),
            "reasons": [reason for _, reason in detail],
            "head_sha": pr["head_sha"],
            "draft": pr["draft"],
            "labels": pr["labels"],
        }
    if verb == "mark-reviewed":
        pr = forge.pr_detail(args.number)
        reasons = []
        if not pr["head_ref"].startswith(FACTORY_PREFIX):
            reasons.append(f"branch '{pr['head_ref']}' is not a factory branch")
        if pr["head_sha"] != args.sha:
            reasons.append(f"head moved: reviewed {args.sha[:8]}, now {pr['head_sha'][:8]}")
        if reasons:
            raise Refused(reasons)
        note = f"Review loop finished with a clean round.\n\n{REVIEW_MARK} {args.sha}\n"
        return _write(
            cfg, "record the review", {"number": args.number, "sha": args.sha}, lambda: forge.comment(args.number, note)
        )
    if verb == "find":
        return find_by_fingerprint(forge, args.fingerprint)
    if verb == "file":
        found = find_by_fingerprint(forge, args.fingerprint)
        open_ones = [m for m in found["matches"] if m["state"] == "open"]
        if open_ones:
            raise Refused([f"already filed and still open as #{open_ones[0]['number']}"])
        backlog = sum(1 for i in forge.issues() if FACTORY_LABEL in i["labels"])
        if backlog >= cfg["max-open-issues"]:
            raise Refused(
                [f"{backlog} factory issues are already open (limit {cfg['max-open-issues']}): clear some first"]
            )
        text = (
            Path(args.body_file).read_text().rstrip()
            + f"\n\nFingerprint: {args.fingerprint}\nFingerprint-id: {found['fingerprint']}\n"
        )
        labels = [FACTORY_LABEL, *args.label]
        previous = [m["number"] for m in found["matches"]]

        def make():
            made = forge.create_issue(args.title, text)
            for label in labels:
                forge.add_label(made["number"], label)
            return {**made, "labels": labels}

        return _write(cfg, "file an issue", {"title": args.title, "labels": labels, "closed_before": previous}, make)
    if verb == "push":
        if not target.path:
            raise ForgeError("push needs a local clone: give a folder, not forge:owner/name")
        default = (
            _git(target.path, "symbolic-ref", "--short", "refs/remotes/origin/HEAD") or "origin/main"
        ).removeprefix("origin/")
        check_pushable(args.branch, default)  # a refusal shows even in a dry run
        return _write(cfg, "push", {"branch": args.branch}, lambda: push_branch(target.path, args.branch, default))
    if verb == "comment":
        body = Path(args.body_file).read_text()
        return _write(cfg, "comment", {"number": args.number}, lambda: forge.comment(args.number, body))
    if verb == "label":
        return _write(
            cfg, "label", {"number": args.number, "label": args.name}, lambda: forge.add_label(args.number, args.name)
        )
    if verb == "open-pr":
        if not args.head.startswith(FACTORY_PREFIX):
            raise Refused([f"head '{args.head}' must start with {FACTORY_PREFIX}"])
        body = Path(args.body_file).read_text()
        return _write(
            cfg,
            "open a draft pull request",
            {"head": args.head, "base": args.base, "title": args.title},
            lambda: forge.open_pr(args.head, args.base, args.title, body),
        )
    if verb == "ready":
        pr = forge.pr_detail(args.number)
        if not pr["head_ref"].startswith(FACTORY_PREFIX):
            raise Refused([f"branch '{pr['head_ref']}' is not a factory branch"])
        return _write(cfg, "mark ready for review", {"number": args.number}, lambda: forge.ready(args.number))
    if verb == "merge":
        pr = forge.pr_detail(args.number)
        reasons = gate(pr, args.sha, cfg)
        if reasons:
            raise Refused(reasons)

        def do():
            if pr["draft"]:
                forge.ready(args.number)
            forge.merge(args.number, args.sha, pr["head_ref"])

        return _write(cfg, "squash-merge", {"number": args.number, "sha": args.sha}, do)
    raise ForgeError(f"unknown verb {verb}")


def build_parser():
    """:return: The argument parser."""
    parser = argparse.ArgumentParser(
        prog="forge.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--root", default=os.getcwd())
    sub = parser.add_subparsers(dest="verb", required=True)
    sub.add_parser("repos")
    for verb in ("issues", "prs"):
        sub.add_parser(verb).add_argument("target")
    for verb in ("issue", "ready"):
        p = sub.add_parser(verb)
        p.add_argument("target")
        p.add_argument("number", type=int)
    p = sub.add_parser("check")
    p.add_argument("target")
    p.add_argument("number", type=int)
    p.add_argument("--sha")
    p = sub.add_parser("comment")
    p.add_argument("target")
    p.add_argument("number", type=int)
    p.add_argument("--body-file", required=True)
    p = sub.add_parser("label")
    p.add_argument("target")
    p.add_argument("number", type=int)
    p.add_argument("name")
    p = sub.add_parser("open-pr")
    p.add_argument("target")
    for flag in ("--head", "--base", "--title", "--body-file"):
        p.add_argument(flag, required=True)
    p = sub.add_parser("merge")
    p.add_argument("target")
    p.add_argument("number", type=int)
    p.add_argument("--sha", required=True)
    p = sub.add_parser("mark-reviewed")
    p.add_argument("target")
    p.add_argument("number", type=int)
    p.add_argument("--sha", required=True)
    p = sub.add_parser("push")
    p.add_argument("target")
    p.add_argument("--branch", required=True)
    p = sub.add_parser("find")
    p.add_argument("target")
    p.add_argument("--fingerprint", required=True)
    p = sub.add_parser("file")
    p.add_argument("target")
    p.add_argument("--title", required=True)
    p.add_argument("--body-file", required=True)
    p.add_argument("--fingerprint", required=True)
    p.add_argument("--label", action="append", default=[])
    return parser


def main(argv=None, make=make_forge, out=None):
    """
    Entry point.

    :param argv: Arguments without the program name.
    :param make: Builds the adapter for a target. Tests replace it.
    :param out: Where to print. Defaults to stdout.
    :return: The exit code: 0 ok, 1 error, 3 refused by a rule.
    """
    out = out or sys.stdout
    args = build_parser().parse_args(argv)
    try:
        root = Path(args.root).resolve()
        cfg = load_config(root)
        if args.verb == "repos":
            result = discover(root, cfg)
        else:
            target = resolve_target(root, cfg, args.target)
            settings = settings_for(cfg, target.name)
            if settings["skip"]:
                raise Refused([f"{target.name} is skipped in factory.toml"])
            result = run_verb(args, root, settings, make(target), target)
    except Refused as exc:
        print(json.dumps({"refused": True, "reasons": exc.reasons}, indent=2), file=out)
        return EXIT_REFUSED
    except (ForgeError, OSError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2), file=out)
        return EXIT_ERROR
    print(json.dumps(result, indent=2), file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
