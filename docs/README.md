# ordleak

**ordleak** studies whether **rank-only completion order** in an asynchronous host–service protocol leaks information under **co-resident CPU contention** — and how such leakage can be mitigated.

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
  victim.py              # service / victim workload (cpu|mem modes)
  client_rank_only.py    # observer client (rank-only)
  attacker.py            # CPU contention generator

scripts/
  run_dataset.py         # experiment runner (produces CSVs)
  analyze.py             # computes ODS, GAP_VAR, AUC, Cohen's d
  bootstrap_ci.py        # bootstrap CIs for AUC & balanced accuracy

out/csv/
  stage1/                # Stage 1 datasets (presence leakage)
  stage2/                # Stage 2 datasets (secret leakage)
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

**Question:** Does a victim-internal secret become inferable from rank-only completion order — and is it **amplified** by an attacker?

**Secret definition:**
- `CPU_*`: CPU-bound work
- `MEM_*`: memory-bound work (deterministic, cache/TLB-unfriendly access)

**Comparisons:**
- **Baseline secret leakage**: `CPU_BASE` vs `MEM_BASE`
- **Attack-amplified secret leakage**: `CPU_ATT` vs `MEM_ATT`

Typical outputs:
```text
out/csv/stage2/
  secret_tr_base.csv
  secret_tr_att.csv
  negctrl_stage2.csv
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
- Next (planned): mitigation / scrubber stage



# ordleak

**ordleak** studies whether **rank-only completion order** in an asynchronous host–service protocol leaks information under **co-resident CPU contention** — and how such leakage can be mitigated.

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
  victim.py              # service / victim workload (cpu|mem modes)
  client_rank_only.py    # observer client (rank-only)
  attacker.py            # CPU contention generator

scripts/
  run_dataset.py         # experiment runner (produces CSVs)
  analyze.py             # computes ODS, GAP_VAR, AUC, Cohen's d
  bootstrap_ci.py        # bootstrap CIs for AUC & balanced accuracy

out/csv/
  stage1/                # Stage 1 datasets (presence leakage)
  stage2/                # Stage 2 datasets (secret leakage)
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

out/csv/stage1/intel_i9_7900x/runset1/
  run1_dataset.csv
  run2_dataset.csv
  run3_dataset.csv
  run4_dataset.csv
  run5_dataset.csv
  run6_negctrl_vs_base.csv
```

---

### Stage 2 — victim secret leakage (CPU vs MEM)

**Question:** Does a victim-internal secret become inferable from rank-only completion order — and is it **amplified** by an attacker?

**Secret definition:**
- `CPU_*`: CPU-bound work
- `MEM_*`: memory-bound work (deterministic, cache/TLB-unfriendly access)

**Comparisons:**
- **Baseline secret leakage**: `CPU_BASE` vs `MEM_BASE`
- **Attack-amplified secret leakage**: `CPU_ATT` vs `MEM_ATT`

Typical outputs:
```text
out/csv/stage2/
  secret_tr_base.csv
  secret_tr_att.csv
  negctrl_stage2.csv
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
- Next (planned): mitigation / scrubber stage
