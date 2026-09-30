"""
Simulatore di un controller PLC con campionamento ciclico.

Riproduce il comportamento di un task periodico che campiona segnali
misto (analogici e digitali) in blocchi di N campioni, e implementa
il protocollo di handshake a doppio buffer con l'oscilloscopio:

  1. Il simulatore scrive i campioni nel buffer di scrittura
  2. Quando il blocco e' pieno, lo copia nel buffer di lettura e
     solleva il flag `dati_pronti`
  3. L'oscilloscopio legge il blocco e segnala `lettura_completa`
  4. Il simulatore riparte da capo

L'oscilloscopio legge quindi sempre da un buffer che il simulatore non
sta modificando: e' il motivo per cui esistono due array anziche uno.
"""
import math
import threading
import time

from config import SAMPLE_CONFIG, SIMULATOR_CONFIG


class PLCSimulator:
    """
    Simula un controller PLC che campiona segnali a frequenza costante.

    Il campionamento e' effettuato da un thread dedicato che rispetta
    il periodo impostato, indipendentemente da cosa fa il main thread.
    """

    def __init__(self):
        self.array_size = SAMPLE_CONFIG['array_size']
        self.sample_rate = SAMPLE_CONFIG['sample_rate_hz']
        self.period = 1.0 / self.sample_rate

        # Buffer di scrittura: il simulatore scrive qui
        self.array_analog_write = [0.0] * self.array_size
        self.array_digital_write = [0] * self.array_size

        # Buffer di lettura: l'oscilloscopio legge qui
        self.array_analog_read = [0.0] * self.array_size
        self.array_digital_read = [0] * self.array_size

        # Stato del handshake
        self.dati_pronti = False
        self.lettura_completa = False
        self.indice_campionamento = 0
        self.sample_count = 0

        # Controllo del ciclo di vita
        self.running = False
        self.thread = None
        self.lock = threading.Lock()

        # Istante di riferimento per il calcolo dei segnali
        self.start_time = 0.0
        self.debug = True

    # ------------------------------------------------------------------
    # Segnali simulati
    # ------------------------------------------------------------------

    def _generate_signals(self, t):
        """
        Genera un campione dei segnali al tempo t (secondi).

        Canale analogico : sinusoide modulata da rumore
        Canale digitale  : onda quadra
        """
        freq_a = SIMULATOR_CONFIG['signal_frequency_hz']
        freq_d = SIMULATOR_CONFIG['digital_frequency_hz']
        rumore = SIMULATOR_CONFIG['noise_level']

        analog = 50.0 + 30.0 * math.sin(2 * math.pi * freq_a * t)

        # Rumore pseudo-casuale derivato dal tempo: evita lo stato
        # globale di random e resta riproducibile.
        analog += rumore * 10.0 * math.sin(2 * math.pi * 997.0 * t)

        digital = 1 if math.sin(2 * math.pi * freq_d * t) > 0 else 0

        return analog, digital

    # ------------------------------------------------------------------
    # Task di campionamento
    # ------------------------------------------------------------------

    def _sample_task(self):
        """
        Thread che campiona alla frequenza impostata.

        Usa perf_counter() come base temporale: e' monotono e non
        soggetto a rettifiche del clock di sistema (a differenza di
        time.time(), che puo' saltare indietro).
        """
        self.start_time = time.perf_counter()
        prossimo = self.start_time

        while self.running:
            with self.lock:
                # Se il blocco precedente non e' stato ancora letto,
                # non si sovrascrive il buffer di lettura.
                if not (self.dati_pronti and self.lettura_completa):
                    t = time.perf_counter() - self.start_time
                    analog, digital = self._generate_signals(t)

                    idx = self.indice_campionamento
                    self.array_analog_write[idx] = analog
                    self.array_digital_write[idx] = digital

                    self.indice_campionamento += 1
                    self.sample_count += 1

                    if self.indice_campionamento >= self.array_size:
                        # Blocco completo: pubblica e metti in attesa
                        self.array_analog_read = self.array_analog_write.copy()
                        self.array_digital_read = self.array_digital_write.copy()
                        self.indice_campionamento = 0
                        self.dati_pronti = True
                        self.lettura_completa = False
                        self._log("Blocco di {} campioni pronto (totale: {})".format(
                            self.array_size, self.sample_count))

            # Rispettta la frequenza di campionamento
            prossimo += self.period
            attesa = prossimo - time.perf_counter()
            if attesa > 0:
                time.sleep(attesa)
            else:
                # Se siamo in ritardo, ripartiamo dall'istante corrente
                # invece di accumulare un ritardo che non si recupera.
                prossimo = time.perf_counter()

    # ------------------------------------------------------------------
    # API pubblica
    # ------------------------------------------------------------------

    def start(self):
        """Avvia il thread di campionamento."""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._sample_task, daemon=True)
        self.thread.start()
        self._log("Avviato a {} Hz, blocchi da {} campioni".format(
            self.sample_rate, self.array_size))

    def stop(self):
        """Ferma il thread di campionamento."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
            self.thread = None
        self._log("Fermato")

    def read_arrays(self):
        """
        Restituisce l'ultimo blocco completo, o None se non e' pronto.

        Non blocca: se l'oscilloscopio arriva troppo tardi, il blocco
        corrente viene saltato e si attende quello successivo.
        """
        with self.lock:
            if not self.dati_pronti:
                return None
            return {
                'analog': self.array_analog_read.copy(),
                'digital': self.array_digital_read.copy(),
                'timestamp': int((time.perf_counter() - self.start_time) * 1000),
                'sample_count': self.sample_count,
            }

    def signal_read_complete(self):
        """
        L'oscilloscopio segnala di aver completato la lettura.

        Sblocca il simulatore, che ricomincia a scrivere un nuovo blocco.
        """
        with self.lock:
            if self.dati_pronti:
                self.lettura_completa = True
                self.dati_pronti = False

    def get_status(self):
        """Stato corrente, usato per diagnostica e API REST."""
        with self.lock:
            return {
                'dati_pronti': self.dati_pronti,
                'lettura_completa': self.lettura_completa,
                'indice_campionamento': self.indice_campionamento,
                'sample_count': self.sample_count,
                'running': self.running,
            }

    def _log(self, message):
        if self.debug:
            print("[SIMULATORE] {}".format(message))
