"""
Server web dell'oscilloscopio.

Espone l'interfaccia sulla porta configurata e inoltra i blocchi di
dati al browser tramite WebSocket.
"""
import time

from flask import Flask, jsonify, render_template
from flask_socketio import SocketIO

from config import WEB_CONFIG
from data_acquisition import DataAcquisition

app = Flask(__name__)
app.config['SECRET_KEY'] = 'oscilloscopio-simulatore'

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

acquisition = DataAcquisition()

# Stato esposto all'interfaccia
stato = {
    'acquiring': False,
    'blocks': 0,
    'last_update': None,
}


# ----------------------------------------------------------------------
# API REST
# ----------------------------------------------------------------------

@app.route('/')
def index():
    """Interfaccia web."""
    return render_template('index.html')


@app.route('/api/status')
def api_status():
    """Stato di acquisizione e configurazione."""
    return jsonify({
        'acquiring': stato['acquiring'],
        'blocks': stato['blocks'],
        'last_update': stato['last_update'],
        'acquisition': acquisition.get_status(),
    })


@app.route('/api/start', methods=['POST'])
def api_start():
    """Avvia l'acquisizione."""
    if not stato['acquiring']:
        acquisition.start()
        stato['acquiring'] = True
    return jsonify({'ok': True, 'acquiring': stato['acquiring']})


@app.route('/api/stop', methods=['POST'])
def api_stop():
    """Ferma l'acquisizione."""
    if stato['acquiring']:
        acquisition.stop()
        stato['acquiring'] = False
    return jsonify({'ok': True, 'acquiring': stato['acquiring']})


# ----------------------------------------------------------------------
# WebSocket
# ----------------------------------------------------------------------

@socketio.on('start_acquisition')
def ws_start():
    if not stato['acquiring']:
        acquisition.start()
        stato['acquiring'] = True
    socketio.emit('acquisition_state', {'acquiring': True})


@socketio.on('stop_acquisition')
def ws_stop():
    if stato['acquiring']:
        acquisition.stop()
        stato['acquiring'] = False
    socketio.emit('acquisition_state', {'acquiring': False})


@socketio.on('clear_buffer')
def ws_clear():
    acquisition.clear()
    socketio.emit('buffer_cleared')


# ----------------------------------------------------------------------
# Flusso dati
# ----------------------------------------------------------------------

def on_block(blocco):
    """
    Callback invocata dal thread di acquisizione a ogni blocco ricevuto.

    Invia l'intero buffer al browser, cosi' zoom e pan possono navigare
    anche i campioni precedenti.
    """
    stato['blocks'] = acquisition.blocks_received
    stato['last_update'] = time.time()

    analog, digital = acquisition.get_all_samples()
    socketio.emit('samples', {
        'analog': analog,
        'digital': digital,
        'total': len(analog),
        'blocks': stato['blocks'],
        'sample_rate': acquisition.simulator.sample_rate,
    })


acquisition.on_block = on_block


def run():
    """Avvia il server."""
    print("=" * 62)
    print("  Oscilloscopio con simulatore integrato")
    print("=" * 62)
    print("  Indirizzo: http://localhost:{}".format(WEB_CONFIG['port']))
    print("  Frequenza: {} Hz".format(acquisition.simulator.sample_rate))
    print("  Blocchi da: {} campioni".format(acquisition.simulator.array_size))
    print("  Ctrl+C per arrestare")
    print("-" * 62)

    try:
        socketio.run(
            app,
            host=WEB_CONFIG['host'],
            port=WEB_CONFIG['port'],
            debug=WEB_CONFIG['debug'],
            allow_unsafe_werkzeug=True,
        )
    finally:
        acquisition.disconnect()
        print("\nChiusura completata")
