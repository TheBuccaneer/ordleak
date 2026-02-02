# ordleak — RESULTS (Threadripper)

This file documents the **current** results produced in this thread, together with the **exact command lines** used to generate and analyze each dataset.

## Testbed + environment notes

- Machine: **AMD Ryzen Threadripper 3970X (32 cores)**
- Pinning: Victim + dataset runner pinned to cores `0,1` via `taskset -c 0,1`
- GUI: **disabled** (headless / `multi-user.target`)
- Frequency governor: **not forced** ("performance mode" not required for these results)
- Threat model: observer sees **rank-only completion order** (`DONE <id>`), no fine-grained timers.

> Note: `scripts/run_dataset.py` **does not store all runtime parameters in the CSV** (it stores: `run_id,label,n,ods,gap_var,first_half_ods`).
> Therefore, the command lines below are the authoritative record for parameters like `--attack-procs`, `--attack-seconds`, `--iters`, `--mem-kb`, etc.

---

## Common commands (analysis)

For any dataset CSV:

```bash
cd ~/projects/ordleak

# Summary + AUC for ODS and GAP_VAR
python3 scripts/analyze.py <CSV>

# Bootstrap 95% CI (default B=5000) for AUC and Balanced Accuracy
# (bootstrap_ci uses ODS by default; see --metric-col if needed)
python3 scripts/bootstrap_ci.py <CSV>
```

For nonstandard labels (e.g., NEGCTRL), pass explicit labels:

```bash
python3 scripts/analyze.py <CSV> --pos-label <POS> --neg-label <NEG>
python3 scripts/bootstrap_ci.py <CSV> --pos-label <POS> --neg-label <NEG>
```

---

# Stage 1 — Attacker presence distinguishability (BASELINE vs ATTACK)

**Goal (Stage 1):** show that an unprivileged co-resident attacker changes completion-order statistics enough that an observer can distinguish `BASELINE` vs `ATTACK` from rank-only completion order.

## How Stage 1 datasets were generated (template)

### Terminal 1 — victim (CPU mode)
```bash
cd ~/projects/ordleak
rm -f out/victim.sock
taskset -c 0,1 python3 -u src/victim.py --sock out/victim_cpu.sock --mode cpu --workers 2 --iters 200000
```

### Terminal 2 — dataset collection

Create a symlink `out/victim.sock` that the client uses:
```bash
cd ~/projects/ordleak
ln -sf victim_cpu.sock out/victim.sock
```

Then collect baseline + attack into the same CSV:

```bash
# BASELINE
taskset -c 0,1 python3 scripts/run_dataset.py   --runs 100 --n 20   --label BASELINE   --out <OUT.csv>

# ATTACK (co-resident; attacker is spawned by run_dataset and inherits CPU affinity)
taskset -c 0,1 python3 scripts/run_dataset.py   --runs 100 --n 20   --attack --attack-procs 32 --attack-seconds 5   --label ATTACK   --out <OUT.csv>
```

> For `run5_dataset.csv` the run count was **200** per class (total 400).

---

## Stage 1 outputs + results (latest)

The following files exist under your artifact-root layout:

- `out/csv/stage1/threadripper/first run_ripper/run1_dataset.csv`
- `out/csv/stage1/threadripper/first run_ripper/run2_dataset.csv`
- `out/csv/stage1/threadripper/first run_ripper/run3_dataset.csv`
- `out/csv/stage1/threadripper/first run_ripper/run4_dataset.csv`
- `out/csv/stage1/threadripper/first run_ripper/run5_dataset.csv`
- `out/csv/stage1/threadripper/first run_ripper/run6_negctrl_vs_base.csv`  (negative control; see Stage 1.6)

### Stage 1 summary table

| Dataset file | Samples | ODS AUC (analyze) | GAP AUC (analyze) | Bootstrap AUC mean (ODS) | 95% CI | Bootstrap BalAcc mean | 95% CI |
|---|---:|---:|---:|---:|---|---:|---|
| run1_dataset.csv | 200 (100/100) | 0.979 | 0.983 | 0.979 | [0.958, 0.995] | 0.958 | [0.930, 0.984] |
| run2_dataset.csv | 200 (100/100) | 0.975 | 0.974 | 0.975 | [0.950, 0.994] | 0.943 | [0.910, 0.973] |
| run3_dataset.csv | 200 (100/100) | 0.923 | 0.918 | 0.924 | [0.890, 0.953] | 0.839 | [0.795, 0.883] |
| run4_dataset.csv | 200 (100/100) | 0.748 | 0.774 | 0.748 | [0.679, 0.815] | 0.750 | [0.689, 0.808] |
| run5_dataset.csv | 400 (200/200) | 0.949 | 0.940 | 0.949 | [0.927, 0.970] | 0.890 | [0.860, 0.917] |

