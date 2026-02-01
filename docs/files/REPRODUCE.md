# REPRODUCE.md — ordleak

This file documents **how to reproduce** the datasets currently stored under:

- `out/csv/stage1/threadripper/first run_ripper/`
- `out/csv/stage2/`

It is written so that a future **artifact bundle** can treat the artifact folder as the **root directory**.
(So paths below are relative to the repository root / artifact root.)

---

## 1) Dataset files (as stored)

### Stage 1 — attacker presence leakage (BASELINE vs ATTACK)

- `out/csv/stage1/threadripper/first run_ripper/run1_dataset.csv`
- `out/csv/stage1/threadripper/first run_ripper/run2_dataset.csv`
- `out/csv/stage1/threadripper/first run_ripper/run3_dataset.csv`
- `out/csv/stage1/threadripper/first run_ripper/run4_dataset.csv`
- `out/csv/stage1/threadripper/first run_ripper/run5_dataset.csv`
- `out/csv/stage1/threadripper/first run_ripper/run6_negctrl_vs_base.csv`

### Stage 2 — secret leakage (CPU vs MEM)

- `out/csv/stage2/threadripper/secret_tr_base.csv`
- `out/csv/stage2/threadripper/secret_tr_att.csv`
- `out/csv/stage2/threadripper/negctrl_stage2.csv`

---

## 2) Machine + conventions used

These commands were executed on a Linux system with CPU pinning via `taskset`.
The victim server listens on a Unix socket. We maintain a stable socket path by symlinking:

- Victim instance uses `--sock out/victim_cpu.sock` or `--sock out/victim_mem.sock`
- We point `out/victim.sock` to the chosen one via `ln -sf ... out/victim.sock`

**Cores:**
- Victim + dataset runner pinned to `0,1` via `taskset -c 0,1`
- Off-core negative control attacker pinned away from victim cores (example: `2-31` on Threadripper)

---

## 3) Stage 1 reproduction (presence leakage)

### Terminal 1 — start victim (CPU mode)
```bash
cd ~/projects/ordleak
rm -f out/victim.sock
taskset -c 0,1 python3 -u src/victim.py --sock out/victim_cpu.sock --mode cpu --workers 2 --iters 200000
```

### Terminal 2 — point stable socket symlink
```bash
cd ~/projects/ordleak
ln -sf victim_cpu.sock out/victim.sock
```

### Terminal 2 — create one Stage 1 dataset (BASELINE then ATTACK into same CSV)

**Example: `run1_dataset.csv`**
```bash
cd ~/projects/ordleak
mkdir -p "out/csv/stage1/threadripper/first run_ripper"

taskset -c 0,1 python3 scripts/run_dataset.py   --runs 100 --n 20   --label BASELINE   --out "out/csv/stage1/threadripper/first run_ripper/run1_dataset.csv"

taskset -c 0,1 python3 scripts/run_dataset.py   --runs 100 --n 20   --attack --attack-procs 32 --attack-seconds 5   --label ATTACK   --out "out/csv/stage1/threadripper/first run_ripper/run1_dataset.csv"
```

Repeat the same pattern for:
- `run2_dataset.csv`
- `run3_dataset.csv`
- `run4_dataset.csv`
- `run5_dataset.csv`

(Optionally vary parameters per run if you are sweeping configs; the above shows the canonical form.)

---

## 4) Stage 1 negative control (off-core attacker)

Goal: show that an attacker running **off-core** (not sharing victim cores) does *not* create a strong signal.

### Terminal 1 — victim (same as Stage 1)
```bash
cd ~/projects/ordleak
rm -f out/victim.sock
taskset -c 0,1 python3 -u src/victim.py --sock out/victim_cpu.sock --mode cpu --workers 2 --iters 200000
```

### Terminal 2 — symlink
```bash
cd ~/projects/ordleak
ln -sf victim_cpu.sock out/victim.sock
```

### Terminal 3 — start off-core attacker (separate)
```bash
cd ~/projects/ordleak
taskset -c 2-31 python3 -u src/attacker.py --procs 32 --seconds 999999
```

### Terminal 2 — collect NEGCTRL_OFFCORE and BASELINE into one CSV

**Important:** `scripts/analyze.py` expects two classes, so we store both labels in the same CSV.
```bash
cd ~/projects/ordleak
mkdir -p "out/csv/stage1/threadripper/first run_ripper"

# With off-core attacker running:
taskset -c 0,1 python3 scripts/run_dataset.py   --runs 100 --n 20   --label NEGCTRL_OFFCORE   --out "out/csv/stage1/threadripper/first run_ripper/run6_negctrl_vs_base.csv"

# Now stop Terminal 3 (attacker), then collect baseline:
taskset -c 0,1 python3 scripts/run_dataset.py   --runs 100 --n 20   --label BASELINE   --out "out/csv/stage1/threadripper/first run_ripper/run6_negctrl_vs_base.csv"
```

