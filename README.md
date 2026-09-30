# Oscilloscopio con simulatore integrato

Interfaccia web per visualizzare, in tempo reale, segnali campionati ciclicamente.
Il campionamento è prodotto da un simulatore che riproduce il comportamento di un
task periodico di un controller PLC, completo di protocollo di handshake.

## Avvio

```bash
pip install -r requirements.txt
python main.py
```

Poi apri **http://localhost:5000**

## Cosa fa

Il simulatore genera due segnali a frequenza costante e li campiona in blocchi:

- **Canale analogico** — sinusoide con rumore sovrapposto
- **Canale digitale** — onda quadra

Ogni volta che un blocco si riempie, viene congelato in un buffer separato e
l'acquisizione si mette in pausa finché il client non conferma la lettura.
Questo garantisce che chi legge non trovi mai dati che cambiano sotto i piedi.

I campioni si accumulano in un buffer circolare fino a 100.000 valori, così è
possibile tornare indietro e rivedere la parte di segnale già trascorsa.

## Comandi

| Pulsante | Effetto |
|----------|---------|
| **Avvia / Ferma** | Avvia o sospende il campionamento |
| **Svuota buffer** | Cancella i campioni accumulati |
| **+ / − / Reset** | Zoom avanti, indietro, vista completa |
| **← / →** | Scorrimento orizzontale |
| **Zoom / Pan / Finestra** | Modalità di interazione col mouse |

Con la rotella si zooma sempre. Trascinando si effettua il pan, oppure si
trascina un rettangolo di selezione, a seconda della modalità attiva.

I due grafici sono sincronizzati: la vista di uno segue quella dell'altro.

## Configurazione

Tutti i parametri sono in `config.py`:

```python
SAMPLE_CONFIG = {
    'array_size': 1000,        # campioni per blocco
    'sample_rate_hz': 1000,    # frequenza di campionamento
}

SIMULATOR_CONFIG = {
    'noise_level': 0.1,              # ampiezza del rumore
    'signal_frequency_hz': 50,       # frequenza della sinusoide
    'digital_frequency_hz': 10,      # frequenza dell'onda quadra
}

BUFFER_CONFIG = {
    'max_samples': 100000,     # capacità del buffer circolare
    'poll_interval': 0.001,    # intervallo di controllo del buffer
}
```

## Struttura del progetto

```
.
├── main.py                 Avvio
├── config.py               Parametri centralizzati
├── simulator.py            Generazione segnali e task di campionamento
├── data_acquisition.py     Polling, handshake e buffer circolare
├── web_server.py           Server Flask e WebSocket
├── static/
│   ├── app.js              Grafici e controlli
│   └── style.css           Stile
└── templates/
    └── index.html          Interfaccia
```

## Note sul simulatore

Il task di campionamento usa `time.perf_counter()` come base temporale anziché
`time.time()`: è monotono e immune alle rettifiche dell'ora di sistema, che
farebbero saltare indietro le etichette temporali.

Il rumore è generato da una funzione sinusoidale ad alta frequenza invece che
dallo stato globale di `random`. Serve a evitare che il simulato si comporti in
modo diverso a ogni esecuzione, così i confronti fra due sessioni sono riproducibili.

## Note sul progetto originale

Questo progetto è nato per visualizzare dati da un PLC Rockwell. La parte di
comunicazione con il controller non è inclusa: il controller scelto per i test
era una ControlLogix L306, con 2,5 MB di memoria totali, e l'allocazione degli
array di campionamento lo avrebbe portato a saturazione. Su un controller con
memoria adeguata l'approccio resterebbe valido e l'interfaccia non cambierebbe.

## Licenza

MIT
