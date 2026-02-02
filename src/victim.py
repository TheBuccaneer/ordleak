#!/usr/bin/env python3
"""
Victim server for ordleak experiments.

Executes N deterministic jobs in parallel and returns:
    DONE <id>
in real completion order (rank-only observable).

Modes:
  - cpu: compute-heavy loop
  - mem: deterministic cache-unfriendly memory access loop (stride=4096)
  - pbkdf2: PBKDF2-SHA256 (CPU-bound KDF)
  - scrypt: scrypt (memory-hard KDF)

Defense (BOS v1):
  - --scrub-window W: buffer W completions before flushing in keyed-permuted order
  - --scrub-seed SEED: PRNG seed for deterministic shuffle (server-side secret)
  - W=0 (default): no scrubbing (baseline)
  - W=1: scrubber active but no reordering (each ID flushed immediately)
  - W>=2: buffer up to W IDs, flush in pseudorandom order
"""
import argparse
import hashlib
import os
import random
import socket
from multiprocessing import Process, Queue
from pathlib import Path
from typing import Iterator, Optional


# =============================================================================
# BOS (Budgeted Order Scrubbing) v1
# =============================================================================

class BOSScrubber:
    """
    Budgeted Order Scrubbing (BOS) v1.

    Buffers completion IDs and releases them in a keyed pseudorandom order
    to reduce order-based information leakage.

    Threat model:
      - Seed is a server-side secret (not observable by attacker)
      - Window size W may be observable (bursty output)
      - For experimental reproducibility, we use a fixed seed

    PRNG state is continuous (initialized once, not reset per flush),
    so identical ID sets do not always receive identical permutations.
    """

    def __init__(self, window: int, seed: int = 42):
        """
        Initialize the scrubber.

        Args:
            window: buffer size W (flush when buffer reaches this size)
            seed: PRNG seed for deterministic shuffle
        """
        self.window = window
        self.buffer: list[int] = []
        # Continuous PRNG state: initialized once, never reset
        self._rng = random.Random(seed)

    def push(self, jid: int) -> None:
        """Add a completed job ID to the buffer."""
        self.buffer.append(jid)

    def maybe_flush(self) -> Iterator[int]:
        """
        If buffer is full (len >= window), flush in permuted order.
        Yields IDs one by one.
        """
        if len(self.buffer) >= self.window:
            yield from self._flush()

    def final_flush(self) -> Iterator[int]:
        """
        Flush any remaining IDs at end-of-run.
        Called after main loop completes.
        """
        if self.buffer:
            yield from self._flush()

    def _flush(self) -> Iterator[int]:
        """
        Internal: shuffle buffer using continuous PRNG and yield all IDs.
        Clears buffer after yielding.
        """
        # Shuffle in-place using continuous PRNG state
        self._rng.shuffle(self.buffer)
        for jid in self.buffer:
            yield jid
        self.buffer.clear()


# =============================================================================
# Work functions
# =============================================================================

def cpu_work(iters: int) -> int:
    """Deterministic CPU work (no randomness, no timers)."""
    x = 0x12345678
    for _ in range(iters):
        x = (x * 1664525 + 1013904223) & 0xFFFFFFFF
        x ^= (x >> 13)
        x = (x * 2246822519) & 0xFFFFFFFF
    return x


def memory_work(iters: int, buf: bytearray) -> int:
    """Deterministic memory-heavy work (cache/TLB-unfriendly access pattern)."""
    stride = 4096  # page-aligned stride for cache/TLB thrashing
    buf_len = len(buf)
    checksum = 0
    for i in range(iters):
        idx = (i * stride) % buf_len
        buf[idx] ^= 0xFF
        checksum += buf[idx]
    return checksum & 0xFFFFFFFF


def kdf_pbkdf2(iters: int = 100000) -> None:
    """PBKDF2-SHA256 (CPU-bound KDF)."""
    password = b"dummy_password"
    salt = b"dummy_salt_12345"
    hashlib.pbkdf2_hmac("sha256", password, salt, iters)