**Interpretation (Stage 1):**
- On Threadripper, attacker presence is **very strongly** distinguishable (AUC often **0.92–0.98** depending on dataset).
- `run4_dataset.csv` is the weakest among these but still **publishable** (AUC ≈ 0.75 with CI above chance).

---

## Stage 1.6 — Negative control (off-core attacker): `run6_negctrl_vs_base.csv`

**Goal:** show that when the attacker is placed **off-core** (not sharing victim cores), the signal collapses toward chance.

### Terminal 3 — off-core attacker
```bash
cd ~/projects/ordleak
taskset -c 2-31 python3 -u src/attacker.py --procs 32 --seconds 999999
```

### Terminal 1 — victim (CPU mode)
```bash
cd ~/projects/ordleak
rm -f out/victim.sock
taskset -c 0,1 python3 -u src/victim.py --sock out/victim_cpu.sock --mode cpu --workers 2 --iters 200000
```

### Terminal 2 — dataset collection (two labels in one CSV)
```bash
cd ~/projects/ordleak
ln -sf victim_cpu.sock out/victim.sock

# NEGCTRL_OFFCORE
taskset -c 0,1 python3 scripts/run_dataset.py   --runs 100 --n 20   --label NEGCTRL_OFFCORE   --out out/csv/stage1/threadripper/first\ run_ripper/run6_negctrl_vs_base.csv

# BASELINE
taskset -c 0,1 python3 scripts/run_dataset.py   --runs 100 --n 20   --label BASELINE   --out out/csv/stage1/threadripper/first\ run_ripper/run6_negctrl_vs_base.csv
```

### Analysis commands + results (latest)
```bash
cd ~/projects/ordleak
python3 scripts/analyze.py out/csv/stage1/threadripper/first\ run_ripper/run6_negctrl_vs_base.csv   --pos-label NEGCTRL_OFFCORE --neg-label BASELINE

python3 scripts/bootstrap_ci.py out/csv/stage1/threadripper/first\ run_ripper/run6_negctrl_vs_base.csv   --pos-label NEGCTRL_OFFCORE --neg-label BASELINE
```

- ODS AUC (analyze): **0.535**
- GAP AUC (analyze): **0.530**
- Bootstrap AUC mean (ODS): **0.535**, 95% CI **[0.458, 0.612]**
- Bootstrap BalAcc mean: **0.544**, 95% CI **[0.500, 0.596]**

**Interpretation:** negative control is **near chance**, supporting that **co-resident** contention is necessary for the strong Stage 1 signal.

---

---
## Stage 1 outputs + results (Intel i9-7900X)

Files (your current layout):

- `out/csv/stage1/intel_i9_7900x/runset1/run1_dataset.csv`
- `out/csv/stage1/intel_i9_7900x/runset1/run2_dataset.csv`
- `out/csv/stage1/intel_i9_7900x/runset1/run3_dataset.csv`
- `out/csv/stage1/intel_i9_7900x/runset1/run4_dataset.csv`
- `out/csv/stage1/intel_i9_7900x/runset1/run5_dataset.csv`
- `out/csv/stage1/intel_i9_7900x/runset1/run6_negctrl_vs_base.csv`  (negative control)

### Stage 1 summary table (Intel)

| Dataset file | Samples | ODS AUC (analyze) | GAP AUC (analyze) | Bootstrap AUC mean (ODS) | 95% CI | Bootstrap BalAcc mean | 95% CI |
|---|---:|---:|---:|---:|---|---:|---|
| run1_dataset.csv | 200 (100/100) | 0.974 | 0.979 | 0.975 | [0.953, 0.990] | 0.945 | [0.912, 0.975] |
| run2_dataset.csv | 200 (100/100) | 0.992 | 0.987 | 0.992 | [0.984, 0.998] | 0.970 | [0.945, 0.990] |
| run3_dataset.csv | 200 (100/100) | 0.967 | 0.964 | 0.967 | [0.946, 0.983] | 0.906 | [0.866, 0.945] |
| run4_dataset.csv | 200 (100/100) | 0.959 | 0.951 | 0.959 | [0.929, 0.983] | 0.922 | [0.885, 0.957] |
| run5_dataset.csv | 200 (100/100) | 0.975 | 0.968 | 0.975 | [0.958, 0.988] | 0.920 | [0.881, 0.955] |
| run6_negctrl_vs_base.csv | 200 (100/100) | 0.544 | 0.581 | 0.544 | [0.472, 0.616] | 0.561 | [0.522, 0.602] |

