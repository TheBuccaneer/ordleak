#!/usr/bin/env python3
"""
Analyze ordleak dataset: compute statistics, AUC, and classifier accuracy.
"""
import argparse
import csv
import sys
from collections import defaultdict

def load_data(path: str) -> tuple[list, list, list]:
    """Load dataset, return (labels, ods_values, gap_var_values)."""
    labels = []
    ods_vals = []
    gap_vals = []
    
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            labels.append(row['label'])
            ods_vals.append(float(row['ods']))
            # gap_var might not exist in old datasets
            gap_vals.append(float(row.get('gap_var', 0)))
    
    return labels, ods_vals, gap_vals

def stats(values: list[float]) -> dict:
    """Compute min, mean, std, max."""
    n = len(values)
    if n == 0:
        return {'min': 0, 'mean': 0, 'std': 0, 'max': 0, 'n': 0}
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / n
    std = variance ** 0.5
    return {
        'min': min(values),
        'mean': mean,
        'std': std,
        'max': max(values),
        'n': n
    }

def cohens_d(group1: list[float], group2: list[float]) -> float:
    """Cohen's d effect size."""
    n1, n2 = len(group1), len(group2)
    if n1 == 0 or n2 == 0:
        return 0.0
    mean1 = sum(group1) / n1
    mean2 = sum(group2) / n2
    var1 = sum((x - mean1) ** 2 for x in group1) / n1
    var2 = sum((x - mean2) ** 2 for x in group2) / n2
    pooled_std = ((var1 + var2) / 2) ** 0.5
    if pooled_std == 0:
        return 0.0
    return (mean2 - mean1) / pooled_std

def auc_roc(labels: list[str], scores: list[float], pos_label: str = "ATTACK") -> float:
    """Compute AUC-ROC."""
    pairs = list(zip(labels, scores))
    pos_scores = [s for l, s in pairs if l == pos_label]
    neg_scores = [s for l, s in pairs if l != pos_label]
    
    if len(pos_scores) == 0 or len(neg_scores) == 0:
        return 0.5
    
    # Mann-Whitney U statistic
    count = 0
    ties = 0
    for p in pos_scores:
        for n in neg_scores:
            if p > n:
                count += 1
            elif p == n:
                ties += 0.5
    
    auc = (count + ties) / (len(pos_scores) * len(neg_scores))
    return auc

def best_threshold_accuracy(labels: list[str], scores: list[float], pos_label: str = "ATTACK") -> tuple[float, float]:
    """Find best threshold and return (accuracy, threshold)."""
    thresholds = sorted(set(scores))
    best_acc = 0.0
    best_thr = 0.0
    
    for thr in thresholds:
        correct = 0
        for label, score in zip(labels, scores):
            pred = pos_label if score >= thr else "BASELINE"
            if pred == label:
                correct += 1
        acc = correct / len(labels)
        if acc > best_acc:
            best_acc = acc
            best_thr = thr
    
    return best_acc, best_thr

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_file", help="Path to dataset.csv")
    args = ap.parse_args()
    
    labels, ods_vals, gap_vals = load_data(args.csv_file)
    
    # Split by label
    baseline_ods = [o for l, o in zip(labels, ods_vals) if l == "BASELINE"]
    attack_ods = [o for l, o in zip(labels, ods_vals) if l == "ATTACK"]
    baseline_gap = [g for l, g in zip(labels, gap_vals) if l == "BASELINE"]
    attack_gap = [g for l, g in zip(labels, gap_vals) if l == "ATTACK"]
    
    print("=" * 60)
    print("DATASET SUMMARY")
    print("=" * 60)
    print(f"Total samples: {len(labels)}")
    print(f"  BASELINE: {len(baseline_ods)}")
    print(f"  ATTACK:   {len(attack_ods)}")
    
    if len(baseline_ods) != len(attack_ods):
        print(f"\n⚠️  WARNING: Unbalanced data! This will bias accuracy.")
    
    print("\n" + "=" * 60)
    print("ODS (Order Disruption Score)")
    print("=" * 60)
    bs = stats(baseline_ods)
    at = stats(attack_ods)
    print(f"BASELINE: mean={bs['mean']:.4f} std={bs['std']:.4f} [min={bs['min']:.4f}, max={bs['max']:.4f}]")
    print(f"ATTACK:   mean={at['mean']:.4f} std={at['std']:.4f} [min={at['min']:.4f}, max={at['max']:.4f}]")
    
    d = cohens_d(baseline_ods, attack_ods)
    auc = auc_roc(labels, ods_vals)
    acc, thr = best_threshold_accuracy(labels, ods_vals)
    
    print(f"\nCohen's d: {d:.3f}", end="")
    if abs(d) < 0.2:
        print(" (negligible)")
    elif abs(d) < 0.5:
        print(" (small)")
    elif abs(d) < 0.8:
        print(" (medium)")
    else:
        print(" (large)")
    
    print(f"AUC-ROC:  {auc:.3f}", end="")
    if auc < 0.55:
        print(" (≈ random guessing)")
    elif auc < 0.7:
        print(" (weak)")
    elif auc < 0.8:
        print(" (acceptable)")
    else:
        print(" (good)")
    
    print(f"Best threshold accuracy: {acc:.1%} (thr={thr:.4f})")
    
    # Gap variance analysis (if available)
    if any(g > 0 for g in gap_vals):
        print("\n" + "=" * 60)
        print("GAP_VAR (Gap Variance)")
        print("=" * 60)
        bs = stats(baseline_gap)
        at = stats(attack_gap)
        print(f"BASELINE: mean={bs['mean']:.4f} std={bs['std']:.4f}")
        print(f"ATTACK:   mean={at['mean']:.4f} std={at['std']:.4f}")
        
        d = cohens_d(baseline_gap, attack_gap)
        auc = auc_roc(labels, gap_vals)
        acc, thr = best_threshold_accuracy(labels, gap_vals)
        
        print(f"\nCohen's d: {d:.3f}")
        print(f"AUC-ROC:  {auc:.3f}")
        print(f"Best threshold accuracy: {acc:.1%}")
    
    print("\n" + "=" * 60)
    print("VERDICT")
    print("=" * 60)
    main_auc = auc_roc(labels, ods_vals)
    if main_auc >= 0.70:
        print("✅ Signal detected! AUC ≥ 0.70 is publishable.")
    elif main_auc >= 0.60:
        print("⚠️  Weak signal. Try: more attacker procs, shorter jobs, core pinning.")
    else:
        print("❌ No signal. AUC ≈ 0.50 means random guessing.")
        print("   Try: --iters 100000, --workers 2, --attack-procs 24")

if __name__ == "__main__":
    main()
