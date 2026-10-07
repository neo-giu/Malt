#!/usr/bin/env bash
# Usage: bash tools/pixelart/render.sh FILE.blend OUT_DIR FRAMES [SETUP]
# Opens a Blender WINDOW for a few seconds (Malt needs it), renders with the fork (dev install), quits without saving.
BLENDER="${BLENDER:-H:/SteamLibrary/steamapps/common/Blender/blender.exe}"
OUT="$(mkdir -p "$2" && cd "$2" && pwd -W)"; HERE="$(cd "$(dirname "$0")" && pwd -W)"
BLENDER_USER_SCRIPTS="${MALT_DEV_SCRIPTS:-H:/GameDev/MaltDev/scripts}" timeout 300 "$BLENDER" "$1" \
  --python "$HERE/render_gui.py" -- "$OUT" "$3" ${4:-} > "$OUT/stdout.txt" 2>&1
cat "$OUT/log.txt"
grep -q "^MALT_FILE .*GameDev.Malt" "$OUT/log.txt" || { echo "ERROR: not rendered with the fork"; exit 1; }
grep -q "Traceback" "$OUT/log.txt" && exit 1 || exit 0
