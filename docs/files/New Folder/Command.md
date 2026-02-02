# ordleak — Command.md (Script inventory + example calls)

This file is a quick "what does each script do" inventory plus copy/paste examples.
Paths are consistent with the current `out/csv/` layout (Threadripper is the reference).

## `src/victim.py`

**Description**  
Starts the victim server. It executes jobs in parallel and only reveals the **rank-only completion order** as `DONE <id>`.

**Key notes**
- Opens a Unix socket (`--sock`) and waits for `RUN <n>` requests (from `client_rank_only.py` / `run_dataset.py`).
- Emits `DONE <id>` in the *actual* completion order.
- Supports **secret modes** via `--mode cpu|mem`; `--mem-kb` controls the buffer size in MEM mode.
- Supports **BOS scrubber** via `--scrub-window W` and `--scrub-seed SEED` (see below).

**Example calls**

CPU mode (typical Stage 1):
```bash
cd ~/projects/ordleak
rm -f out/victim.sock out/victim_cpu.sock
taskset -c 0,1 python3 -u src/victim.py --sock out/victim_cpu.sock --mode cpu --workers 2 --iters 200000
ln -sf victim_cpu.sock out/victim.sock
```

MEM mode (typical Stage 2):
```bash
cd ~/projects/ordleak
rm -f out/victim.sock out/victim_mem.sock
taskset -c 0,1 python3 -u src/victim.py --sock out/victim_mem.sock --mode mem --mem-kb 8192 --workers 2 --iters 200000
ln -sf victim_mem.sock out/victim.sock
```

---

## BOS Scrubber flags (`src/victim.py`)

**Description**  
Budgeted Order Scrubbing (BOS) v1 — a defense that buffers completion IDs and releases them in a keyed pseudorandom order to reduce order-based information leakage.

**Flags**
| Flag | Default | Description |
|------|---------|-------------|
| `--scrub-window W` | 0 | Buffer size. `W=0`: scrubber off (baseline). `W=1`: passthrough (no reorder). `W>=2`: buffer W IDs, flush in permuted order. |
| `--scrub-seed SEED` | 42 | PRNG seed for deterministic shuffle. Treat as server-side secret in production. |

**Threat model (BOS)**
- Seed is a **server-side secret** (not observable by attacker).
- Window size W **may be observable** (output is bursty).
- PRNG state is **continuous** (not reset per flush), so identical ID sets don't always get identical permutations.

**Example calls (scrubber enabled)**

CPU mode with scrubber W=8:
```bash
cd ~/projects/ordleak
rm -f out/victim.sock out/victim_cpu.sock
taskset -c 0,1 python3 -u src/victim.py \
    --sock out/victim_cpu.sock \
    --mode cpu --workers 2 --iters 200000 \
    --scrub-window 8 --scrub-seed 42
ln -sf victim_cpu.sock out/victim.sock
```

MEM mode with scrubber W=16:
```bash
cd ~/projects/ordleak
rm -f out/victim.sock out/victim_mem.sock
taskset -c 0,1 python3 -u src/victim.py \
    --sock out/victim_mem.sock \
    --mode mem --mem-kb 8192 --workers 2 --iters 200000 \
    --scrub-window 16 --scrub-seed 42
ln -sf victim_mem.sock out/victim.sock
```

---

## `src/client_rank_only.py`

**Description**  
Minimal client that requests `RUN <n>` from the victim and reads only the rank-only `DONE <id>` sequence.

**Key notes**
- Acts as the "observer" (no timing, only order).
- Usually used **indirectly** via `scripts/run_dataset.py`.

**Direct example**
```bash
cd ~/projects/ordleak
python3 src/client_rank_only.py --sock out/victim.sock --n 20
```

---

## `src/attacker.py`

**Description**  
Creates CPU contention (busy loops) with `--procs` worker processes for `--seconds` seconds.

**Key notes**
- Typically launched by `scripts/run_dataset.py` when `--attack` is set.
- For an **off-core negative control**, you can run it in a separate terminal pinned away from the victim cores.
- This script does **not** write CSVs; it only generates load.

**Example (off-core negative-control load)**
Threadripper example:
```bash
cd ~/projects/ordleak
taskset -c 2-31 python3 -u src/attacker.py --procs 32 --seconds 600
```

Intel i9-7900X example:
```bash
cd ~/projects/ordleak
taskset -c 2-19 python3 -u src/attacker.py --procs 20 --seconds 600
```

---

## `scripts/run_dataset.py`

**Description**  
Runs many trials, extracts features from rank-only completion orders (e.g., **ODS**, **GAP_VAR**) and writes/appends them to a CSV.

**Key notes**
- Writes a CSV with at least: `label`, `ods`, `gap_var` (plus optional extra columns depending on version).
- Appends if the output file exists (so you can write BASELINE then ATTACK into the same CSV).
- If `--attack` is set, the attacker is started **internally** (`--attack-procs`, `--attack-seconds`).

**Scrubber flags (recorded in CSV)**
- `--scrub-window W` and `--scrub-seed SEED` are written to CSV columns `scrub_window`, `scrub_seed`.
- They do **not** control the victim; you must start `victim.py` with matching flags.
- This ensures traceability: you can always see which scrubber settings were used for a dataset.

**Example calls**

Stage 1 (presence): `BASELINE` then `ATTACK` into the same file (Intel layout shown)
```bash
cd ~/projects/ordleak
mkdir -p out/csv/stage1/intel_i9_7900x/runset1
taskset -c 0,1 python3 scripts/run_dataset.py --runs 100 --n 20 --label BASELINE --out out/csv/stage1/intel_i9_7900x/runset1/run1_dataset.csv
taskset -c 0,1 python3 scripts/run_dataset.py --runs 100 --n 20 --attack --attack-procs 16 --attack-seconds 5 --label ATTACK --out out/csv/stage1/intel_i9_7900x/runset1/run1_dataset.csv
```

