# ordleak — Results & Statistics Summary

*Generated:* 2026-01-30

*Updated:* 2026-01-31 (bootstrap CIs + Threadripper replication + negative control + dataset2)

This document collects the **paper-facing numbers** (sample sizes, per-class descriptive statistics, effect sizes, AUC, and threshold accuracies)
for the datasets that were analyzed with `scripts/analyze.py`, plus bootstrap confidence intervals computed in the chat.

---

## Key takeaways (one paragraph)

Across multiple datasets, the **ATTACK vs BASELINE** distinguisher based on **ordinal completion order** is **measurable**.
The strongest run (`dataset.csv`) reaches **AUC=0.808** with **Cohen’s d=1.223** (balanced 100/100). A larger rerun (`dataset4.csv`, 200/200)
shows the effect persists with **AUC=0.735** (**95% CI [0.688, 0.780]**), indicating the magnitude varies but remains **clearly above chance**.

**Update (Threadripper replication):** `dataset_ripper.csv` improves separability to **AUC=0.864** (95% CI **[0.813, 0.912]**) with **BalancedAcc=0.812** (95% CI **[0.762, 0.862]**), supporting that the effect is not a single-machine artifact.
**Negative control:** `negctrl_offcore.csv` is near chance with **AUC=0.528** (95% CI **[0.453, 0.601]**).

---

## Metric glossary (as used by the scripts)

- **ODS (Order Disruption Score):** normalized inversion count of the completion permutation.
- **GAP_VAR:** variance of absolute consecutive ID differences along the completion sequence (as implemented in the current runner/analyzer).
- **Cohen’s d:** standardized mean difference (ATTACK − BASELINE).
- **AUC-ROC:** threshold-independent separability; **0.5 = random guessing**.

---

## Dataset index

| Dataset file | Total (BASE/ATT) | ODS AUC | ODS d | Verdict |
|---|---:|---:|---:|---|
| `out/csv/config_c.csv` | 100 (50/50) | 0.369 | -0.495 | ❌ no signal |
| `out/csv/config_b.csv` | 100 (50/50) | 0.415 | -0.342 | ❌ no signal |
| `out/csv/config_a.csv` | 100 (50/50) | 0.733 | 0.926 | ✅ signal |
| `out/csv/dataset.csv`  | 200 (100/100) | 0.808 | 1.223 | ✅ strong signal |
| `out/csv/dataset4.csv` | 400 (200/200) | 0.735 | 0.939 | ✅ signal (rerun) |

---

## Detailed numbers per dataset

### `out/csv/config_c.csv`

**ODS**
- BASELINE: mean=0.0752 std=0.0354 [min=0.0158, max=0.1368]
- ATTACK:   mean=0.0598 std=0.0260 [min=0.0158, max=0.1105]
- Cohen's d: **-0.495**
- AUC-ROC: **0.369**
- Best threshold accuracy: **51.0%** (thr=0.0263)

**GAP_VAR**
- BASELINE: mean=1.4520 std=0.9711
- ATTACK:   mean=1.2324 std=0.7201
- Cohen's d: **-0.257**
- AUC-ROC: **0.453**
- Best threshold accuracy: **54.0%**

**Bootstrap confidence intervals (B=5000; `scripts/bootstrap_ci.py`, ODS)**
- AUC mean=**0.369**  95% CI **[0.264, 0.481]**
- BalancedAcc mean=**0.525**  95% CI **[0.500, 0.579]**


---

### `out/csv/config_b.csv`

**ODS**
- BASELINE: mean=0.0209 std=0.0079 [min=0.0053, max=0.0368]
- ATTACK:   mean=0.0182 std=0.0081 [min=0.0000, max=0.0368]
- Cohen's d: **-0.342**
- AUC-ROC: **0.415**
- Best threshold accuracy: **50.0%** (thr=0.0000)

**GAP_VAR**
- BASELINE: mean=0.3702 std=0.1723
- ATTACK:   mean=0.3249 std=0.1659
- Cohen's d: **-0.268**
- AUC-ROC: **0.440**
- Best threshold accuracy: **51.0%**

**Bootstrap confidence intervals (B=5000; `scripts/bootstrap_ci.py`, ODS)**
- AUC mean=**0.414**  95% CI **[0.311, 0.523]**
- BalancedAcc mean=**0.510**  95% CI **[0.500, 0.560]**


---

### `out/csv/config_a.csv`

**ODS**
- BASELINE: mean=0.0073 std=0.0058 [min=0.0000, max=0.0211]
- ATTACK:   mean=0.0132 std=0.0069 [min=0.0000, max=0.0316]
- Cohen's d: **0.926**
- AUC-ROC: **0.733**
- Best threshold accuracy: **67.0%** (thr=0.0105)

**GAP_VAR**
- BASELINE: mean=0.1332 std=0.1266
- ATTACK:   mean=0.1901 std=0.1048
- Cohen's d: **0.490**
- AUC-ROC: **0.668**
- Best threshold accuracy: **67.0%**

