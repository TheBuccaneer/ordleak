#!/usr/bin/env python3
"""
Attacker: generates CPU contention to disturb victim's completion order.
"""
import argparse
import time
from multiprocessing import Process

def burn_cpu():
    """Infinite CPU burn loop."""
    x = 0
    while True:
        x = (x * 1664525 + 1013904223) & 0xFFFFFFFF
        x ^= (x >> 13)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=16, help="number of burn processes")
    ap.add_argument("--seconds", type=int, default=3, help="duration in seconds")
    args = ap.parse_args()

    procs = []
    for _ in range(args.procs):
        p = Process(target=burn_cpu)
        p.start()
        procs.append(p)

    time.sleep(args.seconds)

    for p in procs:
        p.terminate()
        p.join()

if __name__ == "__main__":
    main()