Stage 2 (secret, base): `CPU_BASE` vs `MEM_BASE` into the same file  
Threadripper:
```bash
cd ~/projects/ordleak
mkdir -p out/csv/stage2/threadripper
# CPU victim running + symlink set, then:
taskset -c 0,1 python3 scripts/run_dataset.py --runs 100 --n 20 --label CPU_BASE --out out/csv/stage2/threadripper/secret_tr_base.csv
# MEM victim running + symlink updated, then:
taskset -c 0,1 python3 scripts/run_dataset.py --runs 100 --n 20 --label MEM_BASE --out out/csv/stage2/threadripper/secret_tr_base.csv
```

Intel i9-7900X:
```bash
cd ~/projects/ordleak
mkdir -p out/csv/stage2/i9_7900x
# CPU victim running + symlink set, then:
taskset -c 0,1 python3 scripts/run_dataset.py --runs 100 --n 20 --label CPU_BASE --out out/csv/stage2/i9_7900x/secret_intel_stage2_base.csv
# MEM victim running + symlink updated, then:
taskset -c 0,1 python3 scripts/run_dataset.py --runs 100 --n 20 --label MEM_BASE --out out/csv/stage2/i9_7900x/secret_intel_stage2_base.csv
```

**Defense evaluation (scrubber sweep)**
```bash
cd ~/projects/ordleak
# For each W in {1,2,4,8,16}, start victim with --scrub-window W, then collect:
taskset -c 0,1 python3 scripts/run_dataset.py \
    --runs 50 --n 20 \
    --attack --attack-procs 32 --attack-seconds 5 \
    --label "CPU_ATT_W8" \
    --scrub-window 8 \
    --out out/csv/defense/threadripper/scrub_sweep_cpu_att.csv
```

---

## `scripts/analyze.py`

**Description**  
Reads a dataset CSV and computes (per feature) **AUC**, **best-threshold accuracy**, and **Cohen's d**, printing a summary report.

**CI note**
- `analyze.py` does **not** compute confidence intervals (CIs).  
  Use `scripts/bootstrap_ci.py` for **95% bootstrap CIs**.

**Labels**
- Default labels are `BASELINE` and `ATTACK`.
- For custom labels use:
  - `--pos-label <LABEL_POS>`
  - `--neg-label <LABEL_NEG>`

**Examples**

Standard (Stage 1):
```bash
cd ~/projects/ordleak
python3 scripts/analyze.py out/csv/stage1/intel_i9_7900x/runset1/run1_dataset.csv
```

Negative control (`NEGCTRL_OFFCORE` vs `BASELINE`):
```bash
cd ~/projects/ordleak
python3 scripts/analyze.py out/csv/stage1/intel_i9_7900x/runset1/run6_negctrl_vs_base.csv --pos-label NEGCTRL_OFFCORE --neg-label BASELINE
```

Stage 2 secret:
```bash
cd ~/projects/ordleak
python3 scripts/analyze.py out/csv/stage2/threadripper/secret_tr_base.csv --pos-label MEM_BASE --neg-label CPU_BASE
python3 scripts/analyze.py out/csv/stage2/threadripper/secret_tr_att.csv  --pos-label MEM_ATT  --neg-label CPU_ATT

python3 scripts/analyze.py out/csv/stage2/i9_7900x/secret_intel_stage2_base.csv --pos-label MEM_BASE --neg-label CPU_BASE
python3 scripts/analyze.py out/csv/stage2/i9_7900x/secret_intel_stage2_att.csv  --pos-label MEM_ATT  --neg-label CPU_ATT
```

---

## `scripts/bootstrap_ci.py`

**Description**  
Bootstraps **95% confidence intervals (CI)** for **AUC** and **Balanced Accuracy** from a dataset CSV.

**Concrete behavior**
- Bootstrap resampling over samples (default **B=5000**).
- Prints:
  - `AUC mean=... 95% CI [lo, hi]`
  - `BalancedAcc mean=... 95% CI [lo, hi]`

**Labels**
- Default: `BASELINE` vs `ATTACK`
- For custom labels:
  - `--pos-label <LABEL_POS>`
  - `--neg-label <LABEL_NEG>`

**Examples**

Standard (Stage 1):
```bash
cd ~/projects/ordleak
python3 scripts/bootstrap_ci.py out/csv/stage1/intel_i9_7900x/runset1/run1_dataset.csv
```

Negative control:
```bash
cd ~/projects/ordleak
python3 scripts/bootstrap_ci.py out/csv/stage1/intel_i9_7900x/runset1/run6_negctrl_vs_base.csv --pos-label NEGCTRL_OFFCORE --neg-label BASELINE
```

Stage 2 secret:
```bash
cd ~/projects/ordleak
python3 scripts/bootstrap_ci.py out/csv/stage2/threadripper/secret_tr_base.csv --pos-label MEM_BASE --neg-label CPU_BASE
python3 scripts/bootstrap_ci.py out/csv/stage2/threadripper/secret_tr_att.csv  --pos-label MEM_ATT  --neg-label CPU_ATT

python3 scripts/bootstrap_ci.py out/csv/stage2/i9_7900x/secret_intel_stage2_base.csv --pos-label MEM_BASE --neg-label CPU_BASE
python3 scripts/bootstrap_ci.py out/csv/stage2/i9_7900x/secret_intel_stage2_att.csv  --pos-label MEM_ATT  --neg-label CPU_ATT
```
