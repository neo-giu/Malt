#!/usr/bin/env bash
# Card runner: one task card = one fresh headless Claude session = one commit, run in sequence.
# Usage (repo root, Git Bash):  bash tools/cards/run_cards.sh [--no-gate] T02 T03 T04
# Config: tools/cards/cards.env (sourced if present), then environment variables:
#   CARDS_BATCH   docs/specs/<batch> holding tasks/RULES.md and the cards     (required)
#   CARDS_CHECKS  fast check command run after every card; non-zero = fail     (required)
#   CARDS_GATE    slow acceptance command run once after the wave; gets the run dir as $1 (optional)
#   CARDS_MODEL   worker model (default claude-sonnet-5-5)   CARDS_EFFORT (default medium)
#   CARDS_BUDGET  USD cap per card (default 4)               CARDS_BRANCH (default: current branch)
#   CARDS_PY      python for parsing session output (default: first of .venv, py -3, python3, python)
#   CLAUDE_BIN    CLI path (default: claude on PATH, else newest desktop-app bundled copy)
set -u

[[ -f tools/cards/cards.env ]] && source tools/cards/cards.env

BATCH="${CARDS_BATCH:?set CARDS_BATCH in tools/cards/cards.env}"
CHECKS="${CARDS_CHECKS:?set CARDS_CHECKS in tools/cards/cards.env}"
GATE_CMD="${CARDS_GATE:-}"
MODEL="${CARDS_MODEL:-claude-sonnet-5-5}"
EFFORT="${CARDS_EFFORT:-medium}"
BUDGET="${CARDS_BUDGET:-4}"
BRANCH="${CARDS_BRANCH:-$(git symbolic-ref --short HEAD 2>/dev/null)}"
TASKS="docs/specs/$BATCH/tasks"

GATE=1
IDS=()
for a in "$@"; do
  if [[ "$a" == "--no-gate" ]]; then GATE=0; else IDS+=("$a"); fi