**Interpretation (Stage 1, Intel):**
- Attacker presence is **very strongly** distinguishable across `run1–run5` (AUC ≈ **0.959–0.992**).
- The off-core negative control (`run6_negctrl_vs_base.csv`) drops close to chance (AUC **0.544**, CI includes 0.50), which is consistent with "no shared-core contention ⇒ weak/no signal".

# Stage 2 — Secret-mode leakage (CPU vs MEM)

**Goal (Stage 2):** introduce an explicit **victim secret** (mode = `cpu` vs `mem`) and measure how much an attacker amplifies **mode distinguishability** from rank-only completion order.

Stage 2 produces:
- `secret_tr_base.csv` : CPU_BASE vs MEM_BASE (**no attacker**)
- `secret_tr_att.csv`  : CPU_ATT vs MEM_ATT (**with co-resident attacker**)
- `negctrl_stage2.csv` : CPU_NEGCTRL_OFFCORE vs MEM_NEGCTRL_OFFCORE (**off-core attacker**)

## Stage 2 — Summary table (Threadripper)

| Dataset file | Classes (pos vs neg) | Samples | ODS AUC (analyze) | GAP AUC (analyze) | Bootstrap AUC mean (ODS) | 95% CI | Bootstrap BalAcc mean | 95% CI | Notes |
|---|---|---:|---:|---:|---:|---|---:|---|---|
| `out/csv/stage2/threadripper/secret_tr_base.csv` | `MEM_BASE` vs `CPU_BASE` | 200 (100/100) | 0.476 | 0.466 | 0.476 | [0.400, 0.551] | 0.527 | [0.500, 0.576] | No attacker; near chance |
| `out/csv/stage2/threadripper/secret_tr_att.csv` | `MEM_ATT` vs `CPU_ATT` | 200 (100/100) | 0.800 | 0.783 | 0.800 | [0.731, 0.863] | 0.791 | [0.734, 0.845] | Co-resident attacker; strong signal |
| `out/csv/stage2/threadripper/negctrl_stage2.csv` | `MEM_NEGCTRL_OFFCORE` vs `CPU_NEGCTRL_OFFCORE` | 200 (100/100) | 0.447 | 0.468 | 0.447 | [0.370, 0.528] | 0.551 | [0.507, 0.596] | Off-core attacker; near chance (no amplification) |

## How Stage 2 datasets were generated (Threadripper)

### 2.1 `secret_tr_base.csv` (no attacker)

**Terminal 1 — victim CPU**
```bash
cd ~/projects/ordleak
rm -f out/victim.sock
taskset -c 0,1 python3 -u src/victim.py --sock out/victim_cpu.sock --mode cpu --workers 2 --iters 200000
```

**Terminal 2 — collect CPU_BASE**
```bash
cd ~/projects/ordleak
ln -sf victim_cpu.sock out/victim.sock
taskset -c 0,1 python3 scripts/run_dataset.py   --runs 100 --n 20   --label CPU_BASE   --out out/csv/stage2/threadripper/secret_tr_base.csv
```

**Terminal 1 — victim MEM**
```bash
cd ~/projects/ordleak
rm -f out/victim.sock
taskset -c 0,1 python3 -u src/victim.py --sock out/victim_mem.sock --mode mem --mem-kb 8192 --workers 2 --iters 200000
```

**Terminal 2 — collect MEM_BASE (append)**
```bash
cd ~/projects/ordleak
ln -sf victim_mem.sock out/victim.sock
taskset -c 0,1 python3 scripts/run_dataset.py   --runs 100 --n 20   --label MEM_BASE   --out out/csv/stage2/threadripper/secret_tr_base.csv
```

### Results (latest): `secret_tr_base.csv` (MEM_BASE vs CPU_BASE)

```bash
cd ~/projects/ordleak
python3 scripts/analyze.py out/csv/stage2/threadripper/secret_tr_base.csv --pos-label MEM_BASE --neg-label CPU_BASE
python3 scripts/bootstrap_ci.py out/csv/stage2/threadripper/secret_tr_base.csv --pos-label MEM_BASE --neg-label CPU_BASE
```

- ODS AUC (analyze): **0.476**
- GAP AUC (analyze): **0.466**
- Bootstrap AUC mean (ODS): **0.476**, 95% CI **[0.400, 0.551]**
- Bootstrap BalAcc mean: **0.527**, 95% CI **[0.500, 0.576]**

**Interpretation:** without attacker, CPU vs MEM mode is **near chance** from rank-only order.

