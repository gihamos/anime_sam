import subprocess
import sys
import os
import argparse
import signal
import time
import urllib.request

parser = argparse.ArgumentParser(description="Lance l'API et l'admin en parallèle")
parser.add_argument("--api-port",   default=os.getenv("API_PORT",   "8000"))
parser.add_argument("--admin-port", default=os.getenv("ADMIN_PORT", "8001"))
args = parser.parse_args()

env = {**os.environ, "API_PORT": str(args.api_port), "ADMIN_PORT": str(args.admin_port)}

# Lance l'API en premier
api_proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", str(args.api_port)],
    env=env
)

# Attend que l'API soit prête
print(f"  En attente de l'API sur le port {args.api_port}...")
for _ in range(30):
    try:
        urllib.request.urlopen(f"http://localhost:{args.api_port}/")
        print(f"  API prête !")
        break
    except Exception:
        time.sleep(2)

# Lance l'admin
admin_proc = subprocess.Popen(
    [sys.executable, "admin_main.py"],
    env=env
)

procs = [api_proc, admin_proc]

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