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

- `out/csv/stage2/secret_tr_base.csv`
- `out/csv/stage2/secret_tr_att.csv`
- `out/csv/stage2/negctrl_stage2.csv`

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
- MEM mode: `--mode mem --mem-kb 8192` (example “strong” configuration)

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

taskset -c 0,1 python3 scripts/run_dataset.py   --runs 100 --n 20   --label CPU_BASE   --out out/csv/stage2/secret_tr_base.csv
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

taskset -c 0,1 python3 scripts/run_dataset.py   --runs 100 --n 20   --label MEM_BASE   --out out/csv/stage2/secret_tr_base.csv
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

taskset -c 0,1 python3 scripts/run_dataset.py   --runs 100 --n 20   --attack --attack-procs 32 --attack-seconds 5   --label CPU_ATT   --out out/csv/stage2/secret_tr_att.csv
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

taskset -c 0,1 python3 scripts/run_dataset.py   --runs 100 --n 20   --attack --attack-procs 32 --attack-seconds 5   --label MEM_ATT   --out out/csv/stage2/secret_tr_att.csv
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

taskset -c 0,1 python3 scripts/run_dataset.py   --runs 100 --n 20   --label CPU_NEGCTRL_OFFCORE   --out out/csv/stage2/negctrl_stage2.csv
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

taskset -c 0,1 python3 scripts/run_dataset.py   --runs 100 --n 20   --label MEM_NEGCTRL_OFFCORE   --out out/csv/stage2/negctrl_stage2.csv
```

#### (Optional) Analyze + bootstrap CI for Stage 2 negctrl
```bash
cd ~/projects/ordleak
python3 scripts/analyze.py out/csv/stage2/negctrl_stage2.csv --pos-label MEM_NEGCTRL_OFFCORE --neg-label CPU_NEGCTRL_OFFCORE
python3 scripts/bootstrap_ci.py out/csv/stage2/negctrl_stage2.csv --pos-label MEM_NEGCTRL_OFFCORE --neg-label CPU_NEGCTRL_OFFCORE

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
python3 scripts/analyze.py out/csv/stage2/secret_tr_base.csv --pos-label MEM_BASE --neg-label CPU_BASE
python3 scripts/bootstrap_ci.py out/csv/stage2/secret_tr_base.csv --pos-label MEM_BASE --neg-label CPU_BASE

python3 scripts/analyze.py out/csv/stage2/secret_tr_att.csv  --pos-label MEM_ATT  --neg-label CPU_ATT
python3 scripts/bootstrap_ci.py out/csv/stage2/secret_tr_att.csv  --pos-label MEM_ATT  --neg-label CPU_ATT
```
