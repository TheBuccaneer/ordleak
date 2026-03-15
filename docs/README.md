# ordleak

**ordleak** studies whether **rank-only completion order** in an asynchronous host–service protocol leaks information under **co-resident CPU contention** – and how such leakage can be mitigated.

The project intentionally assumes a **weak observer**:
- no timestamps,
- no fine-grained performance counters,
- only the **relative order** in which jobs complete (`DONE <id>`).

This mirrors realistic IPC / service scenarios where clients only see *which request finished first*, not *how long it took*.

---

## Threat model (high-level)

- **Victim**: user-space service executing jobs via a worker pool  
- **Observer**: unprivileged client that only sees **completion order** (rank-only)  
- **Attacker**: unprivileged co-resident process creating CPU contention  
- **Goal**: infer information from **ordering effects alone**

We explicitly **do not** rely on timers, perf counters, or privileged instrumentation.

---

## Repo layout

```text
src/
  victim.py              # service / victim workload (cpu|mem modes, BOS scrubber)
  client_rank_only.py    # observer client (rank-only)
  attacker.py            # CPU contention generator

scripts/
  run_dataset.py         # experiment runner (produces CSVs)
  analyze.py             # computes ODS, GAP_VAR, AUC, Cohen's d
  bootstrap_ci.py        # bootstrap CIs for AUC & balanced accuracy

out/csv/
  stage1/                # Stage 1 datasets (presence leakage)
  stage2/                # Stage 2 datasets (secret leakage)
  stage3/                # Stage 3 datasets (defense / BOS scrubber evaluation)
```

---

## Stages

### Stage 1 — attacker presence leakage

**Question:** Is the **presence** of a co-resident attacker detectable from completion order alone?

**Setup:**
- Victim executes identical jobs in all runs
- Two conditions:
  - `BASELINE`: no attacker
  - `ATTACK`: co-resident CPU contention
- Labels: `BASELINE` vs `ATTACK`

**Outcome:**
- Tests whether ordering disruption reveals attacker presence
- Establishes the existence of an **ordinal distinguisher** (rank-only)

Typical outputs (example filenames):
```text
out/csv/stage1/threadripper/first run_ripper/
  run1_dataset.csv
  run2_dataset.csv
  run3_dataset.csv
  run4_dataset.csv
  run5_dataset.csv
  run6_negctrl_vs_base.csv
```

---

### Stage 2 — victim secret leakage (CPU vs MEM)

**Question:** Does a victim-internal secret become inferable from rank-only completion order – and is it **amplified** by an attacker?

**Secret definition:**
- `CPU_*`: CPU-bound work
- `MEM_*`: memory-bound work (deterministic, cache/TLB-unfriendly access)

**Comparisons:**
- **Baseline secret leakage**: `CPU_BASE` vs `MEM_BASE`
- **Attack-amplified secret leakage**: `CPU_ATT` vs `MEM_ATT`

Typical outputs:
```text
out/csv/stage2/threadripper/
  secret_tr_base.csv
  secret_tr_att.csv
  negctrl_stage2.csv
```

---

### Stage 3 — defense evaluation (BOS scrubber)

**Question:** Can we mitigate order-based leakage by scrambling the completion order?

**Defense mechanism:** Budgeted Order Scrubbing (BOS v1)
- Buffer `W` completion IDs before releasing
- Flush in keyed pseudorandom permutation (seeded PRNG)
- Seed is server-side secret; `W` may be observable

**Sweep:** Vary `W ∈ {0, 4, 8, 12, 14, 16}` and measure AUC on Stage 2 ATT scenario.

**Key finding:** Leakage decreases with larger `W`, reaching near-chance at `W ≥ 14`.

Typical outputs:
```text
out/csv/stage3/
  stage2_att_W0_r100.csv
  stage2_att_W4_r100.csv
  stage2_att_W8_r100.csv
  stage2_att_W12_r100.csv
  stage2_att_W14_r100.csv
  stage2_att_W16_r100.csv
```

---

## Metrics

All analyses use **rank-only** observables:
- **ODS (Order Disruption Score)**: deviation from FIFO completion order
- **GAP_VAR**: variance of completion gaps
- **AUC / Balanced Accuracy**: classification performance
- **Bootstrap 95% CI**: uncertainty via resampling (default B=5000)

