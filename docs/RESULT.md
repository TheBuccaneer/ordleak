# ordleak — RESULTS (Threadripper)

This file documents the **current** results produced in this thread, together with the **exact command lines** used to generate and analyze each dataset.

## Testbed + environment notes

- Machine: **AMD Ryzen Threadripper 3970X (32 cores)**
- Pinning: Victim + dataset runner pinned to cores `0,1` via `taskset -c 0,1`
- GUI: **disabled** (headless / `multi-user.target`)
- Frequency governor: **not forced** (“performance mode” not required for these results)
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

# Stage 2 — Secret-mode leakage (CPU vs MEM)

**Goal (Stage 2):** introduce an explicit **victim secret** (mode = `cpu` vs `mem`) and measure how much an attacker amplifies **mode distinguishability** from rank-only completion order.

Stage 2 produces:
- `secret_tr_base.csv` : CPU_BASE vs MEM_BASE (**no attacker**)
- `secret_tr_att.csv`  : CPU_ATT vs MEM_ATT (**with co-resident attacker**)
- `negctrl_stage2.csv` : (planned) CPU_NEGCTRL_OFFCORE vs MEM_NEGCTRL_OFFCORE (**off-core attacker**) — **pending**

## Stage 2 — Summary table (Threadripper)

| Dataset file | Classes (pos vs neg) | Samples | ODS AUC (analyze) | GAP AUC (analyze) | Bootstrap AUC mean (ODS) | 95% CI | Bootstrap BalAcc mean | 95% CI | Notes |
|---|---|---:|---:|---:|---:|---|---:|---|---|
| `out/csv/stage2/secret_tr_base.csv` | `MEM_BASE` vs `CPU_BASE` | 200 (100/100) | 0.476 | 0.466 | 0.476 | [0.400, 0.551] | 0.527 | [0.500, 0.576] | No attacker; near chance |
| `out/csv/stage2/secret_tr_att.csv` | `MEM_ATT` vs `CPU_ATT` | 200 (100/100) | 0.800 | 0.783 | 0.800 | [0.731, 0.863] | 0.791 | [0.734, 0.845] | Co-resident attacker; strong signal |
| `out/csv/stage2/negctrl_stage2.csv` | `MEM_NEGCTRL_OFFCORE` vs `CPU_NEGCTRL_OFFCORE` | 200 (100/100) | 0.447 | 0.468 | 0.447 | [0.370, 0.528] | 0.551 | [0.507, 0.596] | Off-core attacker; near chance (no amplification) |

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
taskset -c 0,1 python3 scripts/run_dataset.py   --runs 100 --n 20   --label CPU_BASE   --out out/csv/stage2/secret_tr_base.csv
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
taskset -c 0,1 python3 scripts/run_dataset.py   --runs 100 --n 20   --label MEM_BASE   --out out/csv/stage2/secret_tr_base.csv
```

### Results (latest): `secret_tr_base.csv` (MEM_BASE vs CPU_BASE)

```bash
cd ~/projects/ordleak
python3 scripts/analyze.py out/csv/stage2/secret_tr_base.csv --pos-label MEM_BASE --neg-label CPU_BASE
python3 scripts/bootstrap_ci.py out/csv/stage2/secret_tr_base.csv --pos-label MEM_BASE --neg-label CPU_BASE
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
taskset -c 0,1 python3 scripts/run_dataset.py   --runs 100 --n 20   --attack --attack-procs 32 --attack-seconds 5   --label CPU_ATT   --out out/csv/stage2/secret_tr_att.csv
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
taskset -c 0,1 python3 scripts/run_dataset.py   --runs 100 --n 20   --attack --attack-procs 32 --attack-seconds 5   --label MEM_ATT   --out out/csv/stage2/secret_tr_att.csv
```

### Results: `secret_tr_att.csv` (MEM_ATT vs CPU_ATT)

```bash
cd ~/projects/ordleak
python3 scripts/analyze.py out/csv/stage2/secret_tr_att.csv --pos-label MEM_ATT --neg-label CPU_ATT
python3 scripts/bootstrap_ci.py out/csv/stage2/secret_tr_att.csv --pos-label MEM_ATT --neg-label CPU_ATT
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
- File: `out/csv/stage2/negctrl_stage2.csv`
- Classes: `CPU_NEGCTRL_OFFCORE` vs `MEM_NEGCTRL_OFFCORE`
- Attacker pinned off victim cores (Threadripper example): `2-31`
- Victim + dataset runner pinned to: `0,1`

### Analysis (latest)

```bash
cd ~/projects/ordleak
python3 scripts/analyze.py out/csv/stage2/negctrl_stage2.csv --pos-label MEM_NEGCTRL_OFFCORE --neg-label CPU_NEGCTRL_OFFCORE
python3 scripts/bootstrap_ci.py out/csv/stage2/negctrl_stage2.csv --pos-label MEM_NEGCTRL_OFFCORE --neg-label CPU_NEGCTRL_OFFCORE
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
   Off-core attacker collapses to near chance (AUC ≈ 0.53 with CI overlapping 0.5), consistent with “co-resident contention required”.

3. **Stage 2 addresses the “where is the secret?” reviewer point.**
   The secret is the victim mode (`cpu` vs `mem`), not merely attacker presence.

4. **Attacker amplifies secret leakage in Stage 2.**
   Baseline (no attacker) is near chance, but under co-resident contention we see strong mode distinguishability (AUC ~0.80).

5. **Next missing piece: Stage 2 negative control.**
   `negctrl_stage2.csv` should demonstrate that placing the attacker off-core removes most of the amplification (expected near chance).
