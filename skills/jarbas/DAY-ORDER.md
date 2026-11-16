# Today Order

Use for visual Today order. This changes `dayOrder`, not task due times.

## 1. Prepare a safe order

Fetch fresh state:

```bash
td today --json --full --all
```

Include active non-recurring tasks only. Preserve recurring tasks as fixed anchors because writing `dayOrder` to them can advance their due date. If the requested result requires moving a recurring task, explain the risk and ask before mutating it.

The recurring plan-day meta-task is excluded from `dayOrder` writes.

**Complete when:** every writable task ID has a unique target order and every skipped recurring task is accounted for.

## 2. Batch-write `dayOrder`

Capture the token without printing it and send one Sync API command:

```bash
TOKEN=$(td auth token view)
export TOKEN ORDER_JSON='{"TASK_ID":0,"OTHER_TASK_ID":1}'
python3 - <<'PY'
import json, os, uuid, urllib.parse, urllib.request

command = {
    "type": "item_update_day_orders",
    "uuid": str(uuid.uuid4()),
    "args": {"ids_to_orders": json.loads(os.environ["ORDER_JSON"])},
}
data = urllib.parse.urlencode({"commands": json.dumps([command])}).encode()
request = urllib.request.Request(
    "https://api.todoist.com/api/v1/sync",
    method="POST",
    data=data,
    headers={"Authorization": f"Bearer {os.environ['TOKEN']}"},
)
urllib.request.urlopen(request, timeout=30).read()
PY
unset TOKEN ORDER_JSON
```

`ids_to_orders` is an object. The Sync response's `day_orders` field may be empty on success, so it is not verification. `td task update --order` changes project-level `childOrder` and is not a substitute.

## 3. Verify order

```bash
td today --json --full --all \
  | jq -r '.results | sort_by(.dayOrder) | .[] | "\(.dayOrder)\t\(.id)\t\(.content)"'
```

Compare every writable task against its target. Closed, deleted, and recurring tasks never enter the automatic write batch.

**Complete when:** re-fetched `dayOrder` values match the target for every written task.

## 4. Report

Report the verified final order, identify recurring anchors left untouched, and explicitly state:

```text
Todoist due times were unchanged.
```
