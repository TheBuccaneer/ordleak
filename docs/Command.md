# ordleak — Command.md (Script Inventory + Example Calls)



## `src/victim.py`

**Description** 
Startet den Victim-Server, der Jobs parallel ausführt und ausschließlich die **rank-only Completion Order** als `DONE <id>` ausgibt.

**Wichtige Outputs / Hinweise:**
- Öffnet einen Unix-Socket (`--sock`), wartet auf `RUN <n>` Requests (über `client_rank_only.py` / `run_dataset.py`).
- Emittiert `DONE <id>` in realer Completion-Reihenfolge.
- Unterstützt **Secret-Modes** via `--mode cpu|mem`; `--mem-kb` steuert Memory-Buffergröße im MEM-Mode.

**Beispiel-Aufrufe:**

CPU-Mode (typisch Stage 1):
```bash
cd ~/projects/ordleak
rm -f out/victim.sock
taskset -c 0,1 python3 -u src/victim.py --sock out/victim_cpu.sock --mode cpu --workers 2 --iters 200000
ln -sf victim_cpu.sock out/victim.sock
```

MEM-Mode (typisch Stage 2):
```bash
cd ~/projects/ordleak
rm -f out/victim.sock
taskset -c 0,1 python3 -u src/victim.py --sock out/victim_mem.sock --mode mem --mem-kb 8192 --workers 2 --iters 200000
ln -sf victim_mem.sock out/victim.sock
```



## `src/client_rank_only.py`

**Description** 
Minimaler Client, der beim Victim `RUN <n>` anfordert und nur die rank-only `DONE <id>` Sequenz ausliest.

**Wichtige Outputs / Hinweise:**
- Dient als “Observer” (kein Timing, nur Reihenfolge).
- Wird typischerweise **indirekt** über `scripts/run_dataset.py` genutzt.

**Beispiel-Aufruf (direkt):**
```bash
cd ~/projects/ordleak
python3 src/client_rank_only.py --sock out/victim.sock --n 20
```

---

## `src/attacker.py`

**Description** 
Erzeugt CPU-Contention (busy loops) mit `--procs` Worker-Prozessen für `--seconds` Sekunden.

**Wichtige Outputs / Hinweise:**
- Wird i.d.R. von `scripts/run_dataset.py` gestartet, wenn `--attack` gesetzt ist.
- Für **Negativkontrolle Off-core** kann man es separat pinnen (z.B. TR: `taskset -c 2-31 ...`).
- Dieses Script schreibt **keine CSV**; es ist reine Last.

**Beispiel-Aufruf (Off-core NegCtrl-Last, separat):**
```bash
cd ~/projects/ordleak
taskset -c 2-31 python3 -u src/attacker.py --procs 32 --seconds 600
```

---

## `scripts/run_dataset.py`

**Description** 
Führt viele Runs aus, sammelt aus rank-only Completion-Orders Features (z.B. **ODS**, **GAP_VAR**) und schreibt/appendet sie in eine CSV.

**Wichtige Outputs / Hinweise:**
- Schreibt eine CSV mit mindestens: `label`, `ods`, `gap_var`, plus ggf. Zusatzspalten (je nach Version).
- Appendet, wenn die Datei existiert (BASELINE dann ATTACK in dieselbe Datei).
- Attack wird **intern** gestartet, wenn `--attack` gesetzt ist (`--attack-procs`, `--attack-seconds`).

**Beispiel-Aufrufe:**

Stage 1: BASELINE vs ATTACK (in eine Datei):
```bash
cd ~/projects/ordleak
taskset -c 0,1 python3 scripts/run_dataset.py --runs 100 --n 20 --label BASELINE --out out/csv/run1_dataset.csv
taskset -c 0,1 python3 scripts/run_dataset.py --runs 100 --n 20 --attack --attack-procs 32 --attack-seconds 5 --label ATTACK --out out/csv/run1_dataset.csv
```

Stage 2 (Secret): CPU_BASE vs MEM_BASE:
```bash
cd ~/projects/ordleak
# Victim im cpu-mode laufen lassen + symlink setzen, dann:
taskset -c 0,1 python3 scripts/run_dataset.py --runs 100 --n 20 --label CPU_BASE --out out/csv/stage2/secret_tr_base.csv

# Victim im mem-mode laufen lassen + symlink umsetzen, dann:
taskset -c 0,1 python3 scripts/run_dataset.py --runs 100 --n 20 --label MEM_BASE --out out/csv/stage2/secret_tr_base.csv
```

---

## `scripts/analyze.py`

**Description** 
Liest eine Dataset-CSV, berechnet pro Feature (ODS/GAP_VAR) **AUC**, **Best-threshold Accuracy** und **Cohen’s d** und druckt einen Summary-Report.

**CI-Beschreibung:**
- `analyze.py` berechnet **keine** Konfidenzintervalle (CI).  
- Für **95% Bootstrap-CIs** nutzt man `scripts/bootstrap_ci.py`.

**Besonderheit (Labels):**
- Standardmäßig erwartet es `BASELINE` und `ATTACK`.
- Für andere Labels nutzt du:
  - `--pos-label <LABEL_POS>`
  - `--neg-label <LABEL_NEG>`

**Beispiel-Aufrufe:**

Standard (Stage 1):
```bash
cd ~/projects/ordleak
python3 scripts/analyze.py out/csv/run1_dataset.csv
```

Negativkontrolle (z.B. `NEGCTRL_OFFCORE` vs `BASELINE`):
```bash
cd ~/projects/ordleak
python3 scripts/analyze.py out/csv/run6_negctrl_vs_base.csv --pos-label NEGCTRL_OFFCORE --neg-label BASELINE
```

Stage 2 Secret:
```bash
cd ~/projects/ordleak
python3 scripts/analyze.py out/csv/stage2/secret_tr_base.csv --pos-label MEM_BASE --neg-label CPU_BASE
python3 scripts/analyze.py out/csv/stage2/secret_tr_att.csv  --pos-label MEM_ATT  --neg-label CPU_ATT
```

---

## `scripts/bootstrap_ci.py`

**Description** 
Bootstrappt **95% Konfidenzintervalle (CI)** für **AUC** und **Balanced Accuracy** aus einer Dataset-CSV.

**CI-Beschreibung (konkret):**
- Verwendet Bootstrap-Resampling über die Samples (default **B=5000**).
- Gibt aus:
  - `AUC mean=... 95% CI [lo, hi]`
  - `BalancedAcc mean=... 95% CI [lo, hi]`

**Labels / Klassen:**
- Standard: `BASELINE` vs `ATTACK`
- Für andere Labels:
  - `--pos-label <LABEL_POS>`
  - `--neg-label <LABEL_NEG>`

**Beispiel-Aufrufe:**

Standard (Stage 1):
```bash
cd ~/projects/ordleak
python3 scripts/bootstrap_ci.py out/csv/run1_dataset.csv
```

Negativkontrolle:
```bash
cd ~/projects/ordleak
python3 scripts/bootstrap_ci.py out/csv/run6_negctrl_vs_base.csv --pos-label NEGCTRL_OFFCORE --neg-label BASELINE
```

Stage 2 Secret:
```bash
cd ~/projects/ordleak
python3 scripts/bootstrap_ci.py out/csv/stage2/secret_tr_base.csv --pos-label MEM_BASE --neg-label CPU_BASE
python3 scripts/bootstrap_ci.py out/csv/stage2/secret_tr_att.csv  --pos-label MEM_ATT  --neg-label CPU_ATT
```