---

## 5) Stage 2 reproduction (secret leakage: CPU vs MEM)

Stage 2 uses two victim modes:
- CPU mode: `--mode cpu`
- MEM mode: `--mode mem --mem-kb 8192` (example "strong" configuration)

### 5.1 Baseline secret leakage: `CPU_BASE` vs `MEM_BASE` → `secret_tr_base.csv`

#### Terminal 1 — start victim (CPU mode)
```bash
cd ~/projects/ordleak
rm -f out/victim.sock
taskset -c 0,1 python3 -u src/victim.py --sock out/victim_cpu.sock --mode cpu --workers 2 --iters 200000
```

#### Terminal 2 — symlink + collect CPU_BASE
```bash
cd ~/projects/ordleak
mkdir -p out/csv/stage2
ln -sf victim_cpu.sock out/victim.sock

taskset -c 0,1 python3 scripts/run_dataset.py   --runs 100 --n 20   --label CPU_BASE   --out out/csv/stage2/threadripper/secret_tr_base.csv
```

#### Terminal 1 — restart victim (MEM mode)
Stop victim, then:
```bash
cd ~/projects/ordleak
rm -f out/victim.sock
taskset -c 0,1 python3 -u src/victim.py --sock out/victim_mem.sock --mode mem --mem-kb 8192 --workers 2 --iters 200000
```

#### Terminal 2 — symlink + collect MEM_BASE (append to same CSV)
```bash
cd ~/projects/ordleak
ln -sf victim_mem.sock out/victim.sock

taskset -c 0,1 python3 scripts/run_dataset.py   --runs 100 --n 20   --label MEM_BASE   --out out/csv/stage2/threadripper/secret_tr_base.csv
```

---

### 5.2 Attack-amplified secret leakage: `CPU_ATT` vs `MEM_ATT` → `secret_tr_att.csv`

#### Terminal 1 — start victim (CPU mode)
```bash
cd ~/projects/ordleak
rm -f out/victim.sock
taskset -c 0,1 python3 -u src/victim.py --sock out/victim_cpu.sock --mode cpu --workers 2 --iters 200000
```

#### Terminal 2 — symlink + collect CPU_ATT (attack enabled)
```bash
cd ~/projects/ordleak
mkdir -p out/csv/stage2
ln -sf victim_cpu.sock out/victim.sock

taskset -c 0,1 python3 scripts/run_dataset.py   --runs 100 --n 20   --attack --attack-procs 32 --attack-seconds 5   --label CPU_ATT   --out out/csv/stage2/threadripper/secret_tr_att.csv
```

#### Terminal 1 — restart victim (MEM mode)
Stop victim, then:
```bash
cd ~/projects/ordleak
rm -f out/victim.sock
taskset -c 0,1 python3 -u src/victim.py --sock out/victim_mem.sock --mode mem --mem-kb 8192 --workers 2 --iters 200000
```

#### Terminal 2 — symlink + collect MEM_ATT (append to same CSV)
```bash
cd ~/projects/ordleak
ln -sf victim_mem.sock out/victim.sock

taskset -c 0,1 python3 scripts/run_dataset.py   --runs 100 --n 20   --attack --attack-procs 32 --attack-seconds 5   --label MEM_ATT   --out out/csv/stage2/threadripper/secret_tr_att.csv
```

---

### 5.3 Negative control (Stage 2): `negctrl_stage2.csv`

**Goal:** show that **off-core contention** (attacker not sharing victim cores) does **not** significantly amplify CPU vs MEM distinguishability.

We create a single CSV containing **two labels**:
- `CPU_NEGCTRL_OFFCORE`
- `MEM_NEGCTRL_OFFCORE`

#### Terminal 3 — start off-core attacker (separate)
Pin the attacker away from victim cores (example Threadripper: cores `2-31`):
```bash
cd ~/projects/ordleak
taskset -c 2-31 python3 -u src/attacker.py --procs 32 --seconds 999999
```

#### Terminal 1 — start victim (CPU mode)
```bash
cd ~/projects/ordleak
rm -f out/victim.sock
taskset -c 0,1 python3 -u src/victim.py --sock out/victim_cpu.sock --mode cpu --workers 2 --iters 200000
```

#### Terminal 2 — symlink + collect `CPU_NEGCTRL_OFFCORE`
```bash
cd ~/projects/ordleak
mkdir -p out/csv/stage2
ln -sf victim_cpu.sock out/victim.sock

taskset -c 0,1 python3 scripts/run_dataset.py   --runs 100 --n 20   --label CPU_NEGCTRL_OFFCORE   --out out/csv/stage2/threadripper/negctrl_stage2.csv
```

