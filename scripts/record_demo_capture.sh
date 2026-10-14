#!/bin/bash
# runanchor demo-video capture driver — runs inside a FRESH Terminal.app
# window titled "runanchor — live demo", paired with
# scripts/capture_terminal_window.swift recording that window.
#
# Flow (see submit/demo-script.md for the scene map):
#   1. Open a fresh Terminal window, set title + size, run this script there.
#   2. Start capture: ./capture_terminal_window "runanchor — live demo" out.mov &
#   3. This script sleeps 3s (rec_ready) so the recorder sees a clean window.
#   4. Each scene purges scrollback first — no stale prompts can bleed in.
#   5. Section boundaries are logged (epoch seconds) to $LOG for the
#      assembler (scripts/assemble_demo_video.sh).
#
# Everything on screen is real output — `runanchor` resolves to the wrapper
# created below, which runs the real CLI against a scratch ledger.

export TERM="${TERM:-xterm-256color}"
export PS1='$ '

RA="$(cd "$(dirname "$0")/.." && pwd)"
WORK="${RA_CAPTURE_DIR:-/tmp/ra-capture}"
LOG="$WORK/sections.log"
DEMODIR="$WORK/emptydir"

# capture wrapper: real CLI, scratch ledger — screen shows clean `runanchor <cmd>`
mkdir -p "$WORK/bin"
cat > "$WORK/bin/runanchor" <<EOF
#!/bin/bash
exec env PYTHONPATH="$RA/app" \\
  python3 -m runanchor.cli --ledger "$WORK/demo-ledger.jsonl" "\$@"
EOF
chmod +x "$WORK/bin/runanchor"
export PATH="$WORK/bin:$PATH"

rm -f "$WORK/demo-ledger.jsonl" "$LOG"
mkdir -p "$DEMODIR"
printf '\033]2;runanchor — live demo\007'
printf '\033[3J\033[H\033[2J'   # purge scrollback + clear visible

mark() { printf '%s %s\n' "$(python3 -c 'import time;print(time.time())')" >> "$LOG"; }
type_cmd() { printf '$ %s\n' "$1"; sleep 0.9; }
hold() { sleep "$1"; }

mark rec_ready
sleep 3.0

# ---- scene 1: hook — empty directory ----
mark s1_start
printf '\033[3J\033[H\033[2J'
cd "$DEMODIR"
type_cmd "pwd && ls"
pwd && ls
hold 5
mark s1_end

# ---- scene 2: runanchor demo (real run) ----
mark s2_start
printf '\033[3J\033[H\033[2J'
cd "$RA"
type_cmd "runanchor demo"
runanchor demo
hold 8
mark s2_end

# ---- scene 3: list + show adopted receipt ----
mark s3_start
printf '\033[3J\033[H\033[2J'
type_cmd "runanchor list"
runanchor list
hold 3
ADOPTED=$(runanchor list 2>/dev/null | awk '/state=adopted/{print $1; exit}')
type_cmd "runanchor show $ADOPTED"
[ -n "$ADOPTED" ] && runanchor show "$ADOPTED"
hold 5
mark s3_end

# ---- scene 4: hash chain on the REAL bench ledger + receipt fields ----
mark s4_start
printf '\033[3J\033[H\033[2J'
type_cmd "runanchor check --ledger eval/bench-ledger-20261001-v4.jsonl"
runanchor check --ledger "$RA/eval/bench-ledger-20261001-v4.jsonl"
hold 3
type_cmd "head -1 eval/bench-ledger-20261001-v4.jsonl | cut -c1-160"
head -1 "$RA/eval/bench-ledger-20261001-v4.jsonl" | cut -c1-160
hold 4
type_cmd "runanchor show $ADOPTED"
[ -n "$ADOPTED" ] && runanchor show "$ADOPTED"
hold 6
mark s4_end

# ---- scene 5: measured gate — committed bench matrix + corpus oracle ----
mark s5_start
printf '\033[3J\033[H\033[2J'
type_cmd "sed -n '24,29p' eval/bench-20261001-v4.md"
sed -n '24,29p' "$RA/eval/bench-20261001-v4.md"
hold 6
type_cmd "ls app/corpus | head -8"
ls "$RA/app/corpus" | head -8
hold 2
type_cmd "ls app/corpus/seeded-cwd-data/oracle"
ls "$RA/app/corpus/seeded-cwd-data/oracle"
hold 5
mark s5_end

mark done
printf '\033[3J\033[H\033[2J'
echo "capture complete"
sleep 2
