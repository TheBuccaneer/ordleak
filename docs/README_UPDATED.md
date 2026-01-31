# ordleak

**ordleak** is a minimal experiment harness for studying *scheduler-induced leakage* via **completion order** only.
The observer sees **only ranks / order** (`DONE <id>` sequence). No timestamps, no fine‑grained timers.

## Threat model (frozen)
- **Victim** runs a batch of `N` jobs and reports completions (`DONE <id>`) in *real completion order*.
- **Observer** can request a run and sees only the **ordinal** completion sequence.
- **Attacker** is unprivileged user-space code that creates CPU contention.
- The goal is **distinguishability** (e.g., AUC / accuracy), not “entropy goes down”.

## Repo layout

```
src/       # executable components (victim / observer / attacker)
scripts/   # dataset runner + analysis
out/       # generated logs + CSVs (created automatically)
```

Generated outputs:

```
out/logs/<run_id>.done.log     # rank-only DONE lines for each run
out/csv/<dataset>.csv          # dataset with per-run metrics
```

## Quickstart (reproduce)

### Terminal 1: start the victim (server)
```bash
cd ~/projects/ordleak
mkdir -p out
rm -f out/victim.sock
taskset -c 0,1 python3 -u src/victim.py --sock out/victim.sock --workers 2 --iters 200000
```

Expected banner:
```
victim listening: out/victim.sock  workers=2  iters=200000
```

### Terminal 2: collect a dataset (baseline + attack)
```bash
cd ~/projects/ordleak
mkdir -p out/csv

taskset -c 0,1 python3 scripts/run_dataset.py \
  --runs 100 --n 20 \
  --label BASELINE \
  --out out/csv/dataset.csv

taskset -c 0,1 python3 scripts/run_dataset.py \
  --runs 100 --n 20 \
  --attack --attack-procs 16 --attack-seconds 3 \
  --label ATTACK \
  --out out/csv/dataset.csv
```

### Analyze
```bash
cd ~/projects/ordleak
python3 scripts/analyze.py out/csv/dataset.csv
```

---

## Bootstrap confidence intervals (paper-facing)
To report uncertainty, compute bootstrap 95% confidence intervals for **AUC** and **balanced accuracy** (default `B=5000`) using `scripts/bootstrap_ci.py`:

```bash
cd ~/projects/ordleak
python3 scripts/bootstrap_ci.py out/csv/dataset.csv
python3 scripts/bootstrap_ci.py out/csv/dataset_ripper.csv
python3 scripts/bootstrap_ci.py out/csv/negctrl_offcore.csv
```

Notes:
- Run from the **repo root** (`~/projects/ordleak`). Otherwise you'll get `can't open file .../scripts/bootstrap_ci.py`.
- If you want to bootstrap a different column (e.g., `gap_var`), pass `--metric-col gap_var`.

---

## Components (`src/`)

### `src/victim.py`
Victim server (Unix domain socket). Receives `RUN <N>` and executes `N` CPU-heavy jobs using a fixed-size worker pool.
It streams back `DONE <id>` lines in **real completion order**.

**Args**
- `--sock PATH` : unix socket path (default: `out/victim.sock`)
- `--workers W` : number of worker processes (default: `2`)
- `--iters I`   : work per job (default: `200000`)

**Protocol**
- Client sends: `RUN N\n`
- Victim replies with exactly `N` lines: `DONE <job_id>\n`

### `src/client_rank_only.py`
Observer client. Connects to the victim socket, sends `RUN N`, and writes the **rank-only** completion order to a log file.

**Args**
- `--sock PATH` : victim socket path (default: `out/victim.sock`)
- `--n N`       : number of jobs (default: `20`)
- `--out PATH`  : output log path (default: `out/logs/done.log`)

**Output format (`*.done.log`)**
One line per completion:
```
DONE 7
DONE 0
DONE 3
...
```

### `src/attacker.py`
Unprivileged attacker that generates CPU contention (spawns `--procs` busy-loop processes for `--seconds`).

**Args**
- `--procs P`    : number of burner processes (default: `16`)
- `--seconds S`  : duration (default: `3`)

---

## Experiment pipeline (`scripts/`)

### `scripts/run_dataset.py`
Collects a dataset of repeated trials. For each run:
1. optionally starts the attacker,
2. runs `src/client_rank_only.py` to collect `DONE` order into `out/logs/<run_id>.done.log`,
3. computes per-run metrics from the completion permutation,
4. appends a row to a CSV dataset.

**Args**
- `--victim-sock PATH` : socket path (default: `out/victim.sock`)
- `--n N`              : jobs per run (default: `20`)
- `--runs R`           : number of runs (default: `100`)
- `--attack`           : enable attacker
- `--attack-procs P`   : attacker processes (default: `16`)
- `--attack-seconds S` : attacker duration (default: `3`)
- `--out PATH`         : dataset CSV output path (default: `out/csv/dataset.csv`)
- `--label NAME`       : label to write into CSV (default: `ATTACK` if `--attack` else `BASELINE`)

**Dataset CSV schema**
Header (written once if the file is new):
- `run_id` : e.g., `baseline_000`, `attack_042`
- `label`  : `BASELINE` or `ATTACK` (or custom)
- `n`      : number of jobs
- `ods`    : Order Disruption Score (normalized inversion count)
- `gap_var` : variance of `abs(seq[i+1] - seq[i])` over the completion sequence
- `first_half_ods` : ODS computed on the first half of the completion list (more sensitive to early disruption)

**Metric definitions**
- **ODS**: normalized inversion count of the completion permutation.
- **gap_var**: currently a simple variance over absolute consecutive ID differences. (It is *not* position-gap variance; if you change the definition later, document it here.)
- **first_half_ods**: ODS on prefix length `n//2`.

### `scripts/analyze.py`
Analyzes a dataset CSV and prints:
- summary counts,
- per-label mean/std/min/max,
- **Cohen’s d**,
- **AUC-ROC** (Mann–Whitney based),
- best-threshold accuracy.

Usage:
```bash
python3 scripts/analyze.py out/csv/dataset.csv
```

---


### `scripts/bootstrap_ci.py`
Computes **bootstrap** 95% confidence intervals for **AUC** and **balanced accuracy** on a dataset CSV (default: `B=5000`).

Usage:
```bash
python3 scripts/bootstrap_ci.py out/csv/dataset.csv
```

## Reproducibility notes
- Use `taskset` to pin both victim and dataset runner (including attacker children) to the same cores:
  - example: `taskset -c 0,1 ...`
- Expect some run-to-run variation; report confidence intervals (e.g., bootstrap CI for AUC) for paper-facing results.
- Negative control: pinning the attacker to disjoint cores (not co-resident with the victim) removes the effect (e.g., `negctrl_offcore.csv`: ODS AUC≈0.53).


## Troubleshooting
- If the victim socket path already exists: `rm -f out/victim.sock`
- If a run prints `SKIP ... got X jobs`: the client did not receive all `DONE` lines (usually victim not running or wrong `--sock`).
