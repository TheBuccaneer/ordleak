# REPRODUCE.md — ordleak

This file documents **how to reproduce** the datasets currently stored under:

- `out/csv/stage1/threadripper/first run_ripper/`
- `out/csv/stage2/`
- `out/csv/stage3/`

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

### Stage 3 — defense evaluation (BOS scrubber)

- `out/csv/stage3/stage2_att_W0_r100.csv`
- `out/csv/stage3/stage2_att_W4_r100.csv`
- `out/csv/stage3/stage2_att_W8_r100.csv`
- `out/csv/stage3/stage2_att_W12_r100.csv`
- `out/csv/stage3/stage2_att_W14_r100.csv`
- `out/csv/stage3/stage2_att_W16_r100.csv`

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

---

## 4) Stage 1 negative control (off-core attacker)

Goal: show that an attacker running **off-core** (not sharing victim cores) does *not* create a strong signal.

### Terminal 3 — start off-core attacker (separate)
```bash
cd ~/projects/ordleak
taskset -c 2-31 python3 -u src/attacker.py --procs 32 --seconds 999999
```

### Terminal 2 — collect NEGCTRL_OFFCORE and BASELINE into one CSV
```bash
cd ~/projects/ordleak

# With off-core attacker running:
taskset -c 0,1 python3 scripts/run_dataset.py   --runs 100 --n 20   --label NEGCTRL_OFFCORE   --out "out/csv/stage1/threadripper/first run_ripper/run6_negctrl_vs_base.csv"

# Now stop Terminal 3 (attacker), then collect baseline:
taskset -c 0,1 python3 scripts/run_dataset.py   --runs 100 --n 20   --label BASELINE   --out "out/csv/stage1/threadripper/first run_ripper/run6_negctrl_vs_base.csv"
```

---

## 5) Stage 2 reproduction (secret leakage: CPU vs MEM)

Stage 2 uses two victim modes:
- CPU mode: `--mode cpu`
- MEM mode: `--mode mem --mem-kb 8192`

### 5.1 Baseline secret leakage: `CPU_BASE` vs `MEM_BASE` → `secret_tr_base.csv`

See `RESULT.md` for detailed commands. Summary:
1. Start CPU victim, collect `CPU_BASE` (100 runs)
2. Restart as MEM victim, collect `MEM_BASE` (100 runs)

### 5.2 Attack-amplified secret leakage: `CPU_ATT` vs `MEM_ATT` → `secret_tr_att.csv`

1. Start CPU victim, collect `CPU_ATT` with `--attack --attack-procs 32 --attack-seconds 5`
2. Restart as MEM victim, collect `MEM_ATT`

### 5.3 Negative control: `negctrl_stage2.csv`

Off-core attacker pinned to `2-31`, victim on `0,1`.
Labels: `CPU_NEGCTRL_OFFCORE`, `MEM_NEGCTRL_OFFCORE`

---

## 6) Analysis + Bootstrap CI

Stage 1:
```bash
cd ~/projects/ordleak
python3 scripts/analyze.py "out/csv/stage1/threadripper/first run_ripper/run1_dataset.csv"
python3 scripts/bootstrap_ci.py "out/csv/stage1/threadripper/first run_ripper/run1_dataset.csv"
```

Stage 2:
```bash
cd ~/projects/ordleak
python3 scripts/analyze.py out/csv/stage2/threadripper/secret_tr_att.csv --pos-label MEM_ATT --neg-label CPU_ATT
python3 scripts/bootstrap_ci.py out/csv/stage2/threadripper/secret_tr_att.csv --pos-label MEM_ATT --neg-label CPU_ATT
```

---

# 7) Stage 3 — Defense evaluation (BOS Scrubber, Threadripper)

## 7.1 Overview

**Goal:** Show that increasing the scrubber window `W` reduces AUC (leakage).

**Scenario:** Stage 2 ATT (`CPU_ATT` vs `MEM_ATT`) with BOS scrubber enabled.

**Parameters used:**
- Samples: 100 runs per class (200 total per W)
- Pinning: `taskset -c 0,1`
- Attack: `--attack-procs 16 --attack-seconds 5`
- Victim: `--workers 2 --iters 200000 --mem-kb 8192` (for MEM mode)
- Scrubber: `--scrub-window W --scrub-seed 42`

