"""
Configurazione dell'oscilloscopio con simulatore integrato.
"""
import os

# === Campionamento ===
SAMPLE_CONFIG = {
    'array_size': 1000,          # Campioni per blocco
    'sample_rate_hz': 1000,      # Frequenza di campionamento simulata
    'task_period_ms': 1,         # Periodo task di riferimento
}

# === Generazione segnali simulati ===
SIMULATOR_CONFIG = {
    'noise_level': 0.1,              # Ampiezza del rumore
    'signal_frequency_hz': 50,       # Frequenza della sinusoide analogica
    'digital_frequency_hz': 10,      # Frequenza dell'onda quadra digitale
}

# === Buffer lato PC ===
BUFFER_CONFIG = {
    'max_samples': 100000,       # Campioni accumulati prima di scartare i piu' vecchi
    'poll_interval': 0.001,     # Intervallo di polling del flag dati pronti (s)
}

# === Server web ===
WEB_CONFIG = {
    'host': '0.0.0.0',
    'port': 5000,
    'debug': False,
}