---

### 2.2 `secret_tr_att.csv` (co-resident attacker)

**Terminal 1 — victim CPU**
```bash
cd ~/projects/ordleak
rm -f out/victim.sock
taskset -c 0,1 python3 -u src/victim.py --sock out/victim_cpu.sock --mode cpu --workers 2 --iters 200000
```

**Terminal 2 — collect CPU_ATT**
```bash
cd ~/projects/ordleak
ln -sf victim_cpu.sock out/victim.sock
taskset -c 0,1 python3 scripts/run_dataset.py   --runs 100 --n 20   --attack --attack-procs 32 --attack-seconds 5   --label CPU_ATT   --out out/csv/stage2/threadripper/secret_tr_att.csv
```

**Terminal 1 — victim MEM**
```bash
cd ~/projects/ordleak
rm -f out/victim.sock
taskset -c 0,1 python3 -u src/victim.py --sock out/victim_mem.sock --mode mem --mem-kb 8192 --workers 2 --iters 200000
```

**Terminal 2 — collect MEM_ATT (append)**
```bash
cd ~/projects/ordleak
ln -sf victim_mem.sock out/victim.sock
taskset -c 0,1 python3 scripts/run_dataset.py   --runs 100 --n 20   --attack --attack-procs 32 --attack-seconds 5   --label MEM_ATT   --out out/csv/stage2/threadripper/secret_tr_att.csv
```

### Results: `secret_tr_att.csv` (MEM_ATT vs CPU_ATT)

```bash
cd ~/projects/ordleak
python3 scripts/analyze.py out/csv/stage2/threadripper/secret_tr_att.csv --pos-label MEM_ATT --neg-label CPU_ATT
python3 scripts/bootstrap_ci.py out/csv/stage2/threadripper/secret_tr_att.csv --pos-label MEM_ATT --neg-label CPU_ATT
```

- ODS AUC (analyze): **0.800**
- GAP AUC (analyze): **0.783**
- Bootstrap AUC mean (ODS): **0.800**, 95% CI **[0.731, 0.863]**
- Bootstrap BalAcc mean: **0.791**, 95% CI **[0.734, 0.845]**

**Interpretation:** with co-resident attacker, CPU vs MEM mode becomes **strongly** distinguishable (AUC ~0.80).

---

## 2.3 `negctrl_stage2.csv` (off-core attacker) — DONE

**Goal:** show that placing the attacker **off-core** removes the *amplification* of CPU vs MEM distinguishability.

### Dataset
- File: `out/csv/stage2/threadripper/negctrl_stage2.csv`
- Classes: `CPU_NEGCTRL_OFFCORE` vs `MEM_NEGCTRL_OFFCORE`
- Attacker pinned off victim cores (Threadripper example): `2-31`
- Victim + dataset runner pinned to: `0,1`

### Analysis (latest)

```bash
cd ~/projects/ordleak
python3 scripts/analyze.py out/csv/stage2/threadripper/negctrl_stage2.csv --pos-label MEM_NEGCTRL_OFFCORE --neg-label CPU_NEGCTRL_OFFCORE
python3 scripts/bootstrap_ci.py out/csv/stage2/threadripper/negctrl_stage2.csv --pos-label MEM_NEGCTRL_OFFCORE --neg-label CPU_NEGCTRL_OFFCORE
```

### Results
- ODS AUC (analyze): **0.447**
- GAP AUC (analyze): **0.468**
- Bootstrap AUC mean (ODS): **0.447**, 95% CI **[0.370, 0.528]**
- Bootstrap BalAcc mean: **0.551**, 95% CI **[0.507, 0.596]**

### Interpretation
Near chance ⇒ off-core attacker does **not** amplify CPU vs MEM mode distinguishability, consistent with the co-resident contention mechanism.

---

# Discussion (what these results mean)

1. **Stage 1 is extremely strong on Threadripper.**
   Across multiple datasets, BASELINE vs ATTACK is reliably distinguishable from rank-only completion order, with AUC often > 0.95.

2. **Negative control supports the mechanism.**
   Off-core attacker collapses to near chance (AUC ≈ 0.53 with CI overlapping 0.5), consistent with "co-resident contention required".

3. **Stage 2 addresses the "where is the secret?" reviewer point.**
   The secret is the victim mode (`cpu` vs `mem`), not merely attacker presence.

4. **Attacker amplifies secret leakage in Stage 2.**
   Baseline (no attacker) is near chance, but under co-resident contention we see strong mode distinguishability (AUC ~0.80).

5. **Stage 3 shows BOS can eliminate leakage.**
   With sufficient window size (W ≥ 14), order-based leakage is reduced to random guessing.
   
   