---

## Quickstart (high-level)

1) Start victim (CPU or MEM mode) on pinned cores  
2) Run datasets with `scripts/run_dataset.py`  
3) Analyze with `scripts/analyze.py` and CIs via `scripts/bootstrap_ci.py`

Full command inventory: **`Command.md`**.

---

## Status

- Stage 1 complete (presence leakage)
- Stage 2 complete (secret leakage, attacker-amplified)
- Stage 3 complete (BOS scrubber defense evaluation)

---

# Intel i9-7900X notes

The Threadripper runs are the **reference layout**. Intel runs follow the same stages and analysis scripts, but are stored under:

- Stage 1 datasets: `out/csv/stage1/intel_i9_7900x/runset1/`
- Stage 2 datasets: `out/csv/stage2/i9_7900x/`

## Hardware snapshot (Intel)

- CPU: Intel Core i9-7900X (10C/20T)
- Example topology seen via `lscpu -e`:
  - Core 0: CPUs `0` and `10` (hyperthread siblings)
  - Core 1: CPUs `1` and `11`
- For our "two-core victim" setup we pin to `0,1` (two physical cores).
- For off-core negative controls we pin the attacker away from those: `2-19`.

## Current Intel datasets

### Stage 1 — attacker presence

- `out/csv/stage1/intel_i9_7900x/runset1/run1_dataset.csv`
- `out/csv/stage1/intel_i9_7900x/runset1/run2_dataset.csv`
- `out/csv/stage1/intel_i9_7900x/runset1/run3_dataset.csv`
- `out/csv/stage1/intel_i9_7900x/runset1/run4_dataset.csv`
- `out/csv/stage1/intel_i9_7900x/runset1/run5_dataset.csv`
- `out/csv/stage1/intel_i9_7900x/runset1/run6_negctrl_vs_base.csv` (off-core negative control)

Stage 1 headline result on Intel: attacker presence is **very strongly** distinguishable (AUC roughly **0.96–0.99** across run1–run5); the off-core negative control drops close to chance.

### Stage 2 — secret-mode leakage (CPU vs MEM)

- `out/csv/stage2/i9_7900x/secret_intel_stage2_base.csv` (`CPU_BASE` vs `MEM_BASE`)
- `out/csv/stage2/i9_7900x/secret_intel_stage2_att.csv` (`CPU_ATT` vs `MEM_ATT`)
- `out/csv/stage2/i9_7900x/negctrl_intel_stage2.csv` (off-core negative control)

Stage 2 headline result on Intel: baseline leakage is near chance; co-resident attacker amplifies leakage (see `RESULT.md` for full tables + bootstrap CIs).

## Directory tree (current)


```text
out/csv/
├── stage1
│   ├── intel_i9_7900x/runset1/
│   │   └── run{1-6}*.csv
│   └── threadripper/first run_ripper/
│       └── run{1-6}*.csv
├── stage2
│   ├── i9_7900x/
│   │   └── secret_intel_stage2_{base,att}.csv, negctrl_intel_stage2.csv
│   └── threadripper/
│       └── secret_tr_{base,att}.csv, negctrl_stage2.csv
├── stage3
│   └── stage2_att_W{0,4,8,12,14,16}_r100.csv
├── study
│   ├── kdf_stage2_W0_test.csv
│   └── kdf_stage2_W16_test.csv
├── time_BOS
│   └── overhead_pure_summary_*.csv
└── time_e2e
    └── overhead_summary_*.csv
```

## Where to look for commands and numbers

- Commands / step-by-step reproduction: `REPRODUCE.md`
- Script inventory + copy/paste examples: `Command.md`
- Consolidated results tables (AUC + bootstrap CIs): `RESULT.md`


### Case Study — KDF Fingerprinting

**Question:** Does the side channel generalize to real cryptographic workloads?

**Workloads:**
- PBKDF2-HMAC-SHA256 (CPU-bound)
- scrypt (memory-hard)

**Results:**
- W=0: AUC 0.985 (94% accuracy) — strong leakage
- W=16: AUC 0.514 — no signal (BOS works)

Output: `out/csv/study/kdf_stage2_W{0,16}_test.csv`