done
[[ ${#IDS[@]} -gt 0 ]] || { echo "usage: run_cards.sh [--no-gate] T02 T03 ..."; exit 2; }

find_py() {
  if [[ -n "${CARDS_PY:-}" ]]; then echo "$CARDS_PY"; return; fi
  for c in .venv/Scripts/python .venv/bin/python "py -3" python3 python; do
    if $c -c "import json" >/dev/null 2>&1; then echo "$c"; return; fi
  done
}
find_claude() {
  if [[ -n "${CLAUDE_BIN:-}" ]]; then echo "$CLAUDE_BIN"; return; fi
  if command -v claude >/dev/null 2>&1; then command -v claude; return; fi
  local base="${APPDATA:-$HOME/AppData/Roaming}/Claude/claude-code"
  base="$(cygpath -u "$base" 2>/dev/null || echo "$base")"
  ls -d "$base"/*/*/claude.exe 2>/dev/null | sort -V | tail -n 1
}
PY="$(find_py)"
CLAUDE="$(find_claude)"
[[ -n "$PY" ]] || { echo "no python found; set CARDS_PY"; exit 2; }
[[ -x "$CLAUDE" ]] || { echo "claude CLI not found; set CLAUDE_BIN"; exit 2; }

[[ -n "$BRANCH" && "$(git symbolic-ref --short HEAD 2>/dev/null)" == "$BRANCH" ]] || { echo "not on branch $BRANCH"; exit 2; }
[[ -z "$(git status --porcelain)" ]] || { echo "tree not clean; commit or stash first"; exit 2; }
[[ -f "$TASKS/RULES.md" ]] || { echo "missing $TASKS/RULES.md"; exit 2; }

STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="build/cards/$STAMP"
mkdir -p "$OUT"
SUMMARY="$OUT/summary.md"
{
  echo "# Card run $STAMP"
  echo
  echo "- Batch: $BATCH · branch: $BRANCH · model: $MODEL ($EFFORT) · budget/card: \$$BUDGET"
  echo "- Cards: ${IDS[*]}"
  echo
} > "$SUMMARY"

TOTAL_COST=0
DONE_IDS=()
finish() {
  { echo; echo "Done cards: ${DONE_IDS[*]:-none}"; echo "Total cost: \$$TOTAL_COST"; } >> "$SUMMARY"
  echo "RUN END ($1). Orchestrator: read $SUMMARY"
  exit "$2"
}
stop() { echo "- **STOPPED at $1:** $2" >> "$SUMMARY"; echo "=== STOP at $1: $2"; finish "stopped at $1" 1; }

for ID in "${IDS[@]}"; do
  CARD="$(ls "$TASKS/$ID"-*.md 2>/dev/null | head -n 1)"
  [[ -n "$CARD" ]] || stop "$ID" "no card file $TASKS/$ID-*.md"
  BEFORE="$(git rev-parse HEAD)"
  echo "=== $ID: start $(date +%H:%M:%S) ($CARD)"

  PROMPT="Run the task card $CARD. Follow $TASKS/RULES.md, with these changes:
- Work directly in this checkout, on branch $BRANCH. Do not create branches or worktrees. Do not push.
- Run every command in the foreground. The session must end on the Report.
- Stay inside the card's fence. If you need a file outside it, stop and report it.
- When every 'Done when' check that you can run passes, commit only the files you changed, with the message '$ID: <what changed>' followed by a blank line and the Co-Authored-By line your own system instructions give for your model.
- If you are blocked, or a check fails and you cannot fix it inside the card's fence, do not commit. Leave your changes in the tree.
- Your last message is the card's Report (max 15 lines). Its FIRST line is 'DONE' or 'BLOCKED: <reason>'."

  "$CLAUDE" -p "$PROMPT" \
    --model "$MODEL" --effort "$EFFORT" \
    --tools "Read,Edit,Write,Glob,Grep,Bash" \
    --allowedTools "Read" "Edit" "Write" "Glob" "Grep" "Bash" \
    --disallowedTools "Bash(git push:*)" "Bash(git reset:*)" "Bash(git clean:*)" "Bash(git worktree:*)" \
      "Bash(git checkout:*)" "Bash(git switch:*)" "Bash(git branch:*)" "Bash(git rebase:*)" \
      "Bash(git stash:*)" "Bash(rm -rf:*)" \
    --permission-mode acceptEdits --permission-prompts none \
    --strict-mcp-config --disable-slash-commands \
    --max-budget-usd "$BUDGET" \
    --output-format json > "$OUT/$ID.json" 2> "$OUT/$ID.err"
  CODE=$?

  $PY - "$OUT/$ID.json" "$OUT/$ID.log" "$OUT/$ID.cost" <<'EOF'
import json, sys
src, log, cost = sys.argv[1:4]
try:
    events = json.load(open(src, encoding="utf-8"))
    if isinstance(events, dict):
        events = [events]
    final = [e for e in events if e.get("type") == "result"][-1]
    text, usd, turns = final.get("result", ""), float(final.get("total_cost_usd") or 0), final.get("num_turns")
except Exception as e:
    text, usd, turns = f"(runner: could not read session output: {e})", 0.0, None
open(log, "w", encoding="utf-8").write(text + "\n")
open(cost, "w").write(f"{usd:.2f} {turns}\n")
EOF
  read -r USD TURNS < "$OUT/$ID.cost"
  TOTAL_COST="$(awk "BEGIN{printf \"%.2f\", $TOTAL_COST + $USD}")"
  FIRST="$(sed '/^[[:space:]]*$/d' "$OUT/$ID.log" | head -n 1)"

  {
    echo "## $ID · $(basename "$CARD") · \$$USD · $TURNS turns"
    echo
    echo '```'
    tail -n 20 "$OUT/$ID.log"
    echo '```'
  } >> "$SUMMARY"

  [[ $CODE -eq 0 ]] || stop "$ID" "claude exited $CODE (see $OUT/$ID.err; often the usage limit or the budget cap)"
  DIRTY="$(git status --porcelain)"
  AFTER="$(git rev-parse HEAD)"
  if [[ "$FIRST" == BLOCKED* ]]; then
    if [[ -z "$DIRTY" && "$AFTER" == "$BEFORE" ]]; then
      echo "- skipped: clean BLOCKED" >> "$SUMMARY"; echo "=== $ID: SKIP (clean BLOCKED)"; continue
    fi
    stop "$ID" "BLOCKED with changes left in the tree"
  fi
  [[ "$FIRST" == DONE* ]] || stop "$ID" "Report does not start with DONE or BLOCKED"
  [[ "$AFTER" != "$BEFORE" ]] || stop "$ID" "no new commit"
  [[ -z "$DIRTY" ]] || stop "$ID" "uncommitted changes left"
  bash -c "$CHECKS" > "$OUT/$ID.checks.txt" 2>&1 || stop "$ID" "checks fail after commit (see $OUT/$ID.checks.txt)"
  LINE="verified: commit $(git rev-parse --short HEAD), checks ok ($(tail -n 1 "$OUT/$ID.checks.txt"))"
  echo "- $LINE" >> "$SUMMARY"
  echo "=== $ID: $LINE"
  DONE_IDS+=("$ID")
done

if [[ $GATE -eq 1 && -n "$GATE_CMD" ]]; then
  echo "=== gate"
  bash -c "$GATE_CMD \"\$1\"" _ "$OUT" > "$OUT/gate.txt" 2>&1; GCODE=$?
  { echo; echo "## Gate (exit $GCODE)"; echo; echo '```'; cat "$OUT/gate.txt"; echo '```'; } >> "$SUMMARY"
  [[ $GCODE -eq 0 ]] || finish "gate failed" 3
fi
finish "ok" 0