#### Terminal 1 — restart victim (MEM mode)
Stop victim, then:
```bash
cd ~/projects/ordleak
rm -f out/victim.sock
taskset -c 0,1 python3 -u src/victim.py --sock out/victim_mem.sock --mode mem --mem-kb 8192 --workers 2 --iters 200000
```

#### Terminal 2 — symlink + collect `MEM_NEGCTRL_OFFCORE` (append)
```bash
cd ~/projects/ordleak
ln -sf victim_mem.sock out/victim.sock

taskset -c 0,1 python3 scripts/run_dataset.py   --runs 100 --n 20   --label MEM_NEGCTRL_OFFCORE   --out out/csv/stage2/threadripper/negctrl_stage2.csv
```

#### (Optional) Analyze + bootstrap CI for Stage 2 negctrl
```bash
cd ~/projects/ordleak
python3 scripts/analyze.py out/csv/stage2/threadripper/negctrl_stage2.csv --pos-label MEM_NEGCTRL_OFFCORE --neg-label CPU_NEGCTRL_OFFCORE
python3 scripts/bootstrap_ci.py out/csv/stage2/threadripper/negctrl_stage2.csv --pos-label MEM_NEGCTRL_OFFCORE --neg-label CPU_NEGCTRL_OFFCORE
```

## 6) (Optional) Analysis + Bootstrap CI

Stage 1:
```bash
cd ~/projects/ordleak
python3 scripts/analyze.py "out/csv/stage1/threadripper/first run_ripper/run1_dataset.csv"
python3 scripts/bootstrap_ci.py "out/csv/stage1/threadripper/first run_ripper/run1_dataset.csv"
```

NegCtrl:
```bash
cd ~/projects/ordleak
python3 scripts/analyze.py "out/csv/stage1/threadripper/first run_ripper/run6_negctrl_vs_base.csv"   --pos-label NEGCTRL_OFFCORE --neg-label BASELINE
python3 scripts/bootstrap_ci.py "out/csv/stage1/threadripper/first run_ripper/run6_negctrl_vs_base.csv"   --pos-label NEGCTRL_OFFCORE --neg-label BASELINE
```

Stage 2:
```bash
cd ~/projects/ordleak
python3 scripts/analyze.py out/csv/stage2/threadripper/secret_tr_base.csv --pos-label MEM_BASE --neg-label CPU_BASE
python3 scripts/bootstrap_ci.py out/csv/stage2/threadripper/secret_tr_base.csv --pos-label MEM_BASE --neg-label CPU_BASE

python3 scripts/analyze.py out/csv/stage2/threadripper/secret_tr_att.csv  --pos-label MEM_ATT  --neg-label CPU_ATT
python3 scripts/bootstrap_ci.py out/csv/stage2/threadripper/secret_tr_att.csv  --pos-label MEM_ATT  --neg-label CPU_ATT
```

---

# ordleak — REPRODUCE (Intel i9-7900X)

This file mirrors the **Stage 1** reproduction structure from the Threadripper docs, but for the **Intel i9-7900X** runset.

---

## 1) Datasets covered by this file (Stage 1)

Stage 1 — attacker presence leakage (BASELINE vs ATTACK)

- `out/csv/stage1/intel_i9_7900x/runset1/run1_dataset.csv`
- `out/csv/stage1/intel_i9_7900x/runset1/run2_dataset.csv`
- `out/csv/stage1/intel_i9_7900x/runset1/run3_dataset.csv`
- `out/csv/stage1/intel_i9_7900x/runset1/run4_dataset.csv`
- `out/csv/stage1/intel_i9_7900x/runset1/run5_dataset.csv`
- `out/csv/stage1/intel_i9_7900x/runset1/run6_negctrl_vs_base.csv` (negative control)

---

## 2) Machine + conventions used

- CPU: Intel(R) Core(TM) i9-7900X (10C/20T)
- Victim + dataset runner pinned to `0,1` via `taskset -c 0,1`
  - HT siblings: `0<->10`, `1<->11` (so `0,1` are distinct physical cores)
- Victim server listens on Unix socket:
  - Victim uses `--sock out/victim_cpu.sock`
  - Dataset always connects to `out/victim.sock` (symlink)

---

## 3) Stage 1 reproduction (presence leakage)

### Terminal 1 — start victim (CPU mode)
```bash
cd ~/projects/ordleak
rm -f out/victim.sock out/victim_cpu.sock
taskset -c 0,1 python3 -u src/victim.py --sock out/victim_cpu.sock --mode cpu --workers 2 --iters 200000
```

### Terminal 2 — point stable socket symlink
```bash
cd ~/projects/ordleak
ln -sf victim_cpu.sock out/victim.sock
```

### Terminal 2 — generate Stage 1 datasets (BASELINE then ATTACK into same CSV)

```bash
cd ~/projects/ordleak
mkdir -p out/csv/stage1/intel_i9_7900x/runset1
```

