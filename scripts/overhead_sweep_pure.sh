#!/usr/bin/env bash
set -euo pipefail

# -----------------------------
# Pure BOS overhead (Option B): NO attacker
# -----------------------------
CORES="0,1"
W_LIST=(0 4 8 12 14 16)
REPS=5

RUNS=100
N=20
SEED=42
MEM_KB=8192

# Optional: make victim params explicit (stability)
VICTIM_WORKERS=2
VICTIM_ITERS=200000

# Derived
JOBS_TOTAL=$((RUNS * N))

# Output
TS="$(date +%Y%m%d_%H%M%S)"
OUT_DIR="out"
LOG_DIR="${OUT_DIR}/logs"
CSV_DIR="${OUT_DIR}/csv"
SUMMARY_CSV="${CSV_DIR}/overhead_pure_summary_${TS}.csv"

mkdir -p "${LOG_DIR}" "${CSV_DIR}"

# Summary CSV header
echo "timestamp,mode,W,reps,runs,n,jobs_total,seed,mean_real_s,std_real_s,overhead_vs_W0,throughput_jobs_per_s,throughput_runs_per_s,rep_real_s_list" \
  > "${SUMMARY_CSV}"

# Global victim pid cleanup (in case of abort)
VPID=""
cleanup() {
  if [[ -n "${VPID}" ]]; then
    kill "${VPID}" >/dev/null 2>&1 || true
    wait "${VPID}" >/dev/null 2>&1 || true
    VPID=""
  fi
}
trap cleanup EXIT

wait_for_socket() {
  local sock="$1"
  for _ in $(seq 1 200); do
    [[ -S "${sock}" ]] && return 0
    sleep 0.05
  done
  echo "[ERROR] socket did not appear: ${sock}" >&2
  return 1
}

# Compute mean/std with python (sample std if n>1)
py_stats() {
  python3 - "$@" <<'PY'
import sys, math
xs = [float(x) for x in sys.argv[1:]]
n = len(xs)
mean = sum(xs)/n
if n > 1:
  var = sum((x-mean)**2 for x in xs)/(n-1)
  std = math.sqrt(var)
else:
  std = 0.0
print(f"{mean:.6f} {std:.6f}")
PY
}

run_mode() {
  local mode="$1"   # cpu | mem
  local baseline_mean=""  # mean time for W=0 within this mode

  echo "=== MODE=${mode} (pure, no attack) ==="
  for W in "${W_LIST[@]}"; do
    echo "--- W=${W} (REPS=${REPS}) ---"
    local times=()

    for rep in $(seq 1 "${REPS}"); do
      echo "[${mode}] W=${W} rep=${rep}/${REPS}"

      # Unique sock per mode to avoid confusion
      local sock="victim_${mode}.sock"

      # Ensure clean links
      rm -f "${sock}" "${OUT_DIR}/victim.sock"

      # Start victim (pinned)
      if [[ "${mode}" == "cpu" ]]; then
        taskset -c "${CORES}" python3 -u ./src/victim.py \
          --sock "${sock}" --mode cpu \
          --workers "${VICTIM_WORKERS}" --iters "${VICTIM_ITERS}" \
          --scrub-window "${W}" --scrub-seed "${SEED}" \
          > "${LOG_DIR}/victim_cpu_W${W}_rep${rep}_${TS}.log" 2>&1 &
      else
        taskset -c "${CORES}" python3 -u ./src/victim.py \
          --sock "${sock}" --mode mem --mem-kb "${MEM_KB}" \
          --workers "${VICTIM_WORKERS}" --iters "${VICTIM_ITERS}" \
          --scrub-window "${W}" --scrub-seed "${SEED}" \
          > "${LOG_DIR}/victim_mem_W${W}_rep${rep}_${TS}.log" 2>&1 &
      fi
      VPID=$!

      # Wait for socket
      wait_for_socket "${sock}"

      # Link socket into out/
      ln -sf "../${sock}" "${OUT_DIR}/victim.sock"

      # Timed dataset run (NO ATTACK FLAGS)
      local timefile="${LOG_DIR}/time_pure_${mode}_W${W}_rep${rep}_${TS}.txt"
      local outcsv="${CSV_DIR}/overhead_pure_${mode}_W${W}_rep${rep}_r${RUNS}.csv"

      /usr/bin/time -p taskset -c "${CORES}" python3 ./scripts/run_dataset.py \
        --runs "${RUNS}" --n "${N}" \
        --label "${mode^^}_PURE_OVH" \
        --out "${outcsv}" \
        --scrub-window "${W}" --scrub-seed "${SEED}" \
        2> "${timefile}"

      # Extract real seconds
      local real_s
      real_s="$(grep -E '^real ' "${timefile}" | awk '{print $2}' | tail -n1)"
      if [[ -z "${real_s}" ]]; then
        echo "[ERROR] could not parse real time from ${timefile}" >&2
        exit 1
      fi
      times+=("${real_s}")

      # Stop victim
      cleanup
    done

    # Stats for this W
    read -r mean_s std_s < <(py_stats "${times[@]}")

    # Set baseline for this mode at W=0 (assumes W_LIST starts with 0)
    if [[ -z "${baseline_mean}" ]]; then
      baseline_mean="${mean_s}"
    fi

    # overhead factor vs baseline W=0 (for this mode)
    overhead="$(python3 - <<PY
b=float("${baseline_mean}")
m=float("${mean_s}")
print(f"{(m/b):.6f}" if b>0 else "nan")
PY
)"

    # Throughput
    jobs_per_s="$(python3 - <<PY
m=float("${mean_s}")
print(f"{(${JOBS_TOTAL})/m:.6f}" if m>0 else "nan")
PY
)"
    runs_per_s="$(python3 - <<PY
m=float("${mean_s}")
print(f"{(${RUNS})/m:.6f}" if m>0 else "nan")
PY
)"

    rep_list="$(IFS=';'; echo "${times[*]}")"

    echo "[SUMMARY] mode=${mode} W=${W} mean=${mean_s}s std=${std_s}s overhead=${overhead}x jobs/s=${jobs_per_s} runs/s=${runs_per_s}"

    echo "${TS},${mode},${W},${REPS},${RUNS},${N},${JOBS_TOTAL},${SEED},${mean_s},${std_s},${overhead},${jobs_per_s},${runs_per_s},${rep_list}" \
      >> "${SUMMARY_CSV}"
  done
}

cd ~/projects/ordleak

# If you want shutdown without password prompt, warm sudo once:
if [[ "${EUID}" -ne 0 ]]; then
  sudo -v || true
fi

# CPU block first, then MEM block
run_mode cpu
run_mode mem

echo "All done. Summary written to: ${SUMMARY_CSV}"

echo "Shutting down now..."
if [[ "${EUID}" -eq 0 ]]; then
  shutdown -h now
else
  sudo shutdown -h now
fi
