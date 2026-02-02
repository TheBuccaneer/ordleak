#!/usr/bin/env bash
set -euo pipefail

# -----------------------------
# Config (matches your Stage2 sweep)
# -----------------------------
CORES="0,1"
W_LIST=(0 4 8 12 14 16)
REPS=5

RUNS=100
N=20
ATT_PROCS=16
ATT_SECS=5
SEED=42
MEM_KB=8192

# Derived
JOBS_TOTAL=$((RUNS * N))

# Output
TS="$(date +%Y%m%d_%H%M%S)"
OUT_DIR="out"
LOG_DIR="${OUT_DIR}/logs"
CSV_DIR="${OUT_DIR}/csv"
SUMMARY_CSV="${CSV_DIR}/overhead_summary_${TS}.csv"

mkdir -p "${LOG_DIR}" "${CSV_DIR}"

# Summary CSV header
echo "timestamp,mode,W,reps,runs,n,jobs_total,attack_procs,attack_secs,seed,mean_real_s,std_real_s,overhead_vs_W0,throughput_jobs_per_s,throughput_runs_per_s,rep_real_s_list" \
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

# Compute mean/std with python (population std or sample std? we'll use sample std if n>1)
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

  echo "=== MODE=${mode} ==="
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
          --scrub-window "${W}" --scrub-seed "${SEED}" \
          > "${LOG_DIR}/victim_cpu_W${W}_rep${rep}_${TS}.log" 2>&1 &
      else
        taskset -c "${CORES}" python3 -u ./src/victim.py \
          --sock "${sock}" --mode mem --mem-kb "${MEM_KB}" \
          --scrub-window "${W}" --scrub-seed "${SEED}" \
          > "${LOG_DIR}/victim_mem_W${W}_rep${rep}_${TS}.log" 2>&1 &
      fi
      VPID=$!

      # Wait for socket
      wait_for_socket "${sock}"

      # Link socket into out/
      ln -sf "../${sock}" "${OUT_DIR}/victim.sock"

      # Timed dataset run
      local timefile="${LOG_DIR}/time_${mode}_W${W}_rep${rep}_${TS}.txt"
      local outcsv="${CSV_DIR}/overhead_${mode}_W${W}_rep${rep}_r${RUNS}.csv"

      /usr/bin/time -p taskset -c "${CORES}" python3 ./scripts/run_dataset.py \
        --runs "${RUNS}" --n "${N}" \
        --attack --attack-procs "${ATT_PROCS}" --attack-seconds "${ATT_SECS}" \
        --label "${mode^^}_OVH" \
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

    # Stats for this W (5 reps)
    read -r mean_s std_s < <(py_stats "${times[@]}")

    if [[ -z "${baseline_mean}" ]]; then
      baseline_mean="${mean_s}"  # W=0 baseline for this mode (since W_LIST starts with 0)
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

    # Append to summary CSV
    echo "${TS},${mode},${W},${REPS},${RUNS},${N},${JOBS_TOTAL},${ATT_PROCS},${ATT_SECS},${SEED},${mean_s},${std_s},${overhead},${jobs_per_s},${runs_per_s},${rep_list}" \
      >> "${SUMMARY_CSV}"
  done
}

cd ~/projects/ordleak

# CPU-only block first
run_mode cpu

# MEM block next (as requested)
run_mode mem

echo "All done. Summary written to: ${SUMMARY_CSV}"

# Shutdown at the end
echo "Shutting down now..."
shutdown -h now
