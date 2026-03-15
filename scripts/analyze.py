#!/usr/bin/env python3
"""
Analyze ordleak dataset: compute statistics, AUC, and classifier accuracy.
Supports flexible label matching via exact match or prefix.
"""
import argparse
import csv
import sys
from collections import defaultdict


def load_data(path: str, label_col: str = "label") -> tuple[list, list, list]:
    """Load dataset, return (labels, ods_values, gap_var_values)."""
    labels = []
    ods_vals = []
    gap_vals = []
    
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            labels.append(row[label_col])
            ods_vals.append(float(row['ods']))
            # gap_var might not exist in old datasets
            gap_vals.append(float(row.get('gap_var', 0)))
    
    return labels, ods_vals, gap_vals


def classify_label(lab: str, pos_label: str, neg_label: str,
                   pos_prefix: str | None, neg_prefix: str | None) -> str | None:
    """
    Map a label to canonical class name, or None if no match.
    Prefix matching takes precedence over exact match.
    Returns the canonical class name (pos_label or neg_label).
    """
    # Prefix matching first
    if pos_prefix and lab.startswith(pos_prefix):
        return "POS"
    if neg_prefix and lab.startswith(neg_prefix):
        return "NEG"
    # Exact match fallback
    if lab == pos_label:
        return "POS"
    if lab == neg_label:
        return "NEG"
    return None


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


def auc_roc(mapped_labels: list[str], scores: list[float], pos_class: str = "POS") -> float:
    """Compute AUC-ROC."""
    pairs = list(zip(mapped_labels, scores))
    pos_scores = [s for l, s in pairs if l == pos_class]
    neg_scores = [s for l, s in pairs if l != pos_class]
    
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


def best_threshold_accuracy(mapped_labels: list[str], scores: list[float], 
                            pos_class: str = "POS") -> tuple[float, float]:
    """Find best threshold and return (accuracy, threshold)."""
    thresholds = sorted(set(scores))
    best_acc = 0.0
    best_thr = 0.0
    neg_class = "NEG"
    
    for thr in thresholds:
        correct = 0
        for label, score in zip(mapped_labels, scores):
            pred = pos_class if score >= thr else neg_class
            if pred == label:
                correct += 1
        acc = correct / len(mapped_labels)
        if acc > best_acc:
            best_acc = acc
            best_thr = thr
    
    return best_acc, best_thr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_file", help="Path to dataset.csv")
    ap.add_argument("--pos-label", default="ATTACK", help="positive class label (default: ATTACK)")
    ap.add_argument("--neg-label", default="BASELINE", help="negative class label (default: BASELINE)")
    ap.add_argument("--pos-prefix", default=None, help="positive class prefix (e.g., CPU_)")
    ap.add_argument("--neg-prefix", default=None, help="negative class prefix (e.g., MEM_)")
    ap.add_argument("--label-col", default="label", help="label column name")
    args = ap.parse_args()
    
    # Determine display names
    pos_name = args.pos_prefix.rstrip("_") if args.pos_prefix else args.pos_label
    neg_name = args.neg_prefix.rstrip("_") if args.neg_prefix else args.neg_label
    
    raw_labels, ods_vals, gap_vals = load_data(args.csv_file, args.label_col)
    
    # Map labels and filter
    mapped_labels = []
    filtered_ods = []
    filtered_gap = []
    seen_labels = set(raw_labels)
    
    for lab, ods, gap in zip(raw_labels, ods_vals, gap_vals):
        mapped = classify_label(lab, args.pos_label, args.neg_label,
                               args.pos_prefix, args.neg_prefix)
        if mapped is not None:
            mapped_labels.append(mapped)
            filtered_ods.append(ods)
            filtered_gap.append(gap)
    
    # Split by mapped class
    neg_ods = [o for l, o in zip(mapped_labels, filtered_ods) if l == "NEG"]
    pos_ods = [o for l, o in zip(mapped_labels, filtered_ods) if l == "POS"]
    neg_gap = [g for l, g in zip(mapped_labels, filtered_gap) if l == "NEG"]
    pos_gap = [g for l, g in zip(mapped_labels, filtered_gap) if l == "POS"]
    
    print("=" * 60)
    print("DATASET SUMMARY")
    print("=" * 60)
    print(f"Total samples: {len(mapped_labels)}")
    print(f"  {neg_name}: {len(neg_ods)}")
    print(f"  {pos_name}: {len(pos_ods)}")
    
    if len(neg_ods) == 0 or len(pos_ods) == 0:
        print(f"\nLabels found in CSV: {sorted(seen_labels)}")
        raise SystemExit(f"ERROR: need both classes")
    
    if len(neg_ods) != len(pos_ods):
        print(f"\n  WARNING: Unbalanced data! This will bias accuracy.")
    
    print("\n" + "=" * 60)
    print("ODS (Order Disruption Score)")
    print("=" * 60)
    ns = stats(neg_ods)
    ps = stats(pos_ods)
    print(f"{neg_name}: mean={ns['mean']:.4f} std={ns['std']:.4f} [min={ns['min']:.4f}, max={ns['max']:.4f}]")
    print(f"{pos_name}: mean={ps['mean']:.4f} std={ps['std']:.4f} [min={ps['min']:.4f}, max={ps['max']:.4f}]")
    
    d = cohens_d(neg_ods, pos_ods)
    auc = auc_roc(mapped_labels, filtered_ods)
    acc, thr = best_threshold_accuracy(mapped_labels, filtered_ods)
    
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
    if any(g > 0 for g in filtered_gap):
        print("\n" + "=" * 60)
        print("GAP_VAR (Gap Variance)")
        print("=" * 60)
        ns = stats(neg_gap)
        ps = stats(pos_gap)
        print(f"{neg_name}: mean={ns['mean']:.4f} std={ns['std']:.4f}")
        print(f"{pos_name}: mean={ps['mean']:.4f} std={ps['std']:.4f}")
        
        d = cohens_d(neg_gap, pos_gap)
        auc = auc_roc(mapped_labels, filtered_gap)
        acc, thr = best_threshold_accuracy(mapped_labels, filtered_gap)
        
        print(f"\nCohen's d: {d:.3f}")
        print(f"AUC-ROC:  {auc:.3f}")
        print(f"Best threshold accuracy: {acc:.1%}")
    
    print("\n" + "=" * 60)
    print("VERDICT")
    print("=" * 60)
    main_auc = auc_roc(mapped_labels, filtered_ods)
    if main_auc >= 0.70:
        print("Signal detected! AUC ≥ 0.70 is publishable.")
    elif main_auc >= 0.60:
        print("Weak signal. Try: more attacker procs, shorter jobs, core pinning.")
    else:
        print("No signal. AUC ≈ 0.50 means random guessing.")
        print("   Try: --iters 100000, --workers 2, --attack-procs 24")


if __name__ == "__main__":
    main()