# ordleak — RESULTS (Intel i9-7900X)

This file mirrors the **Stage 1** structure used for the Threadripper, but contains the **Intel i9-7900X** reproduction.

---

## Testbed

- CPU: Intel(R) Core(TM) i9-7900X (10C/20T)
- Pinning: victim + dataset on **`taskset -c 0,1`**
  - On this CPU: `0` is HT-sibling with `10`, and `1` with `11`.
  - Using `0,1` therefore places victim+dataset on two **different physical cores** (and avoids HT siblings).

---

# Stage 1 — attacker presence leakage (BASELINE vs ATTACK)

**Goal (Stage 1):** detect **co-resident attacker presence** from **rank-only completion order**.

**Files (Intel runset):**
- `out/csv/stage1/intel_i9_7900x/runset1/run1_dataset.csv`
- `out/csv/stage1/intel_i9_7900x/runset1/run2_dataset.csv`
- `out/csv/stage1/intel_i9_7900x/runset1/run3_dataset.csv`
- `out/csv/stage1/intel_i9_7900x/runset1/run4_dataset.csv`
- `out/csv/stage1/intel_i9_7900x/runset1/run5_dataset.csv`

**How Stage 1 datasets were generated (template):**
```bash
# Terminal 1: victim
cd ~/projects/ordleak
rm -f out/victim.sock out/victim_cpu.sock
taskset -c 0,1 python3 -u src/victim.py --sock out/victim_cpu.sock --mode cpu --workers 2 --iters 200000

# Terminal 2: stable socket
cd ~/projects/ordleak
ln -sf victim_cpu.sock out/victim.sock

# Terminal 2: dataset (BASELINE then ATTACK into same CSV)
taskset -c 0,1 python3 scripts/run_dataset.py --runs 100 --n 20 --label BASELINE --out out/csv/stage1/intel_i9_7900x/runset1/runX_dataset.csv
taskset -c 0,1 python3 scripts/run_dataset.py --runs 100 --n 20 --attack --attack-procs <P> --attack-seconds <S> --label ATTACK --out out/csv/stage1/intel_i9_7900x/runset1/runX_dataset.csv
```

## Stage 1 results (Intel i9-7900X)

| Run | Dataset file | Attack params | Samples | ODS AUC (analyze) | GAP AUC (analyze) | Bootstrap AUC mean (ODS) | 95% CI | Bootstrap BalAcc mean | 95% CI |
|---:|---|---|---:|---:|---:|---:|---|---:|---|
| 1 | `out/csv/stage1/intel_i9_7900x/runset1/run1_dataset.csv` | procs=None, sec=None | 200 (100/100) | 0.974 | 0.979 | 0.975 | [0.953, 0.990] | 0.945 | [0.912, 0.975] |
| 2 | `out/csv/stage1/intel_i9_7900x/runset1/run2_dataset.csv` | procs=None, sec=None | 200 (100/100) | 0.992 | 0.987 | 0.992 | [0.984, 0.998] | 0.970 | [0.945, 0.990] |
| 3 | `out/csv/stage1/intel_i9_7900x/runset1/run3_dataset.csv` | procs=None, sec=None | 200 (100/100) | 0.967 | 0.964 | 0.967 | [0.946, 0.983] | 0.906 | [0.866, 0.945] |
| 4 | `out/csv/stage1/intel_i9_7900x/runset1/run4_dataset.csv` | procs=None, sec=None | 200 (100/100) | 0.959 | 0.951 | 0.959 | [0.929, 0.983] | 0.922 | [0.885, 0.957] |
| 5 | `out/csv/stage1/intel_i9_7900x/runset1/run5_dataset.csv` | procs=None, sec=None | 200 (100/100) | 0.975 | 0.968 | 0.975 | [0.958, 0.988] | 0.920 | [0.881, 0.955] |

**Interpretation:** Stage 1 is **strongly reproducible** on Intel: ODS AUCs are consistently high (≈0.96–0.99), i.e., attacker presence is detectable from **rank-only completion order**.

---

# Stage 1.6 — negative control (off-core attacker)

**Goal:** attacker runs **off-core** (not sharing victim cores), so we expect **near-chance**.

### Generation (latest)
Terminal 3 (off-core attacker):
```bash
cd ~/projects/ordleak
taskset -c 2-19 python3 -u src/attacker.py --procs 18 --seconds 999999
```

Terminal 1 (victim) and Terminal 2 (symlink) as in Stage 1.