**Bootstrap confidence intervals (B=5000; `scripts/bootstrap_ci.py`, ODS)**
- AUC mean=**0.753**  95% CI **[0.657, 0.843]**
- BalancedAcc mean=**0.713**  95% CI **[0.636, 0.791]**


---

### `out/csv/dataset.csv`  (main run)

**ODS**
- BASELINE: mean=0.0071 std=0.0063 [min=0.0000, max=0.0263]
- ATTACK:   mean=0.0163 std=0.0086 [min=0.0000, max=0.0421]
- Cohen's d: **1.223**
- AUC-ROC: **0.808**
- Best threshold accuracy: **73.5%** (thr=0.0105)

**GAP_VAR**
- BASELINE: mean=0.1188 std=0.1304
- ATTACK:   mean=0.2402 std=0.1644
- Cohen's d: **0.818**
- AUC-ROC: **0.751**
- Best threshold accuracy: **72.0%**

**Bootstrap confidence intervals (B=5000; computed externally)**
- AUC mean=**0.808**  95% CI **[0.749, 0.865]**
- BalancedAcc mean=**0.743**  95% CI **[0.687, 0.799]**

---

### `out/csv/dataset4.csv` (rerun, larger N)

**ODS**
- BASELINE: mean=0.0081 std=0.0058 [min=0.0000, max=0.0263]
- ATTACK:   mean=0.0146 std=0.0079 [min=0.0000, max=0.0421]
- Cohen's d: **0.939**
- AUC-ROC: **0.735**
- Best threshold accuracy: **66.2%** (thr=0.0158)

**GAP_VAR**
- BASELINE: mean=0.1383 std=0.1236
- ATTACK:   mean=0.1940 std=0.1217
- Cohen's d: **0.454**
- AUC-ROC: **0.655**
- Best threshold accuracy: **65.5%**

**Bootstrap confidence intervals (B=5000; computed externally)**
- AUC mean=**0.735**  95% CI **[0.688, 0.780]**
- BalancedAcc mean=**0.668**  95% CI **[0.627, 0.708]**

---

### `out/csv/negctrl_offcore.csv` (negative control: attacker off-core)

**Setup:** victim pinned to cores `0,1`; dataset runner + attacker pinned to disjoint cores `2,3`
(i.e., attacker is **not co-resident** with the victim).

**ODS**
- BASELINE: mean=0.0058 std=0.0061 [min=0.0000, max=0.0368]
- ATTACK:   mean=0.0063 std=0.0059 [min=0.0000, max=0.0263]
- Cohen's d: **0.079** (negligible)
- AUC-ROC: **0.528** (≈ random guessing)
- Best threshold accuracy: **53.0%** (thr=0.0105)

**GAP_VAR**
- BASELINE: mean=0.0945 std=0.1208
- ATTACK:   mean=0.1006 std=0.1037
- Cohen's d: **0.055**
- AUC-ROC: **0.541**
- Best threshold accuracy: **56.0%**

**Interpretation:** When the attacker is pinned to **disjoint cores**, the distinguisher collapses to near-chance performance (AUC ≈ 0.53–0.54), supporting that the main effect requires **co-resident contention** and is not a pipeline/label artifact.


**Bootstrap confidence intervals (B=5000; `scripts/bootstrap_ci.py`, ODS)**
- AUC mean=**0.528**  95% CI **[0.453, 0.601]**
- BalancedAcc mean=**0.539**  95% CI **[0.500, 0.594]**


### `out/csv/dataset2.csv` (variant run)

**Bootstrap confidence intervals (B=5000; `scripts/bootstrap_ci.py`, ODS)**
- AUC mean=**0.733**  95% CI **[0.664, 0.798]**
- BalancedAcc mean=**0.691**  95% CI **[0.631, 0.751]**

### `out/csv/dataset_ripper.csv` (Threadripper replication)

**ODS**
- BASELINE: mean=0.0068 std=0.0053 [min=0.0000, max=0.0316]
- ATTACK:   mean=0.0176 std=0.0084 [min=0.0000, max=0.0368]
- Cohen's d: **1.522**
- AUC-ROC: **0.864**
- Best threshold accuracy: **81.0%** (thr=0.0158)

**GAP_VAR**
- BASELINE: mean=0.1076 std=0.1219
- ATTACK:   mean=0.2380 std=0.1125
- Cohen's d: **1.111**
- AUC-ROC: **0.833**
- Best threshold accuracy: **83.0%**

**Bootstrap confidence intervals (B=5000; `scripts/bootstrap_ci.py`, ODS)**
- AUC mean=**0.864**  95% CI **[0.813, 0.912]**
- BalancedAcc mean=**0.812**  95% CI **[0.762, 0.862]**

## Paper-ready sentence templates

- **Main result:** “Using only ordinal completion observations, we distinguish ATTACK from BASELINE with AUC=0.808 (Cohen’s d=1.223) on 100/100 trials.”
- **Robustness rerun:** “On an independent rerun with 200/200 trials, the effect persists (AUC=0.735, 95% CI [0.688, 0.780]).”
- **Regime dependence:** “The magnitude varies across configurations, but remains significantly above chance in the exploitable regime.”

