"""
Modulo di comunicazione PLC
Gestisce la connessione al PLC Rockwell CompactLogix 5380 via EtherNet/IP
oppure usa il simulatore integrato.
"""
import time
import threading
from config import PLC_CONFIG, TAG_CONFIG, SIMULATOR_CONFIG
from simulator import PLCSimulator

# Tenta di importare pycomm3, altrimenti usa il simulatore
try:
    from pycomm3 import LogixDriver
    PYCOMM3_AVAILABLE = True
except ImportError:
    PYCOMM3_AVAILABLE = False
    print("[ATTENZIONE] pycomm3 non installato. Usa: pip install pycomm3")


class PLCCommunication:
    """
    Gestisce la comunicazione con il PLC Rockwell.
    Supporta sia connessione reale (pycomm3) che simulatore.
    """
    
    def __init__(self):
        self.plc = None
        self.simulator = None
        self.connected = False
        self.use_simulator = SIMULATOR_CONFIG['enabled'] or not PYCOMM3_AVAILABLE
        
        # Stato handshake
        self.dati_pronti = False
        self.lettura_completa = False
        
        # Thread di polling
        self.polling_thread = None
        self.running = False
        self.poll_interval = 0.001  # 1 ms
        
        # Dati letti
        self.last_data = None
        self.data_lock = threading.Lock()
        
        # Buffer circolare per tutti i dati accumulati
        self.all_data = {
            'analog': [],
            'digital': [],
            'timestamps': [],
            'sample_counts': [],
        }
        self.max_samples = 100000  # Massimo 100k campioni
        
        # Callback per nuovi dati
        self.on_data_ready = None
    
    def connect(self):
        """
        Connette al PLC o avvia il simulatore.
        """
        if self.use_simulator:
            print("[PLC] Avvio simulatore...")
            self.simulator = PLCSimulator()
            self.simulator.start()
            self.connected = True
            print("[PLC] Simulatore avviato con successo")
            return True
        
        # Connessione reale al PLC
        try:
            print(f"[PLC] Connessione a {PLC_CONFIG['ip_address']}...")
            self.plc = LogixDriver(f"{PLC_CONFIG['ip_address']}/{PLC_CONFIG['slot']}")
            self.plc.open()
            self.connected = True
            print("[PLC] Connessione stabilita")
            return True
        except Exception as e:
            print(f"[ERRORE] Connessione PLC fallita: {e}")
            print("[PLC] Passaggio al simulatore...")
            self.use_simulator = True
            return self.connect()
    
    def disconnect(self):
        """Disconnette dal PLC o ferma il simulatore."""
        self.running = False
        if self.polling_thread:
            self.polling_thread.join(timeout=2.0)
        
        if self.simulator:
            self.simulator.stop()
            self.simulator = None
        
        if self.plc:
            try:
                self.plc.close()
            except:
                pass
            self.plc = None
        
        self.connected = False
        print("[PLC] Disconnesso")
    
    def start_polling(self):
        """Avvia il thread di polling per leggere i dati."""
        if not self.connected:
            raise Exception("PLC non connesso")
        
        self.running = True
        self.polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
        self.polling_thread.start()
        print("[PLC] Polling avviato")
    
    def stop_polling(self):
        """Ferma il thread di polling."""
        self.running = False
        if self.polling_thread:
            self.polling_thread.join(timeout=2.0)
            self.polling_thread = None
        print("[PLC] Polling fermato")
    
    def _polling_loop(self):
        """
        Loop di polling che controlla i flag di handshake.
        """
        while self.running:
            try:
                if self.use_simulator:
                    self._poll_simulator()
                else:
                    self._poll_real_plc()
            except Exception as e:
                print(f"[ERRORE] Errore nel polling: {e}")
            
            time.sleep(self.poll_interval)
    
    def _poll_simulator(self):
        """Polling del simulatore."""
        status = self.simulator.get_status()
        
        if status['dati_pronti'] and not self.dati_pronti:
            # Nuovi dati disponibili
            self.dati_pronti = True
            data = self.simulator.read_arrays()
            
            if data is None:
                self.dati_pronti = False
                return
            
            with self.data_lock:
                self.last_data = data
                
                # Aggiungi al buffer circolare
                self.all_data['analog'].extend(data['analog'])
                self.all_data['digital'].extend(data['digital'])
                self.all_data['timestamps'].append(data['timestamp'])
                self.all_data['sample_counts'].append(data['sample_count'])
                
                # Limita la dimensione del buffer
                if len(self.all_data['analog']) > self.max_samples:
                    overflow = len(self.all_data['analog']) - self.max_samples
                    self.all_data['analog'] = self.all_data['analog'][overflow:]
                    self.all_data['digital'] = self.all_data['digital'][overflow:]
                    self.all_data['timestamps'] = self.all_data['timestamps'][overflow:]
                    self.all_data['sample_counts'] = self.all_data['sample_counts'][overflow:]
            
            if self.on_data_ready:
                self.on_data_ready(data)
            
            # Segnala che abbiamo letto i dati
            self.simulator.signal_read_complete()
            self.dati_pronti = False
    
    def _poll_real_plc(self):
        """Polling del PLC reale."""
        try:
            # Leggi il flag di dati pronti
            result = self.plc.read(TAG_CONFIG['flag_dati_pronti'])
            if result.value and not self.dati_pronti:
                self.dati_pronti = True
                
                # Leggi gli array
                analog_result = self.plc.read(TAG_CONFIG['array_analog'])
                digital_result = self.plc.read(TAG_CONFIG['array_digital'])
                timestamp_result = self.plc.read(TAG_CONFIG['timestamp'])
                sample_count_result = self.plc.read(TAG_CONFIG['sample_count'])
                
                data = {
                    'analog': analog_result.value,
                    'digital': digital_result.value,
                    'timestamp': timestamp_result.value,
                    'sample_count': sample_count_result.value,
                }
                
                with self.data_lock:
                    self.last_data = data
                
                if self.on_data_ready:
                    self.on_data_ready(data)
        except Exception as e:
            print(f"[ERRORE] Lettura PLC: {e}")
    
    def signal_read_complete(self):
        """
        Segnala al PLC che la lettura è completa.
        """
        if self.use_simulator:
            self.simulator.signal_read_complete()
        else:
            try:
                self.plc.write(TAG_CONFIG['flag_lettura_completa'], True)
                # Reset del flag dopo un breve tempo
                time.sleep(0.001)
                self.plc.write(TAG_CONFIG['flag_lettura_completa'], False)
            except Exception as e:
                print(f"[ERRORE] Segnalazione lettura: {e}")
        
        self.dati_pronti = False
    
    def get_last_data(self):
        """Restituisce gli ultimi dati letti."""
        with self.data_lock:
            return self.last_data
    
    def get_all_data(self):
        """Restituisce tutti i dati accumulati."""
        with self.data_lock:
            return {
                'analog': self.all_data['analog'].copy(),
                'digital': self.all_data['digital'].copy(),
                'timestamps': self.all_data['timestamps'].copy(),
                'sample_counts': self.all_data['sample_counts'].copy(),
            }
    
    def get_status(self):
        """Restituisce lo stato della comunicazione."""
        status = {
            'connected': self.connected,
            'use_simulator': self.use_simulator,
            'dati_pronti': self.dati_pronti,
        }
        
        if self.simulator:
            status['simulator'] = self.simulator.get_status()
        
        return status
