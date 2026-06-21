"""
Script de lancement local (sans Docker).

Lance l'API (port 8000) et l'interface admin (port 8001) en parallèle.
Arrêt propre avec Ctrl+C.

Usage :
    python start.py
    python start.py --api-port 8000 --admin-port 8001
"""
import subprocess
import sys
import os
import argparse
import signal

parser = argparse.ArgumentParser(description="Lance l'API et l'admin en parallèle")
parser.add_argument("--api-port",   default=os.getenv("API_PORT",   "8000"))
parser.add_argument("--admin-port", default=os.getenv("ADMIN_PORT", "8001"))
args = parser.parse_args()

env = {**os.environ, "API_PORT": str(args.api_port), "ADMIN_PORT": str(args.admin_port)}

procs = [
    subprocess.Popen([sys.executable, "main.py"],       env=env),
    subprocess.Popen([sys.executable, "admin_main.py"], env=env),
]

print(f"  API    : http://localhost:{args.api_port}")
print(f"  Admin  : http://localhost:{args.admin_port}")
print("  Ctrl+C pour arrêter\n")

def _stop(sig, frame):
    print("\nArrêt en cours…")
    for p in procs:
        p.terminate()

signal.signal(signal.SIGINT,  _stop)
signal.signal(signal.SIGTERM, _stop)

for p in procs:
    p.wait()