Terminal 2 (collect NEGCTRL + BASELINE into one CSV):
```bash
cd ~/projects/ordleak
mkdir -p out/csv/stage1/intel_i9_7900x/runset1
ln -sf victim_cpu.sock out/victim.sock

# With off-core attacker running:
taskset -c 0,1 python3 scripts/run_dataset.py --runs 100 --n 20 --label NEGCTRL_OFFCORE --out out/csv/stage1/intel_i9_7900x/runset1/run6_negctrl_vs_base.csv

# Stop Terminal 3 (attacker), then collect baseline:
taskset -c 0,1 python3 scripts/run_dataset.py --runs 100 --n 20 --label BASELINE --out out/csv/stage1/intel_i9_7900x/runset1/run6_negctrl_vs_base.csv
```

### Analysis commands + results (latest)

Clean-direction (BASELINE as positive label):
```bash
cd ~/projects/ordleak
python3 scripts/analyze.py out/csv/stage1/intel_i9_7900x/runset1/run6_negctrl_vs_base.csv --pos-label BASELINE --neg-label NEGCTRL_OFFCORE
python3 scripts/bootstrap_ci.py out/csv/stage1/intel_i9_7900x/runset1/run6_negctrl_vs_base.csv --pos-label BASELINE --neg-label NEGCTRL_OFFCORE
```

- ODS AUC (analyze): **0.456**
- GAP AUC (analyze): **0.419**
- Bootstrap AUC mean (ODS): **0.456**, 95% CI **[0.384, 0.528]**
- Bootstrap BalAcc mean: **0.510**, 95% CI **[0.500, 0.558]**

Threadripper-style direction (NEGCTRL_OFFCORE as positive label; same dataset, flipped labels):
```bash
cd ~/projects/ordleak
python3 scripts/bootstrap_ci.py out/csv/stage1/intel_i9_7900x/runset1/run6_negctrl_vs_base.csv --pos-label NEGCTRL_OFFCORE --neg-label BASELINE
```

- Bootstrap AUC mean (ODS): **0.544**, 95% CI **[0.472, 0.616]**
- Bootstrap BalAcc mean: **0.561**, 95% CI **[0.522, 0.602]**

**Interpretation:** negative control is **near chance** (AUC CI overlaps 0.5), supporting that **co-resident** contention is necessary for the strong Stage 1 signal.

---

## Notes / gotcha (why negctrl can look "not chance")

If the attacker is accidentally still running during the "BASELINE" half of `run6_negctrl_vs_base.csv`, the file is not a clean negative control and can show a spurious signal. The commands above explicitly stop the off-core attacker before collecting BASELINE.

---
## Stage 2 outputs + results (Intel i9-7900X)

Files (your current layout):

- `out/csv/stage2/i9_7900x/secret_intel_stage2_base.csv`  (`CPU_BASE` + `MEM_BASE`)
- `out/csv/stage2/i9_7900x/secret_intel_stage2_att.csv`   (`CPU_ATT` + `MEM_ATT`)
- `out/csv/stage2/i9_7900x/negctrl_intel_stage2.csv`       (`CPU_NEGCTRL_OFFCORE` + `MEM_NEGCTRL_OFFCORE`)

### Stage 2 summary table (Intel)

| Dataset file | Labels | Samples | ODS AUC (analyze) | GAP AUC (analyze) | Bootstrap AUC mean (ODS) | 95% CI | Bootstrap BalAcc mean | 95% CI | Notes |
|---|---|---:|---:|---:|---:|---|---:|---|---|
| `out/csv/stage2/i9_7900x/secret_intel_stage2_base.csv` | `MEM_BASE` vs `CPU_BASE` | 200 (100/100) | 0.468 | 0.485 | 0.468 | [0.399, 0.538] | 0.517 | [0.500, 0.556] | No attacker; near chance |
| `out/csv/stage2/i9_7900x/secret_intel_stage2_att.csv` | `MEM_ATT` vs `CPU_ATT` | 200 (100/100) | 0.738 | 0.727 | 0.739 | [0.666, 0.807] | 0.723 | [0.665, 0.779] | Co-resident attacker; amplified signal |
| `out/csv/stage2/i9_7900x/negctrl_intel_stage2.csv` | `MEM_NEGCTRL_OFFCORE` vs `CPU_NEGCTRL_OFFCORE` | 200 (100/100) | 0.587 | 0.601 | 0.587 | [0.522, 0.651] | 0.590 | [0.525, 0.653] | Off-core attacker; should be near chance |