**Run 1 (`run1_dataset.csv`)**
```bash
cd ~/projects/ordleak
taskset -c 0,1 python3 scripts/run_dataset.py --runs 100 --n 20 --label BASELINE --out out/csv/stage1/intel_i9_7900x/runset1/run1_dataset.csv
taskset -c 0,1 python3 scripts/run_dataset.py --runs 100 --n 20 --attack --attack-procs 16 --attack-seconds 5 --label ATTACK --out out/csv/stage1/intel_i9_7900x/runset1/run1_dataset.csv
```

**Run 2 (`run2_dataset.csv`)**
```bash
cd ~/projects/ordleak
taskset -c 0,1 python3 scripts/run_dataset.py --runs 100 --n 20 --label BASELINE --out out/csv/stage1/intel_i9_7900x/runset1/run2_dataset.csv
taskset -c 0,1 python3 scripts/run_dataset.py --runs 100 --n 20 --attack --attack-procs 16 --attack-seconds 5 --label ATTACK --out out/csv/stage1/intel_i9_7900x/runset1/run2_dataset.csv
```

**Run 3 (`run3_dataset.csv`)**
```bash
cd ~/projects/ordleak
taskset -c 0,1 python3 scripts/run_dataset.py --runs 100 --n 20 --label BASELINE --out out/csv/stage1/intel_i9_7900x/runset1/run3_dataset.csv
taskset -c 0,1 python3 scripts/run_dataset.py --runs 100 --n 20 --attack --attack-procs 16 --attack-seconds 5 --label ATTACK --out out/csv/stage1/intel_i9_7900x/runset1/run3_dataset.csv
```

**Run 4 (`run4_dataset.csv`)**
```bash
cd ~/projects/ordleak
taskset -c 0,1 python3 scripts/run_dataset.py --runs 100 --n 20 --label BASELINE --out out/csv/stage1/intel_i9_7900x/runset1/run4_dataset.csv
taskset -c 0,1 python3 scripts/run_dataset.py --runs 100 --n 20 --attack --attack-procs 16 --attack-seconds 5 --label ATTACK --out out/csv/stage1/intel_i9_7900x/runset1/run4_dataset.csv
```

**Run 5 (`run5_dataset.csv`)**
```bash
cd ~/projects/ordleak
taskset -c 0,1 python3 scripts/run_dataset.py --runs 100 --n 20 --label BASELINE --out out/csv/stage1/intel_i9_7900x/runset1/run5_dataset.csv
taskset -c 0,1 python3 scripts/run_dataset.py --runs 100 --n 20 --attack --attack-procs 16 --attack-seconds 5 --label ATTACK --out out/csv/stage1/intel_i9_7900x/runset1/run5_dataset.csv
```

---

## 4) Stage 1 negative control (off-core attacker)

Goal: show that an attacker running **off-core** (not sharing victim cores) does *not* create a strong signal.

### Terminal 1 — victim (same as Stage 1)
```bash
cd ~/projects/ordleak
rm -f out/victim.sock out/victim_cpu.sock
taskset -c 0,1 python3 -u src/victim.py --sock out/victim_cpu.sock --mode cpu --workers 2 --iters 200000
```

### Terminal 2 — symlink
```bash
cd ~/projects/ordleak
ln -sf victim_cpu.sock out/victim.sock
```

### Terminal 3 — start off-core attacker (separate)
```bash
cd ~/projects/ordleak
taskset -c 2-19 python3 -u src/attacker.py --procs 18 --seconds 999999
```

### Terminal 2 — collect NEGCTRL_OFFCORE and BASELINE into one CSV

**Important:** `scripts/analyze.py` expects two classes, so we store both labels in the same CSV.
```bash
cd ~/projects/ordleak
mkdir -p out/csv/stage1/intel_i9_7900x/runset1

# With off-core attacker running:
taskset -c 0,1 python3 scripts/run_dataset.py --runs 100 --n 20 --label NEGCTRL_OFFCORE --out out/csv/stage1/intel_i9_7900x/runset1/run6_negctrl_vs_base.csv

# Now stop Terminal 3 (attacker), then collect baseline:
taskset -c 0,1 python3 scripts/run_dataset.py --runs 100 --n 20 --label BASELINE --out out/csv/stage1/intel_i9_7900x/runset1/run6_negctrl_vs_base.csv
```

---

## 5) Analysis commands (Stage 1)

Example for `run1_dataset.csv`:
```bash
cd ~/projects/ordleak
python3 scripts/analyze.py out/csv/stage1/intel_i9_7900x/runset1/run1_dataset.csv
python3 scripts/bootstrap_ci.py out/csv/stage1/intel_i9_7900x/runset1/run1_dataset.csv
```

