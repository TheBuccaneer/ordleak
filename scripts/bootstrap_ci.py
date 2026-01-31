#!/usr/bin/env python3
"""
Bootstrap CI for ordleak experiments.
Supports flexible label matching via exact match or prefix.
"""
import csv
import random
import statistics as st
import argparse


def auc_mann_whitney(xs, ys):
    """
    AUC via Mann-Whitney U with tie-aware average ranks.
    ys: 1=positive, 0=negative
    """
    n = len(xs)
    order = sorted(range(n), key=lambda i: xs[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j < n and xs[order[j]] == xs[order[i]]:
            j += 1
        avg = (i + 1 + j) / 2.0  # ranks start at 1
        for k in range(i, j):
            ranks[order[k]] = avg
        i = j

    n1 = sum(ys)
    n0 = n - n1
    if n0 == 0 or n1 == 0:
        return float("nan")

    Rpos = sum(r for r, t in zip(ranks, ys) if t == 1)
    U = Rpos - n1 * (n1 + 1) / 2.0
    return U / (n0 * n1)


def best_balanced_acc(xs, ys):
    """
    Best balanced accuracy over thresholds (predict positive if x >= thr).
    BalancedAcc = (TPR + TNR)/2
    """
    vals = sorted(set(xs))
    best = 0.0
    for thr in vals:
        tp = fp = tn = fn = 0
        for v, t in zip(xs, ys):
            pred = 1 if v >= thr else 0
            if pred == 1 and t == 1:
                tp += 1
            elif pred == 1 and t == 0:
                fp += 1
            elif pred == 0 and t == 0:
                tn += 1
            else:
                fn += 1
        tpr = tp / (tp + fn) if (tp + fn) else 0.0
        tnr = tn / (tn + fp) if (tn + fp) else 0.0
        bal = (tpr + tnr) / 2.0
        if bal > best:
            best = bal
    return best


def ci(vals, alpha=0.05):
    vals = sorted(vals)
    lo = vals[int((alpha / 2) * len(vals))]
    hi = vals[int((1 - alpha / 2) * len(vals))]
    return st.mean(vals), lo, hi


def classify_label(lab: str, pos_label: str, neg_label: str, 
                   pos_prefix: str | None, neg_prefix: str | None) -> int | None:
    """
    Classify a label as positive (1), negative (0), or skip (None).
    Prefix matching takes precedence over exact match.
    """
    # Prefix matching first
    if pos_prefix and lab.startswith(pos_prefix):
        return 1
    if neg_prefix and lab.startswith(neg_prefix):
        return 0
    # Exact match fallback
    if lab == pos_label:
        return 1
    if lab == neg_label:
        return 0
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path", help="CSV with columns incl. label + ods")
    ap.add_argument("--pos-label", default="ATTACK", help="positive class label (default: ATTACK)")
    ap.add_argument("--neg-label", default="BASELINE", help="negative class label (default: BASELINE)")
    ap.add_argument("--pos-prefix", default=None, help="positive class prefix (e.g., CPU_)")
    ap.add_argument("--neg-prefix", default=None, help="negative class prefix (e.g., MEM_)")
    ap.add_argument("--label-col", default="label", help="label column name")
    ap.add_argument("--metric-col", default="ods", help="metric column name (e.g., ods)")
    ap.add_argument("--B", type=int, default=5000, help="bootstrap resamples")
    ap.add_argument("--seed", type=int, default=0, help="rng seed")
    args = ap.parse_args()

    rows = list(csv.DictReader(open(args.csv_path, newline="")))
    if not rows:
        raise SystemExit("empty CSV")

    # allow common ods column names
    metric_col = args.metric_col
    if metric_col not in rows[0]:
        for k in ("ods", "ODS", "val_ods"):
            if k in rows[0]:
                metric_col = k
                break
    if metric_col not in rows[0]:
        raise SystemExit(f"metric column not found (tried {args.metric_col}, ods/ODS/val_ods)")

    X = []
    y = []
    seen_labels = set()
    
    for r in rows:
        lab = (r.get(args.label_col) or "").strip()
        seen_labels.add(lab)
        
        t = classify_label(lab, args.pos_label, args.neg_label, 
                          args.pos_prefix, args.neg_prefix)
        if t is None:
            continue
            
        try:
            v = float(r[metric_col])
        except Exception:
            continue
        X.append(v)
        y.append(t)

    n = len(X)
    n_pos = sum(y)
    n_neg = n - n_pos
    
    # Determine display names
    pos_name = args.pos_prefix.rstrip("_") if args.pos_prefix else args.pos_label
    neg_name = args.neg_prefix.rstrip("_") if args.neg_prefix else args.neg_label
    
    print(f"Bootstrap (B={args.B}) on {args.csv_path}")
    print(f"N total={n}  {neg_name}={n_neg}  {pos_name}={n_pos}")
    
    if n_pos == 0 or n_neg == 0:
        print(f"\nLabels found in CSV: {sorted(seen_labels)}")
        raise SystemExit(f"ERROR: need both classes. Got {neg_name}={n_neg}, {pos_name}={n_pos}")

    random.seed(args.seed)
    aucs = []
    bals = []
    for _ in range(args.B):
        idx = [random.randrange(n) for _ in range(n)]
        xs = [X[i] for i in idx]
        ys = [y[i] for i in idx]
        if 0 in ys and 1 in ys:
            aucs.append(auc_mann_whitney(xs, ys))
            bals.append(best_balanced_acc(xs, ys))

    m_auc, lo_auc, hi_auc = ci(aucs)
    m_bal, lo_bal, hi_bal = ci(bals)
    print(f"AUC mean={m_auc:.3f}  95% CI [{lo_auc:.3f}, {hi_auc:.3f}]")
    print(f"BalancedAcc mean={m_bal:.3f}  95% CI [{lo_bal:.3f}, {hi_bal:.3f}]")


if __name__ == "__main__":
    main()