**Interpretation (Stage 2, Intel):**
- **Baseline secret leakage** (`CPU_BASE` vs `MEM_BASE`) is **near chance** (AUC **0.468**).
- With the attacker, **secret leakage becomes clearly measurable** (AUC **0.739**), i.e., attacker presence **amplifies** the CPU-vs-MEM mode difference in rank-only completion order.
- The stage-2 negative control is **only weak/moderate** (AUC **0.587**) — ideally closer to 0.5; keep this as a "sanity check" result and (if needed) re-run with stricter off-core pinning and/or fewer background processes.

---

# Stage 3 — Defense: BOS Scrubber Results (Threadripper)

**Goal:** Measure the **leakage–overhead tradeoff** of Budgeted Order Scrubbing (BOS v1).

## Defense mechanism

BOS v1 buffers completion IDs in a window of size `W` and flushes them in a **keyed pseudorandom permutation** using a seeded PRNG shuffle.

- `W=0`: scrubber off (baseline)
- `W>=1`: buffer up to W IDs before flushing in permuted order

**Threat model:**
- Seed is a **server-side secret** (not observable by attacker)
- Window size `W` may be observable (bursty output)
- PRNG state is continuous (not reset per flush)

## Defense files

```
out/csv/stage3/
├── stage2_att_W0_r100.csv
├── stage2_att_W4_r100.csv
├── stage2_att_W8_r100.csv
├── stage2_att_W12_r100.csv
├── stage2_att_W14_r100.csv
└── stage2_att_W16_r100.csv
```

## Experimental setup (Stage 3)

- **Scenario:** Stage 2 ATT (CPU_ATT vs MEM_ATT) with BOS scrubber enabled
- **Samples:** 100 runs per class (200 total per W value)
- **Pinning:** `taskset -c 0,1` for victim + dataset runner
- **Attack:** `--attack-procs 16 --attack-seconds 5`
- **Victim params:** `--workers 2 --iters 200000 --mem-kb 8192` (for MEM mode)
- **Scrubber:** `--scrub-window W --scrub-seed 42`

---

## AUC vs W (Stage 2 ATT: `MEM_ATT` vs `CPU_ATT`)

| W | Samples | ODS AUC | ODS 95% CI | GAP_VAR AUC | Interpretation |
|---:|---:|---:|---|---:|---|
| 0 (baseline) | 200 (100/100) | **0.821** | [0.759, 0.878] | 0.835 | Strong leakage (baseline) |
| 4 | 200 (100/100) | **0.750** | — | 0.724 | Leakage reduced, but still present |
| 8 | 200 (100/100) | **0.773** | [0.700, 0.845] | 0.789 | Non-monotonic: higher than W=4 |
| 12 | 200 (100/100) | **0.677** | [0.601, 0.749] | 0.514 | ODS "weak", GAP_VAR ≈ random |
| 14 | 200 (100/100) | **0.501** | [0.420, 0.580] | 0.597 | ODS ≈ random, GAP_VAR slight signal |
| 16 | 200 (100/100) | **0.449** | [0.369, 0.530] | 0.461 | Both ≈ random (leakage eliminated) |

---

## Key findings

### 1) Baseline leakage is real and stable
At W=0, the secret (CPU vs MEM) is strongly distinguishable:
- ODS AUC **0.821**
- GAP_VAR AUC **0.835**

With tight CIs → this is not noise.

### 2) BOS is tunable – but not monotonic
Leakage generally decreases with larger W, but **not strictly monotonically**:
- W=4 reduces leakage (ODS 0.75)
- W=8 **increases again** (ODS 0.773, GAP_VAR 0.789)

**Design insight:** Certain window sizes can create new patterns (chunk/flush effects) that are again classifiable.

### 3) Transition zone and threshold
- **W=12:** ODS only "weak" (0.677), GAP_VAR ≈ random (0.514)
- **W=14:** ODS is effectively neutralized (0.501, CI spans 0.5)
- **W=16:** Both metrics clearly random (ODS 0.449, GAP_VAR 0.461)

**Takeaway:** In this threat model, the "safe" zone for order-based leakage is approximately **W ≥ 14**.

### 4) Feature perspective (ODS vs GAP_VAR)
- **ODS** (order-based) is effectively neutralized at W ≈ 14
- **GAP_VAR** shows residual signal at W=14 (0.597), but becomes random at W=16 (0.461)

This can be framed as: "secondary signal sometimes persists at intermediate W".

---

## Reviewer-ready summary

| Claim | Evidence |
|-------|----------|
| Leakage is significant without defense | W=0: AUC ≈ 0.82–0.84 |
| BOS can eliminate leakage | W=16: AUC ≈ 0.45–0.46 (random) |
| Non-monotonic behavior exists | W=8 leaks more than W=4 |
| Practical recommendation | Choose **W ≥ 14** to suppress order-based leakage |