Negative control:
```bash
cd ~/projects/ordleak
python3 scripts/analyze.py out/csv/stage1/intel_i9_7900x/runset1/run6_negctrl_vs_base.csv --pos-label NEGCTRL_OFFCORE --neg-label BASELINE
python3 scripts/bootstrap_ci.py out/csv/stage1/intel_i9_7900x/runset1/run6_negctrl_vs_base.csv --pos-label NEGCTRL_OFFCORE --neg-label BASELINE
```

---

## 6) Stage 2 reproduction (secret-mode leakage on Intel i9-7900X)

This follows the same protocol as the Threadripper Stage 2, but with the Intel output paths:

- `out/csv/stage2/i9_7900x/secret_intel_stage2_base.csv`
- `out/csv/stage2/i9_7900x/secret_intel_stage2_att.csv`
- `out/csv/stage2/i9_7900x/negctrl_intel_stage2.csv`

### 6.1 Base (CPU_BASE vs MEM_BASE in the same CSV)

**Terminal 1 — CPU victim**
```bash
cd ~/projects/ordleak
rm -f out/victim.sock out/victim_cpu.sock
taskset -c 0,1 python3 -u src/victim.py --sock out/victim_cpu.sock --mode cpu --workers 2 --iters 200000
```

**Terminal 2 — symlink + CPU_BASE dataset**
```bash
cd ~/projects/ordleak
ln -sf victim_cpu.sock out/victim.sock
mkdir -p out/csv/stage2/i9_7900x
taskset -c 0,1 python3 scripts/run_dataset.py --runs 100 --n 20 --label CPU_BASE --out out/csv/stage2/i9_7900x/secret_intel_stage2_base.csv
```

Stop victim (Ctrl+C).

**Terminal 1 — MEM victim**
```bash
cd ~/projects/ordleak
rm -f out/victim.sock out/victim_mem.sock
taskset -c 0,1 python3 -u src/victim.py --sock out/victim_mem.sock --mode mem --mem-kb 8192 --workers 2 --iters 200000
```

**Terminal 2 — symlink + MEM_BASE dataset (append to same CSV)**
```bash
cd ~/projects/ordleak
ln -sf victim_mem.sock out/victim.sock
taskset -c 0,1 python3 scripts/run_dataset.py --runs 100 --n 20 --label MEM_BASE --out out/csv/stage2/i9_7900x/secret_intel_stage2_base.csv
```

### 6.2 Attack (CPU_ATT vs MEM_ATT in the same CSV)

**CPU victim + CPU_ATT dataset**
```bash
cd ~/projects/ordleak
rm -f out/victim.sock out/victim_cpu.sock
taskset -c 0,1 python3 -u src/victim.py --sock out/victim_cpu.sock --mode cpu --workers 2 --iters 200000
```

```bash
cd ~/projects/ordleak
ln -sf victim_cpu.sock out/victim.sock
taskset -c 0,1 python3 scripts/run_dataset.py --runs 100 --n 20 --attack --attack-procs 32 --attack-seconds 5 --label CPU_ATT --out out/csv/stage2/i9_7900x/secret_intel_stage2_att.csv
```

Stop victim (Ctrl+C).

**MEM victim + MEM_ATT dataset**
```bash
cd ~/projects/ordleak
rm -f out/victim.sock out/victim_mem.sock
taskset -c 0,1 python3 -u src/victim.py --sock out/victim_mem.sock --mode mem --mem-kb 8192 --workers 2 --iters 200000
```

```bash
cd ~/projects/ordleak
ln -sf victim_mem.sock out/victim.sock
taskset -c 0,1 python3 scripts/run_dataset.py --runs 100 --n 20 --attack --attack-procs 32 --attack-seconds 5 --label MEM_ATT --out out/csv/stage2/i9_7900x/secret_intel_stage2_att.csv
```

### 6.3 Stage 2 negative control (off-core attacker)

On the i9-7900X, CPUs `0` and `1` are *different physical cores* (core 0 and core 1). The sibling hyperthreads are `10` and `11`.
So pinning victim+dataset to `0,1` is a reasonable "two-core" setup, and the off-core set is `2-19`.

**Terminal 3 — off-core attacker**
```bash
cd ~/projects/ordleak
taskset -c 2-19 python3 -u src/attacker.py --procs 20 --seconds 999999
```

**Terminal 1 — CPU victim**
```bash
cd ~/projects/ordleak
rm -f out/victim.sock out/victim_cpu.sock
taskset -c 0,1 python3 -u src/victim.py --sock out/victim_cpu.sock --mode cpu --workers 2 --iters 200000
```

**Terminal 2 — symlink + CPU_NEGCTRL_OFFCORE**
```bash
cd ~/projects/ordleak
ln -sf victim_cpu.sock out/victim.sock
taskset -c 0,1 python3 scripts/run_dataset.py --runs 100 --n 20 --label CPU_NEGCTRL_OFFCORE --out out/csv/stage2/i9_7900x/negctrl_intel_stage2.csv
```

