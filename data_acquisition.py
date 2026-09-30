"""
Acquisizione dati: legge i blocchi prodotti dal simulatore e li accumula.

Espone due cose:
  - un flusso incrementale (callback) per l'aggiornamento del grafico
  - un buffer circolare con tutti i campioni acquisiti, che il client
    puo' interrogare per lo zoom e il pan

Il buffer circolare e' thread-safe: viene scritto dal thread di polling
e letto dal thread del server web.
"""
import threading
import time

from config import BUFFER_CONFIG
from simulator import PLCSimulator


class DataAcquisition:
    """Legge i blocchi dal simulatore e li accumula in un buffer circolare."""

    def __init__(self):
        self.simulator = PLCSimulator()
        self.running = False
        self.connected = False
        self._thread = None
        self._stop_event = threading.Event()

        self._lock = threading.Lock()
        self._buffer = []              # (analog, digital) per ogni campione
        self._max_samples = BUFFER_CONFIG['max_samples']
        self._poll_interval = BUFFER_CONFIG['poll_interval']

        self.on_block = None           # callback(chunk) ad ogni blocco
        self.blocks_received = 0

    # ------------------------------------------------------------------
    # Connessione
    # ------------------------------------------------------------------

    def connect(self):
        """Avvia il simulatore."""
        if self.connected:
            return
        self.simulator.start()
        self.connected = True

    def disconnect(self):
        """Ferma l'acquisizione e il simulatore."""
        self.stop()
        self.simulator.stop()
        self.connected = False

    # ------------------------------------------------------------------
    # Acquisizione
    # ------------------------------------------------------------------

    def start(self):
        """Avvia il thread di polling."""
        if self.running:
            return
        if not self.connected:
            self.connect()

        self._stop_event.clear()
        self.running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        print("[ACQUISIZIONE] Polling avviato")

    def stop(self):
        """Ferma il thread di polling, se attivo."""
        if not self.running:
            return
        self.running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        print("[ACQUISIZIONE] Polling fermato")

    def _poll_loop(self):
        """Controlla continuamente se il simulatore ha un blocco pronto."""
        while not self._stop_event.is_set():
            blocco = self.simulator.read_arrays()
            if blocco is not None:
                self._append_block(blocco)
                self.blocks_received += 1

                # Notifica il client che puo' liberare il blocco
                self.simulator.signal_read_complete()

                if self.on_block:
                    try:
                        self.on_block(blocco)
                    except Exception as exc:
                        # Un errore nel client non deve fermare
                        # l'acquisizione: si logga e si prosegue.
                        print("[ACQUISIZIONE] Errore nel callback: {}".format(exc))

            self._stop_event.wait(self._poll_interval)

    def _append_block(self, blocco):
        """Aggiunge un blocco al buffer circolare, scartando i vecchi."""
        analog = blocco['analog']
        digital = blocco['digital']

        with self._lock:
            self._buffer.extend(zip(analog, digital))

            eccedenti = len(self._buffer) - self._max_samples
            if eccedenti > 0:
                del self._buffer[:eccedenti]

    # ------------------------------------------------------------------
    # Lettura
    # ------------------------------------------------------------------

    def get_all_samples(self):
        """
        Restituisce due liste separate: analogici e digitali.

        Restituisce copie, per non esporre il buffer a chi legge.
        """
        with self._lock:
            if not self._buffer:
                return [], []
            separati = zip(*self._buffer)
            analog, digital = next(separati), next(separati)
            return list(analog), list(digital)

    def get_last_block(self):
        """Ultimo blocco completo ricevuto, o None."""
        with self._lock:
            if not self._buffer:
                return None
            n = self.simulator.array_size
            analog = [a for a, _ in self._buffer[-n:]]
            digital = [d for _, d in self._buffer[-n:]]
            return {
                'analog': analog,
                'digital': digital,
                'sample_count': self.simulator.sample_count,
            }

    def clear(self):
        """Svuota il buffer circolare."""
        with self._lock:
            self._buffer.clear()
        self.blocks_received = 0

    def get_status(self):
        """Stato per diagnostica e API REST."""
        with self._lock:
            campioni = len(self._buffer)
        return {
            'connected': self.connected,
            'running': self.running,
            'samples_buffered': campioni,
            'max_samples': self._max_samples,
            'blocks_received': self.blocks_received,
            'sample_rate_hz': self.simulator.sample_rate,
            'block_size': self.simulator.array_size,
            'simulator': self.simulator.get_status(),
        }
