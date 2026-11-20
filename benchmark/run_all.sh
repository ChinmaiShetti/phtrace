#!/bin/sh
# Runs every index REPS times, each in a fresh process, rotating the order to spread out drift.
#   INDEXES  space-separated list (default: all four configurations)
#   HB_ARGS  extra ALEX-HB flags, e.g. "--hb-window 4096 --hb-hot 64 --hb-migrate 4"
set -eu
REPS="${REPS:-5}"
INDEXES="${INDEXES:-btree alex alexhb alexhb-nomig}"
HB_ARGS="${HB_ARGS:-}"
TRACES="${TRACES:-/traces}"
OUT="${OUT:-/results}"
mkdir -p "$OUT"
rm -f "$OUT/results.csv"
{
  echo "date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "compiler: $(g++ --version | head -1)"
  echo "cpu: $(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2 | sed 's/^ //')"
  echo "cores: $(nproc)"
  echo "memory: $(grep MemTotal /proc/meminfo | awk '{print $2/1024 " MB"}')"
  echo "kernel: $(uname -r)"
  echo "alex_commit: $(git -C /bench/third_party/alex rev-parse HEAD)"
  echo "tlx_commit: $(git -C /bench/third_party/tlx rev-parse HEAD)"
  echo "reps: $REPS"
  echo "indexes: $INDEXES"
  echo "hb_args: ${HB_ARGS:-defaults W=4096 H=64 M=4}"
} > "$OUT/environment.txt"
cat "$OUT/environment.txt"
for rep in $(seq 1 "$REPS"); do
  # rotate the list by (rep - 1) positions so each index runs in every slot
  set -- $INDEXES
  shift_by=$(( (rep - 1) % $# ))
  i=0
  while [ "$i" -lt "$shift_by" ]; do first="$1"; shift; set -- "$@" "$first"; i=$((i + 1)); done
  for idx in "$@"; do
    # shellcheck disable=SC2086
    ./build/bench --index "$idx" --traces "$TRACES" --rep "$rep" --out "$OUT/results.csv" $HB_ARGS
  done
done
echo "done: $OUT/results.csv"