Stop CPU victim (Ctrl+C).

**Terminal 1 — MEM victim**
```bash
cd ~/projects/ordleak
rm -f out/victim.sock out/victim_mem.sock
taskset -c 0,1 python3 -u src/victim.py --sock out/victim_mem.sock --mode mem --mem-kb 8192 --workers 2 --iters 200000
```

**Terminal 2 — symlink + MEM_NEGCTRL_OFFCORE**
```bash
cd ~/projects/ordleak
ln -sf victim_mem.sock out/victim.sock
taskset -c 0,1 python3 scripts/run_dataset.py --runs 100 --n 20 --label MEM_NEGCTRL_OFFCORE --out out/csv/stage2/i9_7900x/negctrl_intel_stage2.csv
```

### 6.4 Analysis commands (Stage 2, Intel)

```bash
cd ~/projects/ordleak
python3 scripts/analyze.py out/csv/stage2/i9_7900x/secret_intel_stage2_base.csv --pos-label MEM_BASE --neg-label CPU_BASE
python3 scripts/bootstrap_ci.py out/csv/stage2/i9_7900x/secret_intel_stage2_base.csv --pos-label MEM_BASE --neg-label CPU_BASE

python3 scripts/analyze.py out/csv/stage2/i9_7900x/secret_intel_stage2_att.csv --pos-label MEM_ATT --neg-label CPU_ATT
python3 scripts/bootstrap_ci.py out/csv/stage2/i9_7900x/secret_intel_stage2_att.csv --pos-label MEM_ATT --neg-label CPU_ATT

python3 scripts/analyze.py out/csv/stage2/i9_7900x/negctrl_intel_stage2.csv --pos-label MEM_NEGCTRL_OFFCORE --neg-label CPU_NEGCTRL_OFFCORE
python3 scripts/bootstrap_ci.py out/csv/stage2/i9_7900x/negctrl_intel_stage2.csv --pos-label MEM_NEGCTRL_OFFCORE --neg-label CPU_NEGCTRL_OFFCORE
```

---

# 7) Defense evaluation — BOS Scrubber (Threadripper)

This section documents how to measure the **leakage–overhead tradeoff** of Budgeted Order Scrubbing (BOS v1).

## 7.1 Overview

**Goal:** Show that increasing the scrubber window `W` reduces AUC (leakage) at the cost of increased latency/overhead.

**Key measurements:**
- **AUC vs W** (Stage 2 ATT scenario: `CPU_ATT` vs `MEM_ATT`)
- **Overhead vs W** (runtime or throughput)

**Window sizes to sweep:** `W ∈ {1, 2, 4, 8, 16}` (optionally 32)

**Output directory:**
```
out/csv/defense/threadripper/
```

---

## 7.2 Scrubber sweep — Stage 2 ATT (`CPU_ATT` vs `MEM_ATT`)

For each value of `W`, we:
1. Start victim with `--scrub-window W`
2. Collect `CPU_ATT` samples (with attacker)
3. Restart victim with same `W` but `--mode mem`
4. Collect `MEM_ATT` samples (with attacker)
5. Analyze the resulting CSV

### Setup (common)
```bash
cd ~/projects/ordleak
mkdir -p out/csv/defense/threadripper
```

### W=1 (passthrough, no reordering)

**Terminal 1 — CPU victim with scrubber W=1**
```bash
cd ~/projects/ordleak
rm -f out/victim.sock out/victim_cpu.sock
taskset -c 0,1 python3 -u src/victim.py \
    --sock out/victim_cpu.sock --mode cpu --workers 2 --iters 200000 \
    --scrub-window 1 --scrub-seed 42
```

**Terminal 2 — symlink + collect CPU_ATT**
```bash
cd ~/projects/ordleak
ln -sf victim_cpu.sock out/victim.sock
taskset -c 0,1 python3 scripts/run_dataset.py \
    --runs 50 --n 20 \
    --attack --attack-procs 32 --attack-seconds 5 \
    --label CPU_ATT \
    --scrub-window 1 \
    --out out/csv/defense/threadripper/scrub_w1_att.csv
```

**Terminal 1 — MEM victim with scrubber W=1**
```bash
cd ~/projects/ordleak
rm -f out/victim.sock out/victim_mem.sock
taskset -c 0,1 python3 -u src/victim.py \
    --sock out/victim_mem.sock --mode mem --mem-kb 8192 --workers 2 --iters 200000 \
    --scrub-window 1 --scrub-seed 42
```