def kdf_scrypt(n: int = 16384, r: int = 8, p: int = 1, dklen: int = 32) -> None:
    """scrypt (memory-hard KDF)."""
    password = b"dummy_password"
    salt = b"dummy_salt_12345"
    hashlib.scrypt(password, salt=salt, n=n, r=r, p=p, dklen=dklen)


def worker(job_q: Queue, done_q: Queue, iters: int, mode: str, mem_size_kb: int) -> None:
    """Worker process: pull jobs, do work, report completion."""
    buf: Optional[bytearray] = bytearray(mem_size_kb * 1024) if mode == "mem" else None

    while True:
        jid = job_q.get()
        if jid is None:
            return

        if mode == "cpu":
            cpu_work(iters)
        elif mode == "mem":
            assert buf is not None
            memory_work(iters, buf)
        elif mode == "pbkdf2":
            kdf_pbkdf2(iters)
        elif mode == "scrypt":
            kdf_scrypt()

        done_q.put(jid)


# =============================================================================
# Main server
# =============================================================================

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sock", default="out/victim.sock", help="unix socket path")
    ap.add_argument("--workers", type=int, default=2, help="number of worker processes (default: 2)")
    ap.add_argument("--iters", type=int, default=200_000, help="work per job (default: 200000)")
    ap.add_argument("--mode", choices=["cpu", "mem", "pbkdf2", "scrypt"], default="cpu",
                    help="work type: cpu, mem, pbkdf2, or scrypt (default: cpu)")
    ap.add_argument("--mem-kb", type=int, default=256, help="buffer size in KB for mem mode (default: 256)")
    # BOS scrubber flags
    ap.add_argument("--scrub-window", type=int, default=0,
                    help="scrubber window size W (0=off, 1=passthrough, >=2=reorder buffer)")
    ap.add_argument("--scrub-seed", type=int, default=42,
                    help="scrubber PRNG seed (default: 42)")
    args = ap.parse_args()

    sock_path = Path(args.sock)
    sock_path.parent.mkdir(parents=True, exist_ok=True)

    if sock_path.exists():
        sock_path.unlink()

    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(str(sock_path))
    srv.listen(1)
    os.chmod(str(sock_path), 0o777)

    # Scrubber info for logging
    scrub_info = f"scrub_window={args.scrub_window}" if args.scrub_window > 0 else "scrub=off"

    print(
        f"victim listening: {sock_path}  workers={args.workers}  iters={args.iters}  "
        f"mode={args.mode}  mem_kb={args.mem_kb}  {scrub_info}",
        flush=True,
    )

    while True:
        conn, _ = srv.accept()
        try:
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

                procs = [
                    Process(target=worker, args=(job_q, done_q, args.iters, args.mode, args.mem_kb))
                    for _ in range(args.workers)
                ]
                for p in procs:
                    p.start()

                for jid in range(n):
                    job_q.put(jid)

                # Initialize scrubber if enabled (W > 0)
                scrubber: Optional[BOSScrubber] = None
                if args.scrub_window > 0:
                    scrubber = BOSScrubber(window=args.scrub_window, seed=args.scrub_seed)

                # Collect completions in REAL completion order (rank-only observable)
                try:
                    for _rank in range(n):
                        jid = done_q.get()

                        if scrubber:
                            scrubber.push(jid)
                            for out_id in scrubber.maybe_flush():
                                conn.sendall(f"DONE {out_id}\n".encode())
                        else:
                            conn.sendall(f"DONE {jid}\n".encode())

                    # Final flush: emit any remaining buffered IDs
                    if scrubber:
                        for out_id in scrubber.final_flush():
                            conn.sendall(f"DONE {out_id}\n".encode())

                finally:
                    # Clean up workers (always, even on early exit)
                    for _ in procs:
                        job_q.put(None)
                    for p in procs:
                        p.join(timeout=2.0)
                        if p.is_alive():
                            p.terminate()
                            p.join(timeout=1.0)

        except (BrokenPipeError, ConnectionResetError):
            # Client disconnected early; continue serving
            pass

    # unreachable
    # return 0


if __name__ == "__main__":
    raise SystemExit(main())
