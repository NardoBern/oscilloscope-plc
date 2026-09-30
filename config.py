"""
Configurazione dell'oscilloscopio PLC
"""
import os

# === Configurazione PLC ===
PLC_CONFIG = {
    'ip_address': os.getenv('PLC_IP', '192.168.1.10'),
    'slot': 0,
    'timeout': 5.0,
}

# === Configurazione Campionamento ===
SAMPLE_CONFIG = {
    'array_size': 1000,
    'sample_rate_hz': 1000,  # 1 kHz
    'task_period_ms': 1,     # Task period del PLC
}

# === Tag PLC ===
# Nomi dei tag nel PLC (da adattare al proprio progetto)
TAG_CONFIG = {
    # Array di dati
    'array_analog': 'OSCILLOSCOPE.Array_Analogici',      # REAL[1000]
    'array_digital': 'OSCILLOSCOPE.Array_Digitali',     # DINT[1000]
    
    # Handshake
    'flag_dati_pronti': 'OSCILLOSCOPE.Dati_Pronti',      # BOOL
    'flag_lettura_completa': 'OSCILLOSCOPE.Lettura_Completa',  # BOOL
    'indice_campionamento': 'OSCILLOSCOPE.Indice',       # DINT
    
    # Metadati
    'timestamp': 'OSCILLOSCOPE.Timestamp',               # DINT (ms)
    'sample_count': 'OSCILLOSCOPE.Sample_Count',         # DINT
}

# === Configurazione Web Server ===
WEB_CONFIG = {
    'host': '0.0.0.0',
    'port': 5000,
    'debug': False,
}

# === Configurazione Simulatore ===
SIMULATOR_CONFIG = {
    'enabled': True,  # Usa simulatore invece di PLC reale
    'noise_level': 0.1,
    'signal_frequency_hz': 50,  # Frequenza del segnale simulato
}
