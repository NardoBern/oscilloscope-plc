/**
 * Oscilloscopio web - frontend
 *
 * Riceve l'intero buffer di campioni via WebSocket e lo disegna.
 * I controlli zoom/pan sono sincronizzati tra i due grafici.
 */

// Stato
let analogChart = null;
let digitalChart = null;
let acquiring = false;

document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    initWebSocket();
    refreshStatus();
});

// ---------------------------------------------------------------------
// Grafici
// ---------------------------------------------------------------------

function zoomOptions() {
    return {
        zoom: {
            enabled: true,
            mode: 'x',
            wheel: { enabled: true },
            pinch: { enabled: true },
            drag: false,
        },
        pan: {
            enabled: false,
            mode: 'x',
        },
        limits: {
            // 'original' = usa come estremi quelli della serie dati
            // corrente, cosi' i limiti seguono la dimensione del buffer.
            x: { min: 'original', max: 'original' },
        },
    };
}

function baseOptions(titoloY, extraY = {}) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
            legend: { labels: { color: '#e8e8e8' } },
            tooltip: {
                backgroundColor: 'rgba(10, 10, 20, 0.95)',
                borderColor: '#00d4ff',
                borderWidth: 1,
            },
            zoom: zoomOptions(),
        },
        scales: {
            x: {
                type: 'linear',
                title: { display: true, text: 'Campioni', color: '#8b8b9e' },
                ticks: { color: '#8b8b9e', maxTicksLimit: 12 },
                grid: { color: 'rgba(255,255,255,0.07)' },
            },
            y: {
                title: { display: true, text: titoloY, color: '#8b8b9e' },
                ticks: { color: '#8b8b9e' },
                grid: { color: 'rgba(255,255,255,0.07)' },
                ...extraY,
            },
        },
    };
}

/**
 * Sincronizza la vista X di `grafico` con quella di `altro`.
 * Chiamata dopo ogni update, perche' i due grafici restino allineati.
 */
function sincronizzaVista(grafico, altro) {
    if (!grafico || !altro) return;
    const scala = grafico.scales && grafico.scales.x;
    if (!scala || scala.min === undefined) return;
    if (altro.options.scales.x.min === scala.min) return; // gia' allineato

    altro.options.scales.x.min = scala.min;
    altro.options.scales.x.max = scala.max;
    altro.update('none');
}

function collegaSincronizzazione(grafico, altro) {
    const aggiorna = grafico.update.bind(grafico);
    let inCorso = false;

    grafico.update = (...args) => {
        const risultato = aggiorna(...args);
        // Evita ricorsione reciproca fra i due grafici.
        if (!inCorso) {
            inCorso = true;
            sincronizzaVista(grafico, altro);
            inCorso = false;
        }
        return risultato;
    };
}

function initCharts() {
    analogChart = new Chart(
        document.getElementById('analog-chart'),
        {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Canale analogico',
                    data: [],
                    borderColor: '#00d4ff',
                    backgroundColor: 'rgba(0, 212, 255, 0.12)',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    tension: 0,
                }],
            },
            options: baseOptions('Valore analogico'),
        }
    );

    digitalChart = new Chart(
        document.getElementById('digital-chart'),
        {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Canale digitale',
                    data: [],
                    borderColor: '#ff6b6b',
                    backgroundColor: 'rgba(255, 107, 107, 0.15)',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    stepped: true,
                }],
            },
            options: baseOptions('Stato (0/1)', { min: -0.1, max: 1.1 }),
        }
    );

    collegaSincronizzazione(analogChart, digitalChart);
    collegaSincronizzazione(digitalChart, analogChart);
}

function updateCharts(analog, digital) {
    if (!analog.length) return;

    const labels = Array.from({ length: analog.length }, (_, i) => i);

    analogChart.data.labels = labels;
    analogChart.data.datasets[0].data = analog;
    analogChart.update('none');

    digitalChart.data.labels = labels;
    digitalChart.data.datasets[0].data = digital;
    digitalChart.update('none');
}

// ---------------------------------------------------------------------
// Controlli
// ---------------------------------------------------------------------

function entrambi(fn) {
    [analogChart, digitalChart].forEach((c) => c && fn(c));
}

function zoomBy(fattore) {
    entrambi((c) => c.zoom(fattore));
}

function panBy(delta) {
    entrambi((c) => c.pan({ x: delta }));
}

function resetView() {
    entrambi((c) => c.resetZoom());
}

function setMode(nuova) {
    document.querySelectorAll('[data-mode]').forEach((btn) => {
        btn.classList.toggle('attivo', btn.dataset.mode === nuova);
    });

    entrambi((chart) => {
        const z = chart.options.plugins.zoom;
        z.zoom.enabled = (nuova === 'zoom' || nuova === 'select');
        z.zoom.drag = (nuova === 'select');
        z.pan.enabled = (nuova === 'pan');

        if (nuova === 'select') {
            z.zoom.dragBackgroundColor = 'rgba(0, 212, 255, 0.25)';
            z.zoom.dragBorderColor = '#00d4ff';
            z.zoom.dragBorderWidth = 1;
        }
        chart.update('none');
    });
}

// ---------------------------------------------------------------------
// WebSocket
// ---------------------------------------------------------------------

function initWebSocket() {
    const socket = io();

    socket.on('connect', () => setConnection(true));
    socket.on('disconnect', () => setConnection(false));

    socket.on('samples', (dati) => {
        updateCharts(dati.analog, dati.digital);
        updateReadout(dati);
    });

    socket.on('acquisition_state', (stato) => {
        acquiring = stato.acquiring;
        updateButtons();
    });

    socket.on('buffer_cleared', () => {
        updateCharts([0], [0]);
        document.getElementById('sample-count').textContent = '0';
        document.getElementById('block-count').textContent = '0';
    });

    window.socket = socket;
}

function setConnection(connesso) {
    const el = document.getElementById('connection-status');
    el.textContent = connesso ? 'Connesso' : 'Disconnesso';
    el.className = 'status ' + (connesso ? 'connected' : 'disconnected');
}

function updateButtons() {
    document.getElementById('btn-start').disabled = acquiring;
    document.getElementById('btn-stop').disabled = !acquiring;

    const el = document.getElementById('acq-state');
    el.textContent = acquiring ? 'In corso' : 'Ferma';
    el.className = 'badge ' + (acquiring ? 'on' : 'off');
}

function updateReadout(dati) {
    document.getElementById('sample-count').textContent = dati.total;
    document.getElementById('block-count').textContent = dati.blocks;
    document.getElementById('sample-rate').textContent =
        (dati.sample_rate / 1000).toFixed(1) + ' kHz';
}

// ---------------------------------------------------------------------
// Azioni
// ---------------------------------------------------------------------

function startAcquisition() {
    if (window.socket) window.socket.emit('start_acquisition');
}

function stopAcquisition() {
    if (window.socket) window.socket.emit('stop_acquisition');
}

function clearBuffer() {
    if (window.socket) window.socket.emit('clear_buffer');
}

async function refreshStatus() {
    try {
        const risposta = await fetch('/api/status');
        const dati = await risposta.json();
        const a = dati.acquisition;

        document.getElementById('sample-rate').textContent =
            (a.sample_rate_hz / 1000).toFixed(1) + ' kHz';
        document.getElementById('block-size').textContent =
            a.block_size + ' campioni';
        document.getElementById('buffer-limit').textContent =
            a.max_samples.toLocaleString('it-IT');
    } catch (err) {
        console.error('Impossibile leggere lo stato:', err);
    }
}
