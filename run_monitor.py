#!/usr/bin/env python3
"""run_monitor.py — wrapper com retry para o cron."""
import subprocess, sys, time

for tentativa in range(3):
    r = subprocess.run([sys.executable, 'monitor.py'])
    if r.returncode == 0:
        break
    time.sleep(30)
