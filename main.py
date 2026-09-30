"""
Avvio dell'oscilloscopio con simulatore integrato.
"""
import os
import sys

# Permette l'esecuzione come `python main.py` da qualsiasi directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web_server import run  # noqa: E402

if __name__ == '__main__':
    run()