**Window sizes tested:** `W ∈ {0, 4, 8, 12, 14, 16}`

**Output directory:**
```
out/csv/stage3/
```

---

## 7.2 Scrubber sweep commands

For each `W`, the procedure is:

### Example: W=8

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
    --runs 100 --n 20 \
    --attack --attack-procs 16 --attack-seconds 5 \
    --label CPU_ATT \
    --scrub-window 8 --scrub-seed 42 \
    --out out/csv/stage3/stage2_att_W8_r100.csv
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
    --runs 100 --n 20 \
    --attack --attack-procs 16 --attack-seconds 5 \
    --label MEM_ATT \
    --scrub-window 8 --scrub-seed 42 \
    --out out/csv/stage3/stage2_att_W8_r100.csv
```

Repeat for W ∈ {0, 4, 12, 14, 16}.

---

## 7.3 Analysis (Stage 3)

```bash
cd ~/projects/ordleak

# W=0 (baseline)
python3 scripts/analyze.py out/csv/stage3/stage2_att_W0_r100.csv --pos-label MEM_ATT --neg-label CPU_ATT
python3 scripts/bootstrap_ci.py out/csv/stage3/stage2_att_W0_r100.csv --pos-label MEM_ATT --neg-label CPU_ATT

# W=4
python3 scripts/analyze.py out/csv/stage3/stage2_att_W4_r100.csv --pos-label MEM_ATT --neg-label CPU_ATT
python3 scripts/bootstrap_ci.py out/csv/stage3/stage2_att_W4_r100.csv --pos-label MEM_ATT --neg-label CPU_ATT

# W=8
python3 scripts/analyze.py out/csv/stage3/stage2_att_W8_r100.csv --pos-label MEM_ATT --neg-label CPU_ATT
python3 scripts/bootstrap_ci.py out/csv/stage3/stage2_att_W8_r100.csv --pos-label MEM_ATT --neg-label CPU_ATT

# W=12
python3 scripts/analyze.py out/csv/stage3/stage2_att_W12_r100.csv --pos-label MEM_ATT --neg-label CPU_ATT
python3 scripts/bootstrap_ci.py out/csv/stage3/stage2_att_W12_r100.csv --pos-label MEM_ATT --neg-label CPU_ATT

# W=14
python3 scripts/analyze.py out/csv/stage3/stage2_att_W14_r100.csv --pos-label MEM_ATT --neg-label CPU_ATT
python3 scripts/bootstrap_ci.py out/csv/stage3/stage2_att_W14_r100.csv --pos-label MEM_ATT --neg-label CPU_ATT

# W=16
python3 scripts/analyze.py out/csv/stage3/stage2_att_W16_r100.csv --pos-label MEM_ATT --neg-label CPU_ATT
python3 scripts/bootstrap_ci.py out/csv/stage3/stage2_att_W16_r100.csv --pos-label MEM_ATT --neg-label CPU_ATT
```

---

## 7.4 Results summary

| W | ODS AUC | ODS 95% CI | GAP_VAR AUC | Interpretation |
|---:|---:|---|---:|---|
| 0 | **0.821** | [0.759, 0.878] | 0.835 | Strong leakage (baseline) |
| 4 | **0.750** | — | 0.724 | Leakage reduced |
| 8 | **0.773** | [0.700, 0.845] | 0.789 | Non-monotonic: higher than W=4 |
| 12 | **0.677** | [0.601, 0.749] | 0.514 | ODS weak, GAP_VAR ≈ random |
| 14 | **0.501** | [0.420, 0.580] | 0.597 | ODS ≈ random |
| 16 | **0.449** | [0.369, 0.530] | 0.461 | Both ≈ random (leakage eliminated) |

**Key finding:** W ≥ 14 effectively eliminates order-based leakage.

---

# Intel i9-7900X reproduction

See `RESULT.md` for Intel Stage 1 and Stage 2 reproduction commands and results.

**Files:**
- `out/csv/stage1/intel_i9_7900x/runset1/run{1-6}_dataset.csv`
- `out/csv/stage2/i9_7900x/secret_intel_stage2_{base,att}.csv`
- `out/csv/stage2/i9_7900x/negctrl_intel_stage2.csv`

**Pinning:** `taskset -c 0,1` (victim + dataset), `taskset -c 2-19` (off-core attacker)

---

# 8) Case Study: KDF Fingerprinting (PBKDF2 vs. scrypt)

Victim modes `pbkdf2` and `scrypt` use Python's `hashlib`.

## Output files
```
out/csv/study/
├── kdf_stage2_W0_test.csv
└── kdf_stage2_W16_test.csv
```


## W=0 (baseline)

### Terminal 1 — PBKDF2 victim
```bash
cd ~/projects/ordleak
rm -f out/victim.sock victim_pbkdf2.sock
taskset -c 0,1 python3 -u ./src/victim.py \
  --sock victim_pbkdf2.sock --mode pbkdf2 --iters 100000 --workers 2 --scrub-window 0
