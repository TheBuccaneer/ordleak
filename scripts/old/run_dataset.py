#!/usr/bin/env python3
"""
Dataset collection script for ordleak experiments.
Runs multiple trials, logs completion order, computes ODS.
"""
import argparse
import csv
import subprocess
import time
from pathlib import Path

def read_done_ids(path: Path) -> list[int]:
    """Parse DONE <id> lines from log file."""
    ids = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line.startswith("DONE "):
            ids.append(int(line.split()[1]))
    return ids

def inv_count(seq: list[int]) -> int:
    """Count inversions in sequence."""
    inv = 0
    n = len(seq)
    for i in range(n):
        for j in range(i + 1, n):
            if seq[i] > seq[j]:
                inv += 1
    return inv

def ods(seq: list[int]) -> float:
    """Order Disruption Score = normalized inversion count."""
    n = len(seq)
    if n < 2:
        return 0.0
    return inv_count(seq) / (n * (n - 1) / 2)

def compute_gap_variance(seq: list[int]) -> float:
    """Variance of gaps between consecutive job IDs."""
    if len(seq) < 2:
        return 0.0
    gaps = [abs(seq[i+1] - seq[i]) for i in range(len(seq) - 1)]
    mean_gap = sum(gaps) / len(gaps)
    variance = sum((g - mean_gap) ** 2 for g in gaps) / len(gaps)
    return variance

def first_half_disorder(seq: list[int]) -> float:
    """ODS of first half only (more sensitive to early disruption)."""
    half = seq[:len(seq) // 2]
    return ods(half)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--victim-sock", default="out/victim.sock")
    ap.add_argument("--n", type=int, default=20, help="jobs per run (default: 20)")
    ap.add_argument("--runs", type=int, default=100, help="number of runs (default: 100)")
    ap.add_argument("--attack", action="store_true", help="run with attacker")
    ap.add_argument("--attack-procs", type=int, default=16, help="attacker processes (default: 16)")
    ap.add_argument("--attack-seconds", type=int, default=3, help="attacker duration (default: 3)")
    ap.add_argument("--out", default="out/csv/dataset.csv")
    ap.add_argument("--label", default=None)
    args = ap.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not out_path.exists()

    label = args.label or ("ATTACK" if args.attack else "BASELINE")

    with out_path.open("a", newline="") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["run_id", "label", "n", "ods", "gap_var", "first_half_ods"])

        for i in range(args.runs):
            run_id = f"{label.lower()}_{i:03d}"
            done_log = Path(f"out/logs/{run_id}.done.log")
            done_log.parent.mkdir(parents=True, exist_ok=True)

            attacker = None
            if args.attack:
                attacker = subprocess.Popen(
                    ["python3", "src/attacker.py", 
                     "--procs", str(args.attack_procs), 
                     "--seconds", str(args.attack_seconds)],
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.DEVNULL
                )
                time.sleep(0.3)  # let attacker ramp up

            try:
                subprocess.check_call([
                    "python3", "src/client_rank_only.py",
                    "--sock", args.victim_sock,
                    "--n", str(args.n),
                    "--out", str(done_log),
                ], timeout=60)
            except subprocess.TimeoutExpired:
                print(f"TIMEOUT {run_id}", flush=True)
                if attacker:
                    attacker.kill()
                continue

            if attacker is not None:
                try:
                    attacker.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    attacker.kill()

            seq = read_done_ids(done_log)
            if len(seq) != args.n:
                print(f"SKIP {run_id}: got {len(seq)} jobs, expected {args.n}", flush=True)
                continue

            val_ods = ods(seq)
            val_gap = compute_gap_variance(seq)
            val_fhd = first_half_disorder(seq)
            
            w.writerow([run_id, label, args.n, f"{val_ods:.6f}", f"{val_gap:.6f}", f"{val_fhd:.6f}"])
            f.flush()
            print(f"ok {run_id}: ODS={val_ods:.4f} GAP_VAR={val_gap:.4f}", flush=True)

if __name__ == "__main__":
    main()
