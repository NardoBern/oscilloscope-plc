"""
Simulatore PLC Rockwell CompactLogix 5380
Genera dati sintetici e gestisce l'handshake come farebbe il PLC reale.
"""
import time
import math
import threading
from config import SAMPLE_CONFIG, SIMULATOR_CONFIG


class PLCSimulator:
    """
    Simula il comportamento di un PLC CompactLogix 5380 con:
    - Campionamento a 1 kHz
    - Double buffering per handshake
    - Generazione di segnali misti (analogici e digitali)
    """
    
    def __init__(self):
        self.array_size = SAMPLE_CONFIG['array_size']
        self.sample_rate = SAMPLE_CONFIG['sample_rate_hz']
        self.period = 1.0 / self.sample_rate
        
        # Buffer di scrittura (il PLC scrive qui)
        self.array_analog_write = [0.0] * self.array_size
        self.array_digital_write = [0] * self.array_size
        
        # Buffer di lettura (l'oscilloscopio legge qui)
        self.array_analog_read = [0.0] * self.array_size
        self.array_digital_read = [0] * self.array_size
        
        # Stato handshake
        self.dati_pronti = False
        self.lettura_completa = False
        self.indice_campionamento = 0
        
        # Controllo
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        
        # Generazione segnali
        self.start_time = time.time()
        self.sample_count = 0
        
        # Debug
        self.debug = True
        
    def _log(self, message):
        """Stampa messaggi di debug."""
        if self.debug:
            print(f"[SIMULATORE] {message}")
    
    def _generate_signals(self, t):
        """
        Genera segnali sintetici misti per test.
        """
        # Segnale analogico: sinusoide + rumore
        analog_value = (
            50.0 + 
            30.0 * math.sin(2 * math.pi * SIMULATOR_CONFIG['signal_frequency_hz'] * t) +
            SIMULATOR_CONFIG['noise_level'] * 10 * (2 * (time.time() % 1) - 1)
        )
        
        # Segnale digitale: onda quadra
        digital_value = 1 if math.sin(2 * math.pi * 10 * t) > 0 else 0
        
        return analog_value, digital_value
    
    def _sample_task(self):
        """
        Task di campionamento che simula il ciclo del PLC.
        """
        self._log("Task di campionamento avviato")
        
        while self.running:
            loop_start = time.time()
            
            with self.lock:
                # Se i dati sono pronti, aspetta che l'oscilloscopio li abbia letti
                if self.dati_pronti:
                    if self.lettura_completa:
                        # L'oscilloscopio ha letto, resetta e ricomincia
                        self._log(f"Lettura completata dopo {self.sample_count} campioni totali")
                        self.dati_pronti = False
                        self.lettura_completa = False
                        self.indice_campionamento = 0
                    else:
                        # Aspetta che l'oscilloscopio legga
                        time.sleep(0.001)
                        continue
                
                # Genera nuovo campione
                t = loop_start - self.start_time
                analog, digital = self._generate_signals(t)
                
                # Scrivi nel buffer di scrittura
                self.array_analog_write[self.indice_campionamento] = analog
                self.array_digital_write[self.indice_campionamento] = digital
                
                self.indice_campionamento += 1
                self.sample_count += 1
                
                # Se l'array è pieno, segnala che i dati sono pronti
                if self.indice_campionamento >= self.array_size:
                    self.indice_campionamento = 0
                    self.dati_pronti = True
                    
                    # Copia nel buffer di lettura
                    self.array_analog_read = self.array_analog_write.copy()
                    self.array_digital_read = self.array_digital_write.copy()
                    
                    self._log(f"Buffer pieno! {self.array_size} campioni pronti (totale: {self.sample_count})")
            
            # Mantieni la frequenza di campionamento
            elapsed = time.time() - loop_start
            sleep_time = self.period - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def start(self):
        """Avvia il simulatore."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._sample_task, daemon=True)
            self.thread.start()
            self._log(f"Avviato a {self.sample_rate} Hz")
    
    def stop(self):
        """Ferma il simulatore."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        self._log("Fermato")
    
    def read_arrays(self):
        """
        Legge gli array dal buffer di lettura (come farebbe l'oscilloscopio).
        """
        with self.lock:
            if not self.dati_pronti:
                return None
            
            return {
                'analog': self.array_analog_read.copy(),
                'digital': self.array_digital_read.copy(),
                'timestamp': int((time.time() - self.start_time) * 1000),
                'sample_count': self.sample_count,
            }
    
    def signal_read_complete(self):
        """
        Segnala al PLC che la lettura è completa (handshake).
        """
        with self.lock:
            self.lettura_completa = True
            self._log("Segnalato: lettura completa")
    
    def get_status(self):
        """Restituisce lo stato corrente del simulatore."""
        with self.lock:
            return {
                'dati_pronti': self.dati_pronti,
                'lettura_completa': self.lettura_completa,
                'indice_campionamento': self.indice_campionamento,
                'sample_count': self.sample_count,
                'running': self.running,
            }