```

### Terminal 2 — Collect PBKDF2
```bash
cd ~/projects/ordleak
ln -sf ../victim_pbkdf2.sock out/victim.sock
taskset -c 0,1 python3 ./scripts/run_dataset.py \
  --runs 100 --n 50 --label PBKDF2 \
  --out out/csv/study/kdf_stage2_W0_test.csv \
  --scrub-window 0 --scrub-seed 42
```

Stop victim (Ctrl+C).

## W=0 (Attacker)

### Terminal 1 — scrypt victim
```bash
cd ~/projects/ordleak
rm -f out/victim.sock victim_scrypt.sock
taskset -c 0,1 python3 -u ./src/victim.py \
  --sock victim_scrypt.sock --mode scrypt --workers 2 --scrub-window 0
```

### Terminal 2 — Collect scrypt (append)
```bash
cd ~/projects/ordleak
ln -sf ../victim_scrypt.sock out/victim.sock
taskset -c 0,1 python3 ./scripts/run_dataset.py \
  --runs 100 --n 50 --label SCRYPT \
  --attack --attack-procs 16 --attack-seconds 5 \
  --out out/csv/study/kdf_stage2_W0_test.csv \
  --scrub-window 0 --scrub-seed 42
```



## W=16 (with BOS defense - baseline)

### Terminal 1 — PBKDF2 victim (W=16)
```bash
cd ~/projects/ordleak
rm -f out/victim.sock victim_pbkdf2.sock
taskset -c 0,1 python3 -u ./src/victim.py \
  --sock victim_pbkdf2.sock --mode pbkdf2 --iters 100000 --workers 2 --scrub-window 16
```

### Terminal 2 — Collect PBKDF2
```bash
cd ~/projects/ordleak
ln -sf ../victim_pbkdf2.sock out/victim.sock
taskset -c 0,1 python3 ./scripts/run_dataset.py \
  --runs 100 --n 50 --label PBKDF2 \
  --out out/csv/study/kdf_stage2_W16_test.csv \
  --scrub-window 16 --scrub-seed 42
```

Stop victim (Ctrl+C).

### Terminal 1 — scrypt victim (W=16)
```bash
cd ~/projects/ordleak
rm -f out/victim.sock victim_scrypt.sock
taskset -c 0,1 python3 -u ./src/victim.py \
  --sock victim_scrypt.sock --mode scrypt --workers 2 --scrub-window 16
```

### Terminal 2 — Collect scrypt (append)
```bash
cd ~/projects/ordleak
ln -sf ../victim_scrypt.sock out/victim.sock
taskset -c 0,1 python3 ./scripts/run_dataset.py \
  --runs 100 --n 50 --label SCRYPT \
  --attack --attack-procs 16 --attack-seconds 5 \
  --out out/csv/study/kdf_stage2_W16_test.csv \
  --scrub-window 16 --scrub-seed 42
```



## Analyze
```bash
# W=0
python3 ./scripts/analyze.py out/csv/study/kdf_stage2_W0_test.csv --pos-label SCRYPT --neg-label PBKDF2
python3 ./scripts/bootstrap_ci.py out/csv/study/kdf_stage2_W0_test.csv --pos-label SCRYPT --neg-label PBKDF2

# W=16
python3 ./scripts/analyze.py out/csv/study/kdf_stage2_W16_test.csv --pos-label SCRYPT --neg-label PBKDF2
python3 ./scripts/bootstrap_ci.py out/csv/study/kdf_stage2_W16_test.csv --pos-label SCRYPT --neg-label PBKDF2
```

**Note:** AUC is direction-sensitive. 