**Terminal 2 — symlink + collect MEM_ATT (append)**
```bash
cd ~/projects/ordleak
ln -sf victim_mem.sock out/victim.sock
taskset -c 0,1 python3 scripts/run_dataset.py \
    --runs 50 --n 20 \
    --attack --attack-procs 32 --attack-seconds 5 \
    --label MEM_ATT \
    --scrub-window 1 \
    --out out/csv/defense/threadripper/scrub_w1_att.csv
```

### W=2

**Terminal 1 — CPU victim with scrubber W=2**
```bash
cd ~/projects/ordleak
rm -f out/victim.sock out/victim_cpu.sock
taskset -c 0,1 python3 -u src/victim.py \
    --sock out/victim_cpu.sock --mode cpu --workers 2 --iters 200000 \
    --scrub-window 2 --scrub-seed 42
```

**Terminal 2 — symlink + collect CPU_ATT**
```bash
cd ~/projects/ordleak
ln -sf victim_cpu.sock out/victim.sock
taskset -c 0,1 python3 scripts/run_dataset.py \
    --runs 50 --n 20 \
    --attack --attack-procs 32 --attack-seconds 5 \
    --label CPU_ATT \
    --scrub-window 2 \
    --out out/csv/defense/threadripper/scrub_w2_att.csv
```

**Terminal 1 — MEM victim with scrubber W=2**
```bash
cd ~/projects/ordleak
rm -f out/victim.sock out/victim_mem.sock
taskset -c 0,1 python3 -u src/victim.py \
    --sock out/victim_mem.sock --mode mem --mem-kb 8192 --workers 2 --iters 200000 \
    --scrub-window 2 --scrub-seed 42
```

**Terminal 2 — symlink + collect MEM_ATT (append)**
```bash
cd ~/projects/ordleak
ln -sf victim_mem.sock out/victim.sock
taskset -c 0,1 python3 scripts/run_dataset.py \
    --runs 50 --n 20 \
    --attack --attack-procs 32 --attack-seconds 5 \
    --label MEM_ATT \
    --scrub-window 2 \
    --out out/csv/defense/threadripper/scrub_w2_att.csv
```

### W=4

**Terminal 1 — CPU victim with scrubber W=4**
```bash
cd ~/projects/ordleak
rm -f out/victim.sock out/victim_cpu.sock
taskset -c 0,1 python3 -u src/victim.py \
    --sock out/victim_cpu.sock --mode cpu --workers 2 --iters 200000 \
    --scrub-window 4 --scrub-seed 42
```

**Terminal 2 — symlink + collect CPU_ATT**
```bash
cd ~/projects/ordleak
ln -sf victim_cpu.sock out/victim.sock
taskset -c 0,1 python3 scripts/run_dataset.py \
    --runs 50 --n 20 \
    --attack --attack-procs 32 --attack-seconds 5 \
    --label CPU_ATT \
    --scrub-window 4 \
    --out out/csv/defense/threadripper/scrub_w4_att.csv
```

**Terminal 1 — MEM victim with scrubber W=4**
```bash
cd ~/projects/ordleak
rm -f out/victim.sock out/victim_mem.sock
taskset -c 0,1 python3 -u src/victim.py \
    --sock out/victim_mem.sock --mode mem --mem-kb 8192 --workers 2 --iters 200000 \
    --scrub-window 4 --scrub-seed 42
```

**Terminal 2 — symlink + collect MEM_ATT (append)**
```bash
cd ~/projects/ordleak
ln -sf victim_mem.sock out/victim.sock
taskset -c 0,1 python3 scripts/run_dataset.py \
    --runs 50 --n 20 \
    --attack --attack-procs 32 --attack-seconds 5 \
    --label MEM_ATT \
    --scrub-window 4 \
    --out out/csv/defense/threadripper/scrub_w4_att.csv
```

### W=8

**Terminal 1 — CPU victim with scrubber W=8**
```bash
cd ~/projects/ordleak
rm -f out/victim.sock out/victim_cpu.sock
taskset -c 0,1 python3 -u src/victim.py \
    --sock out/victim_cpu.sock --mode cpu --workers 2 --iters 200000 \
    --scrub-window 8 --scrub-seed 42
```

**Terminal 2 — symlink + collect CPU_ATT**
```bash
cd ~/projects/ordleak
ln -sf victim_cpu.sock out/victim.sock
taskset -c 0,1 python3 scripts/run_dataset.py \
    --runs 50 --n 20 \
    --attack --attack-procs 32 --attack-seconds 5 \
    --label CPU_ATT \
    --scrub-window 8 \
    --out out/csv/defense/threadripper/scrub_w8_att.csv
```

**Terminal 1 — MEM victim with scrubber W=8**
```bash
cd ~/projects/ordleak
rm -f out/victim.sock out/victim_mem.sock
taskset -c 0,1 python3 -u src/victim.py \
    --sock out/victim_mem.sock --mode mem --mem-kb 8192 --workers 2 --iters 200000 \
    --scrub-window 8 --scrub-seed 42
```

