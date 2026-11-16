---
name: gamenative
description: "Interact with GameNative (Android Wine game emulator) over adb to configure containers, launch games, and debug black-screen/graphics issues. Use when the user mentions GameNative, running Windows games on Android, Broken Sword, or container/graphics config for Winlator-like apps."
metadata:
  version: 1.0.0
  category: gaming
  requires:
    bins: [adb, android]
---

# GameNative — Android Wine Game Emulator

GameNative runs Windows games on ARM Android via Wine + Box64/FEXCore emulation.
This skill is for driving it over `adb` and the `android` CLI from a host machine
when you cannot (or do not want to) tap the screen by hand.

## Prereqs
- `adb` connected to the device: `adb devices` should list `XXXXXXXX device`.
- `android` CLI available (the android-cli skill wraps it). Update with `android update`.
- Device screen is 1080x2400 in the tested setup. Adjust coordinates if different:
  `adb shell wm size`.

## FAST INTERACTION PATTERNS (do this instead of blind tapping)

The single biggest time-saver: **dump the UI tree and tap the element center**,
never guess pixel coords. Blind `input tap X Y` wastes cycles.

```bash
# Dump clickable/visible UI with centers (pretty JSON)
android layout -p
```

Then tap the `center` coordinate of the element you want:
```bash
adb shell input tap <cx> <cy>
```

### Key stable coordinates (1080x2400 — verify with layout first)
- Game detail screen:
  - **Play**:        `238,705`
  - **Options** (gear): `774,706`
  - **Uninstall**:   `932,706`
- Options sheet → "Edit container": `621,376`
- Quick Menu (in-game overlay) — open via swipe-down or back:
  - **Exit**: `116,974`
  - Brightness **+**: `897,509`   (brightness defaults to 10% — raise it!)
  - Brightness **-**: `388,509`
  - Close menu (back arrow): `971,100`
- Feedback/crash dialog "How did the game run?":
  - Dismiss by swiping up, or tap a star. Common issue checkboxes:
    "No Graphics", "Directx Error", "Does Not Open", "Graphics Glitches".
  - Get back to library: swipe up, then tap the game card.

### Navigation helpers
```bash
adb shell input keyevent KEYCODE_BACK          # back
adb shell input swipe 540 1800 540 800 300     # scroll up in a sheet
adb shell am start -n app.gamenative/.MainActivity   # focus the app
```

### Screenshots (you are text-only — rely on layout, not vision)
```bash
android screen capture -o /tmp/shot.png
# Model cannot SEE images. Use `android layout -p` to read UI state instead.
```

### Logs
```bash
adb logcat -d -t 300 --pid=$(adb shell pidof app.gamenative) \
  | grep -iE "err|crash|fail|wine|ddraw|bs1dc|cnc|render|direct"
```
Look for the launch command line — it prints the chosen DX wrapper, graphics
driver, Wine version, and the final env vars. Very useful for debugging.

## COORDINATE SCALING CHEAT SHEET (CRITICAL)

**Two coordinate systems exist on the test device:**
- `android layout -p` returns centers in **2400x1080** (XServer virtual landscape)
- `adb shell input tap` uses **1080x2400** (physical portrait)

**Scale formula:**
```
raw_x = cx * 1080 / 2400
raw_y = cy * 2400 / 1080
```

**Example:** Options button at layout `[1240, 979]` → tap `558, 2175`

**ALWAYS:**
1. Dump layout first (`android layout -p`)
2. Compute scaled coords
3. Then `adb shell input tap` — never guess pixels.

## CONTAINER CONFIG — DECISION MAKING

