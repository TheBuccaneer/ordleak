#!/usr/bin/env python3
"""
Client: connects to victim, sends RUN N, logs DONE lines to file.
Rank-only observation: no timestamps, just order.
"""
import argparse
import socket
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sock", default="out/victim.sock", help="victim socket path")
    ap.add_argument("--n", type=int, default=20, help="number of jobs")
    ap.add_argument("--out", default="out/logs/done.log", help="output log file")
    args = ap.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(args.sock)
    sock.sendall(f"RUN {args.n}\n".encode())

    # Read all DONE lines
    buf = b""
    lines = []
    while len(lines) < args.n:
        chunk = sock.recv(4096)
        if not chunk:
            break
        buf += chunk
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            line = line.decode().strip()
            if line.startswith("DONE "):
                lines.append(line)

    sock.close()

    # Write to file (rank-only: just the order of DONE lines)
    with out_path.open("w") as f:
        for line in lines:
            f.write(line + "\n")

if __name__ == "__main__":
    main()
