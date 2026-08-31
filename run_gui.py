#!/usr/bin/env python3
"""Entry point for the TextShot GUI application."""

import sys
import os
import argparse
import traceback

# ── Fix working directory (critical when launched via VBS/shortcut) ──
_HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(_HERE)
sys.path.insert(0, _HERE)

# ── Log everything to file (pythonw has no console) ──────────────────
_LOG = os.path.join(_HERE, "textshot_run.log")
_logfile = open(_LOG, "w", buffering=1, encoding="utf-8")

class _Tee:
    def __init__(self, *streams): self.streams = streams
    def write(self, data):
        for s in self.streams:
            try: s.write(data); s.flush()
            except Exception: pass
    def flush(self):
        for s in self.streams:
            try: s.flush()
            except Exception: pass
    def isatty(self): return False

sys.stdout = _Tee(sys.stdout, _logfile)
sys.stderr = _Tee(sys.stderr, _logfile)

print(f"[TextShot] Lanzando desde: {_HERE}")
print(f"[TextShot] Python: {sys.executable}  v{sys.version}")

try:
    from textshot.gui import main
    parser = argparse.ArgumentParser()
    parser.add_argument("langs", nargs="?", default="eng")
    args = parser.parse_args()
    print(f"[TextShot] Idioma: {args.langs}")
    main(langs=args.langs)
except Exception:
    traceback.print_exc()
    input("Presioná Enter para cerrar...")  # solo si hay consola
