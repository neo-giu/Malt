#!/usr/bin/env bash
# Usage: render.sh FILE.blend OUT_DIR FRAMES [SETUP]   (GUI launch, quits without saving; refer to render_gui.py)
# On timeout the whole Blender process tree is killed, so no Malt server process is left behind.
BLENDER="${BLENDER:-H:/SteamLibrary/steamapps/common/Blender/blender.exe}"
LIMIT="${RENDER_TIMEOUT:-180}"
OUT="$(mkdir -p "$2" && cd "$2" && pwd -W)"; HERE="$(cd "$(dirname "$0")" && pwd -W)"
BLENDER_USER_SCRIPTS="${MALT_DEV_SCRIPTS:-H:/GameDev/MaltDev/scripts}" "$BLENDER" "$1" \
  --python "$HERE/render_gui.py" -- "$OUT" "$3" ${4:-} > "$OUT/stdout.txt" 2>&1 &
PID=$!
WINPID="$(cat /proc/$PID/winpid 2>/dev/null)"
for ((i = 0; i < LIMIT; i++)); do
  kill -0 $PID 2>/dev/null || break
  sleep 1
done
if kill -0 $PID 2>/dev/null; then
  echo "ERROR: timeout after ${LIMIT}s, killing Blender tree (winpid $WINPID)"
  [ -n "$WINPID" ] && taskkill //PID "$WINPID" //T //F > /dev/null 2>&1
  kill -9 $PID 2>/dev/null
  cat "$OUT/log.txt" 2>/dev/null
  exit 1
fi
wait $PID
cat "$OUT/log.txt"
grep -q "^MALT_FILE .*GameDev.Malt" "$OUT/log.txt" || { echo "ERROR: not rendered with the fork"; exit 1; }
grep -q "Traceback" "$OUT/log.txt" && exit 1
grep -q "MaltGraphExecutionException" "$OUT/stdout.txt" && { echo "ERROR: Malt errors in stdout.txt"; exit 1; }
exit 0
