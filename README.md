# 📊 Oscilloscopio PLC - Rockwell CompactLogix 5380

Software oscilloscopio per la visualizzazione in tempo reale di dati campionati da un PLC Rockwell CompactLogix 5380.

## 🚀 Avvio Rapido

### 1. Installa le dipendenze

```bash
pip install flask flask-socketio pycomm3
```

### 2. Avvia il server

```bash
python main.py
```

### 3. Apri il browser

Vai su: **http://localhost:5000**

## 📋 Funzionalità

- ✅ **Visualizzazione in tempo reale** di segnali analogici e digitali
- ✅ **Simulatore PLC integrato** per test senza hardware
- ✅ **Interfaccia web moderna** con grafici interattivi
- ✅ **Handshake sincronizzato** tra software e PLC
- ✅ **Frequenza di campionamento** fino a 1 kHz
- ✅ **Buffer circolare** da 1000 campioni

## 🔧 Configurazione

Modifica `config.py` per personalizzare:

```python
# Indirizzo IP del PLC
PLC_CONFIG = {
    'ip_address': '192.168.1.10',
    'slot': 0,
}

# Abilita/disabilita simulatore
SIMULATOR_CONFIG = {
    'enabled': True,  # False per usare il PLC reale
}
```

## 🏗️ Architettura

```
oscilloscope_plc/
├── main.py                 # Entry point
├── config.py               # Configurazione
├── plc_communication.py    # Comunicazione PLC
├── simulator.py            # Simulatore PLC
├── web_server.py           # Server web Flask
├── static/
│   ├── style.css           # Stili CSS
│   └── app.js              # Logica frontend
└── templates/
    └── index.html          # Interfaccia web
```

## 🔌 Connessione al PLC Reale

1. Installa `pycomm3`:
   ```bash
   pip install pycomm3
   ```

2. Modifica `config.py`:
   ```python
   SIMULATOR_CONFIG = {
       'enabled': False,
   }
   ```

3. Configura i tag nel PLC (Studio 5000):

   | Nome Tag | Tipo | Descrizione |
   |----------|------|-------------|
   | `OSCILLOSCOPE.Array_Analogici` | REAL[1000] | Buffer dati analogici |
   | `OSCILLOSCOPE.Array_Digitali` | DINT[1000] | Buffer dati digitali |
   | `OSCILLOSCOPE.Dati_Pronti` | BOOL | Flag dati pronti |
   | `OSCILLOSCOPE.Lettura_Completa` | BOOL | Flag lettura completata |
   | `OSCILLOSCOPE.Indice` | DINT | Indice di campionamento |
   | `OSCILLOSCOPE.Timestamp` | DINT | Timestamp (ms) |
   | `OSCILLOSCOPE.Sample_Count` | DINT | Contatore campioni |

## 📡 Protocollo di Handshake

```
┌─────────────┐                    ┌─────────────┐
│             │  Dati_Pronti=1     │             │
│    PLC      │ ─────────────────> │ Oscilloscopio│
│             │                    │             │
│             │  Lettura_Completa=1│             │
│             │ <───────────────── │             │
└─────────────┘                    └─────────────┘
```

1. Il PLC campiona i dati e li scrive in un buffer
2. Quando il buffer è pieno, imposta `Dati_Pronti = 1`
3. L'oscilloscopio legge i dati e imposta `Lettura_Completa = 1`
4. Il PLC resetta i flag e ricomincia il campionamento

## 🛠️ Sviluppo

### Struttura del progetto

- **Backend**: Python + Flask + WebSocket
- **Frontend**: HTML + CSS + JavaScript + Chart.js
- **Comunicazione**: EtherNet/IP via pycomm3

### Estensioni future

- [ ] Trigger configurabile
- [ ] Esportazione dati (CSV, JSON)
- [ ] Multi-canale
- [ ] Allarmi e soglie
- [ ] Storico dati

## 📄 Licenza

Progetto dimostrativo per scopi educativi.

---

**Buon oscilloscopio!** 📈
