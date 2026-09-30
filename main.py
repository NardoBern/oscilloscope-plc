"""
Entry point principale per l'oscilloscopio PLC
"""
import sys
import os

# Aggiungi la directory corrente al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web_server import run_server, plc_comm


def main():
    """
    Funzione principale.
    """
    print("=" * 60)
    print("  📊 Oscilloscopio PLC - Rockwell CompactLogix 5380")
    print("=" * 60)
    print()
    print("Avvio del server web...")
    print("Apri il browser su: http://localhost:5000")
    print()
    print("Premi Ctrl+C per arrestare il server")
    print("-" * 60)
    
    try:
        run_server()
    except KeyboardInterrupt:
        print("\n\n[MAIN] Arresto in corso...")
    finally:
        plc_comm.disconnect()
        print("[MAIN] Server arrestato")


if __name__ == '__main__':
    main()
