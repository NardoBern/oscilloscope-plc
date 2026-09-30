"""
Server Web per l'oscilloscopio PLC
Fornisce un'interfaccia web con grafici in tempo reale via WebSocket.
"""
import json
import time
import threading
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from config import WEB_CONFIG, SAMPLE_CONFIG
from plc_communication import PLCCommunication

app = Flask(__name__)
app.config['SECRET_KEY'] = 'oscilloscope_plc_secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Istanza globale della comunicazione PLC
plc_comm = PLCCommunication()

# Stato dell'oscilloscopio
oscilloscope_state = {
    'running': False,
    'triggered': False,
    'sample_count': 0,
    'last_update': None,
}


@app.route('/')
def index():
    """Pagina principale."""
    return render_template('index.html')


@app.route('/api/status')
def api_status():
    """API per lo stato del sistema."""
    return jsonify({
        'plc': plc_comm.get_status(),
        'oscilloscope': oscilloscope_state,
        'config': {
            'array_size': SAMPLE_CONFIG['array_size'],
            'sample_rate': SAMPLE_CONFIG['sample_rate_hz'],
        }
    })


@app.route('/api/start', methods=['POST'])
def api_start():
    """Avvia l'acquisizione."""
    if not plc_comm.connected:
        plc_comm.connect()
    
    if not oscilloscope_state['running']:
        plc_comm.start_polling()
        oscilloscope_state['running'] = True
    
    return jsonify({'success': True, 'message': 'Acquisizione avviata'})


@app.route('/api/stop', methods=['POST'])
def api_stop():
    """Ferma l'acquisizione."""
    oscilloscope_state['running'] = False
    plc_comm.stop_polling()
    return jsonify({'success': True, 'message': 'Acquisizione fermata'})


@app.route('/api/data')
def api_data():
    """API per l'ultimo blocco di dati."""
    data = plc_comm.get_last_data()
    if data:
        return jsonify(data)
    return jsonify({'error': 'Nessun dato disponibile'}), 404


@socketio.on('connect')
def handle_connect():
    """Gestione connessione WebSocket."""
    print('[WEB] Client connesso')
    emit('status', {'message': 'Connesso al server'})


@socketio.on('disconnect')
def handle_disconnect():
    """Gestione disconnessione WebSocket."""
    print('[WEB] Client disconnesso')


@socketio.on('start_acquisition')
def handle_start_acquisition():
    """Avvia l'acquisizione via WebSocket."""
    if not plc_comm.connected:
        plc_comm.connect()
    
    if not oscilloscope_state['running']:
        plc_comm.start_polling()
        oscilloscope_state['running'] = True
    
    emit('acquisition_started', {'success': True})


@socketio.on('stop_acquisition')
def handle_stop_acquisition():
    """Ferma l'acquisizione via WebSocket."""
    oscilloscope_state['running'] = False
    plc_comm.stop_polling()
    emit('acquisition_stopped', {'success': True})


def broadcast_data(data):
    """
    Invia i dati a tutti i client connessi via WebSocket.
    """
    socketio.emit('new_data', data)


def data_callback(data):
    """
    Callback chiamata quando ci sono nuovi dati dal PLC.
    """
    oscilloscope_state['sample_count'] = data.get('sample_count', 0)
    oscilloscope_state['last_update'] = time.time()
    
    # Invia tutti i dati accumulati via WebSocket
    all_data = plc_comm.get_all_data()
    broadcast_data(all_data)
    
    # Segnala che la lettura è completa
    plc_comm.signal_read_complete()


def run_server():
    """
    Avvia il server web.
    """
    print(f"[WEB] Avvio server su {WEB_CONFIG['host']}:{WEB_CONFIG['port']}")
    socketio.run(
        app,
        host=WEB_CONFIG['host'],
        port=WEB_CONFIG['port'],
        debug=WEB_CONFIG['debug'],
        allow_unsafe_werkzeug=True
    )


# Registra il callback per i nuovi dati
plc_comm.on_data_ready = data_callback

if __name__ == '__main__':
    try:
        run_server()
    except KeyboardInterrupt:
        print("\n[WEB] Arresto server...")
    finally:
        plc_comm.disconnect()