---

## Overhead vs W

We measured BOS runtime overhead in two configurations:
- **Option A (with attack):** End-to-end runtime including co-resident attacker (5s contention per run)
- **Option B (pure):** Runtime without attacker (isolates BOS cost)

Each measurement: 5 repetitions × 100 runs × 20 jobs = 10,000 jobs per (W, mode) combination.

### Option A: End-to-end under attack

| W | CPU runtime (s) | CPU overhead | MEM runtime (s) | MEM overhead |
|---:|---:|---:|---:|---:|
| 0 | 518.67 ± 0.29 | baseline | 518.24 ± 0.22 | baseline |
| 4 | 518.37 ± 0.22 | −0.06% | 518.42 ± 0.45 | +0.03% |
| 8 | 518.72 ± 0.23 | +0.01% | 518.51 ± 0.22 | +0.05% |
| 12 | 518.76 ± 0.11 | +0.02% | 518.36 ± 0.20 | +0.02% |
| 14 | 518.58 ± 0.30 | −0.02% | 518.31 ± 0.23 | +0.01% |
| 16 | 518.58 ± 0.24 | −0.02% | 518.25 ± 0.24 | +0.00% |

### Option B: Pure overhead (no attacker)

| W | CPU runtime (s) | CPU overhead | MEM runtime (s) | MEM overhead |
|---:|---:|---:|---:|---:|
| 0 | 46.65 ± 0.05 | baseline | 31.51 ± 0.02 | baseline |
| 4 | 46.65 ± 0.04 | −0.00% | 31.52 ± 0.04 | +0.01% |
| 8 | 46.62 ± 0.03 | −0.06% | 31.35 ± 0.30 | −0.51% |
| 12 | 46.64 ± 0.02 | −0.03% | 31.45 ± 0.20 | −0.20% |
| 14 | 46.66 ± 0.05 | +0.02% | 31.51 ± 0.02 | +0.00% |
| 16 | 46.66 ± 0.05 | +0.03% | 31.52 ± 0.01 | +0.03% |

### Interpretation

BOS adds **no measurable runtime overhead** (<0.1% in all configurations). Under attack, runtime is dominated by attacker-induced delays; without attacker, buffering and shuffling costs remain in the noise floor. The defense is effectively "free" in our threat model.


---

# Case Study: KDF Fingerprinting (PBKDF2 vs. scrypt)

## Goal

Validate that completion-order fingerprinting generalizes from synthetic CPU/MEM workloads to real cryptographic primitives:
- **PBKDF2-HMAC-SHA256** (CPU-bound KDF, 100k iterations)
- **scrypt** (memory-hard KDF, N=16384, r=8, p=1)

## Setup

- Victim modes: `--mode pbkdf2` and `--mode scrypt`
- Samples: 50 runs per class, n=50 jobs per run
- No attacker (clean channel)
- Pinning: `taskset -c 0,1`

## Files
```
out/csv/study/
├── kdf_stage2_W0_test.csv
└── kdf_stage2_W16_test.csv
```

## Results

### W=0 (no defense)

| Metric | SCRYPT | PBKDF2 | Cohen's d | AUC |
|--------|--------|--------|-----------|-----|
| ODS | 0.0089 ± 0.0048 | 0.0287 ± 0.0080 | 2.995 | **0.985** |
| GAP_VAR | 0.4678 ± 0.3104 | 2.4365 ± 1.2976 | 2.087 | 0.979 |

Bootstrap (B=5000): AUC mean=0.985, 95% CI [0.963, 0.999]

Best threshold accuracy: 94.0%

### W=16 (BOS defense)

| Metric | AUC | Bootstrap 95% CI |
|--------|-----|------------------|
| ODS | **0.514** | [0.406, 0.621] |

Bootstrap (B=5000): AUC mean=0.513

**Signal eliminated** — CI includes 0.5.

## Summary Table

| W | ODS AUC | 95% CI | Interpretation |
|---:|---:|---|---|
| 0 | **0.985** | [0.963, 0.999] | Strong leakage |
| 16 | **0.514** | [0.406, 0.621] | No signal (BOS works) |

## Interpretation

PBKDF2 induces higher completion-order disruption than scrypt despite being faster (~17ms vs ~33ms per call). This is explained by **service-time variance**: PBKDF2 (CPU-bound) shows higher variability, causing more job reordering; scrypt (memory-hard) runs more consistently.

With BOS (W=16), AUC drops from 0.985 to 0.514 — confirming that the defense generalizes to real cryptographic workloads.