**Terminal 2 — symlink + collect MEM_ATT (append)**
```bash
cd ~/projects/ordleak
ln -sf victim_mem.sock out/victim.sock
taskset -c 0,1 python3 scripts/run_dataset.py \
    --runs 50 --n 20 \
    --attack --attack-procs 32 --attack-seconds 5 \
    --label MEM_ATT \
    --scrub-window 8 \
    --out out/csv/defense/threadripper/scrub_w8_att.csv
```

### W=16

**Terminal 1 — CPU victim with scrubber W=16**
```bash
cd ~/projects/ordleak
rm -f out/victim.sock out/victim_cpu.sock
taskset -c 0,1 python3 -u src/victim.py \
    --sock out/victim_cpu.sock --mode cpu --workers 2 --iters 200000 \
    --scrub-window 16 --scrub-seed 42
```

**Terminal 2 — symlink + collect CPU_ATT**
```bash
cd ~/projects/ordleak
ln -sf victim_cpu.sock out/victim.sock
taskset -c 0,1 python3 scripts/run_dataset.py \
    --runs 50 --n 20 \
    --attack --attack-procs 32 --attack-seconds 5 \
    --label CPU_ATT \
    --scrub-window 16 \
    --out out/csv/defense/threadripper/scrub_w16_att.csv
```

**Terminal 1 — MEM victim with scrubber W=16**
```bash
cd ~/projects/ordleak
rm -f out/victim.sock out/victim_mem.sock
taskset -c 0,1 python3 -u src/victim.py \
    --sock out/victim_mem.sock --mode mem --mem-kb 8192 --workers 2 --iters 200000 \
    --scrub-window 16 --scrub-seed 42
```

**Terminal 2 — symlink + collect MEM_ATT (append)**
```bash
cd ~/projects/ordleak
ln -sf victim_mem.sock out/victim.sock
taskset -c 0,1 python3 scripts/run_dataset.py \
    --runs 50 --n 20 \
    --attack --attack-procs 32 --attack-seconds 5 \
    --label MEM_ATT \
    --scrub-window 16 \
    --out out/csv/defense/threadripper/scrub_w16_att.csv
```

---

## 7.3 Analysis (scrubber sweep)

```bash
cd ~/projects/ordleak

# W=1
python3 scripts/analyze.py out/csv/defense/threadripper/scrub_w1_att.csv --pos-label MEM_ATT --neg-label CPU_ATT
python3 scripts/bootstrap_ci.py out/csv/defense/threadripper/scrub_w1_att.csv --pos-label MEM_ATT --neg-label CPU_ATT

# W=2
python3 scripts/analyze.py out/csv/defense/threadripper/scrub_w2_att.csv --pos-label MEM_ATT --neg-label CPU_ATT
python3 scripts/bootstrap_ci.py out/csv/defense/threadripper/scrub_w2_att.csv --pos-label MEM_ATT --neg-label CPU_ATT

# W=4
python3 scripts/analyze.py out/csv/defense/threadripper/scrub_w4_att.csv --pos-label MEM_ATT --neg-label CPU_ATT
python3 scripts/bootstrap_ci.py out/csv/defense/threadripper/scrub_w4_att.csv --pos-label MEM_ATT --neg-label CPU_ATT

# W=8
python3 scripts/analyze.py out/csv/defense/threadripper/scrub_w8_att.csv --pos-label MEM_ATT --neg-label CPU_ATT
python3 scripts/bootstrap_ci.py out/csv/defense/threadripper/scrub_w8_att.csv --pos-label MEM_ATT --neg-label CPU_ATT

# W=16
python3 scripts/analyze.py out/csv/defense/threadripper/scrub_w16_att.csv --pos-label MEM_ATT --neg-label CPU_ATT
python3 scripts/bootstrap_ci.py out/csv/defense/threadripper/scrub_w16_att.csv --pos-label MEM_ATT --neg-label CPU_ATT
```

---

## 7.4 Overhead measurement

**Simple approach:** measure total runtime for a fixed number of runs.

```bash
cd ~/projects/ordleak

# Baseline (no scrubber, W=0)
time taskset -c 0,1 python3 scripts/run_dataset.py --runs 50 --n 20 --label OVERHEAD_TEST --out /dev/null

# With scrubber W=8
# (victim must be running with --scrub-window 8)
time taskset -c 0,1 python3 scripts/run_dataset.py --runs 50 --n 20 --label OVERHEAD_TEST --out /dev/null
```

Record wall-clock time for each W and compute relative overhead.

---

## 7.5 Expected output structure

```
out/csv/defense/threadripper/
├── scrub_w1_att.csv
├── scrub_w2_att.csv
├── scrub_w4_att.csv
├── scrub_w8_att.csv
└── scrub_w16_att.csv
```
