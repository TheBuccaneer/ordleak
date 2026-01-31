#!/usr/bin/env python3
"""
Victim server for ordleak experiments.
Executes N CPU-heavy jobs in parallel, returns DONE <id> in real completion order.
"""
import argparse
import os
import socket
import sys
from multiprocessing import Process, Queue
from pathlib import Path

def cpu_work(iters: int) -> int:
    """Deterministic CPU work (no randomness, no timers)."""
    x = 0x12345678
    for _ in range(iters):
        x = (x * 1664525 + 1013904223) & 0xFFFFFFFF
        x ^= (x >> 13)
        x = (x * 2246822519) & 0xFFFFFFFF
    return x

def worker(job_q: Queue, done_q: Queue, iters: int):
    """Worker process: pull jobs, do work, report completion."""
    while True:
        jid = job_q.get()
        if jid is None:
            return
        cpu_work(iters)
        done_q.put(jid)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sock", default="out/victim.sock", help="unix socket path")
    ap.add_argument("--workers", type=int, default=2, help="number of worker processes (default: 2)")
    ap.add_argument("--iters", type=int, default=200_000, help="work per job (default: 200000 = ~20ms)")
    args = ap.parse_args()

    sock_path = Path(args.sock)
    sock_path.parent.mkdir(parents=True, exist_ok=True)

    if sock_path.exists():
        sock_path.unlink()

    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(str(sock_path))
    srv.listen(1)
    os.chmod(str(sock_path), 0o777)

    print(f"victim listening: {sock_path}  workers={args.workers}  iters={args.iters}", flush=True)

    while True:
        conn, _ = srv.accept()
        with conn:
            data = conn.recv(1 << 20)
            if not data:
                continue
            msg = data.decode(errors="replace").strip()
            
            parts = msg.split()
            if len(parts) != 2 or parts[0] != "RUN" or not parts[1].isdigit():
                conn.sendall(b"ERR expected: RUN <N>\n")
                continue

            n = int(parts[1])
            job_q: Queue = Queue()
            done_q: Queue = Queue()

            procs = [Process(target=worker, args=(job_q, done_q, args.iters)) for _ in range(args.workers)]
            for p in procs:
                p.start()

            for jid in range(n):
                job_q.put(jid)

            # Collect completions in REAL completion order
            for rank in range(n):
                jid = done_q.get()
                conn.sendall(f"DONE {jid}\n".encode())

            for _ in procs:
                job_q.put(None)
            for p in procs:
                p.join()

if __name__ == "__main__":
    raise SystemExit(main())