From the official docs
(https://deepwiki.com/utkarshdalal/GameNative/6-container-and-emulation-system):

### Two container variants
- **glibc**: standard Linux userland + Box64 x86_64 emulation. Uses Wine 9.2 x86_64.
  More mature/compatible for older x86 games. PRoot filesystem isolation.
- **bionic**: Android Bionic libc + Box64 or FEXCore, ARM64EC Wine builds
  (proton-9.0-arm64ec / proton-10.0-arm64ec). Best raw perf on ARM64EC,
  but newer and less proven with old/odd games.

Rule of thumb: **old/2D/quirky games → try glibc first. Modern DX11/12 → bionic.**

### Emulator (for WoW64 / 32-bit processes)
- **Box64**: `box64Version`, `box64Preset` (Performance | Compatibility).
- **FEXCore**: `fexcorePreset` (Fastest | Fast | Slow | Slowest accuracy).
  Higher accuracy = slower. Start at "Fast" or "Compatibility".

### Graphics driver
Driver | Target | Notes
-------|--------|------
Wrapper / Wrapper-v2 | all (Turnip) | default; Zink+Mesa Vulkan path
Turnip | Adreno | direct Turnip, Glibc only
VirGL  | all    | software Vulkan (slow, very compatible)
Adreno | Adreno | proprietary
Vortek | all    | Zink + Mesa

### Display Renderer
- **Vulkan** (default with Wrapper) — needs a working Vulkan ICD.
- **OpenGL** — use when Vulkan path is broken; pairs with WineD3D.

### DX Wrapper — THE usual black-screen culprit
Wrapper | Use for
--------|--------
DXVK    | DX9–DX11 games on Vulkan. Fast but breaks old DirectDraw titles.
VKD3D   | DX12 only.
WineD3D | Wine's OpenGL DX translation. Most compatible for OLD games
        | (DirectDraw / DX7–9 2D). Switch Display Renderer to OpenGL too.
CNC DDraw | Purpose-built for old 2D DirectDraw games (C&C, Broken Sword,
        | point-and-click). Config emits `renderer=gl` — needs OpenGL display
        | renderer, NOT Vulkan. If paired with Vulkan+zink it often black-screens.

### Black screen / "No Graphics" triage order
1. Raise **display brightness** (Quick Menu + button) — it defaults to 10%.
2. Check `android layout -p`: a single full-screen clickable surface means the
   XServer is up but the game window isn't painting.
3. Switch DX wrapper: old 2D game → **WineD3D** (set Display Renderer = OpenGL)
   or **CNC DDraw** (also needs OpenGL renderer). Avoid DXVK for DirectDraw.
4. Try the other **container variant** (glibc ↔ bionic).
5. Drop emulator preset to **Compatibility** / **Slowest** for accuracy.
6. Check logcat for `XRequestError` / `BadWindow` — usually a renderer mismatch.

### Graphics driver config string (advanced)
`vulkanVersion=1.3,version=turnip26.0.0_R8,presentMode=mailbox,
syncFrame=0,disablePresentWait=0,resourceType=auto,bcnEmulation=auto,
bcnEmulationType=compute,maxDeviceMemory=4096`

### "Use known config"
Options sheet has **Use known config** (`621,1550` in the options list) which
applies a community/GPU-matched preset. Try it first, but if it black-screens,
fall back to the WineD3D/CNC DDraw path above.

## Example session
```bash
adb devices                                   # confirm connected
android layout -p                             # find Play button center
adb shell input tap 238 705                   # launch
sleep 20
android layout -p                             # is XServer up? single surface = no paint
adb logcat -d -t 300 --pid=$(adb shell pidof app.gamenative) | grep -i ddraw
# black screen → back out, edit container, set WineD3D + OpenGL renderer, retry
```

## CONTAINER EDIT FLOW (by adb taps)
```
# From game detail screen:
adb shell input tap 774 706   # Options gear
android layout -p             # find "Edit container" center
adb shell input tap <cx> <cy> # tap it
# In Edit Container dialog, navigate tabs:
# General tab: Container Variant → glibc | Wine Version → wine-9.2-x86_64
# Graphics tab: DX Wrapper → WineD3D | Display Renderer → OpenGL
# Save, then retry
```

## CONTAINER CONFIG DECISION TREE (QUICK REF)

```
Game type?
├─ Modern DX11/12 (2018+) → bionic + ARM64EC Wine + DXVK/VKD3D + Vulkan
├─ 32-bit DX9 3D (2005–2015) → try glibc + Wine 9.x + DXVK + Vulkan first
└─ OLD 2D / DirectDraw / DX7-9 2D (pre-2010) → glibc + Wine 9.x + WineD3D + OpenGL
   │
   ├─ Still black? → try CNC DDraw + OpenGL (NOT Vulkan)
   ├─ Still black? → bionic + ARM64EC + WineD3D + OpenGL
   └─ Still black? → Box64 Compatibility preset + WineD3D + OpenGL
```

## COMMON BROKEN-GAME FIXES (from DeepWiki docs)

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Black screen, XServer up | Renderer mismatch | Switch DX wrapper + matching display renderer |
| "No Graphics" / 10% brightness | Brightness default | Quick Menu → Brightness + |
| "DirectX Error" | Wrong DX wrapper | DXVK→WineD3D for old games |
| Game launches, immediate crash | 32-bit/WoW64 emulation fail | Switch container variant, Box64 Compat preset |
| "DirectDraw error" / black intro video | CNC DDraw + Vulkan+zink | CNC DDraw needs OpenGL renderer |
| XRequestError / BadWindow | XServer/graphics mismatch | Switch Display Renderer (Vulkan↔OpenGL) |

## USEFUL ADB COMMANDS

```bash
# Get GameNative PID
adb shell pidof app.gamenative

# Live logcat filtered to game
adb logcat -d -t 500 --pid=$(adb shell pidof app.gamenative)

# Dump UI tree with centers
android layout -p

# Tap at physical coords
adb shell input tap X Y

# Swipe (x1 y1 x2 y2 duration_ms)
adb shell input swipe 540 1800 540 800 300

# Key event
adb shell input keyevent KEYCODE_BACK

# Screen size (physical)
adb shell wm size
```