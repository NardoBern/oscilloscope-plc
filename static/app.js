/**
 * Frontend per l'oscilloscopio PLC
 * Gestisce i grafici in tempo reale e la comunicazione WebSocket
 */

// Configurazione
const MAX_POINTS = 1000;
const UPDATE_INTERVAL = 50; // ms

// Stato
let socket = null;
let analogChart = null;
let digitalChart = null;
let isAcquiring = false;
let currentMode = 'zoom'; // 'zoom', 'pan', 'select'

// Inizializzazione
document.addEventListener('DOMContentLoaded', function() {
    initCharts();
    connectWebSocket();
    updateStatus();
});

/**
 * Inizializza i grafici Chart.js
 */
function initCharts() {
    const commonOptions = {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        interaction: {
            intersect: false,
            mode: 'index',
        },
        plugins: {
            legend: {
                labels: {
                    color: '#fff',
                }
            },
            tooltip: {
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                titleColor: '#fff',
                bodyColor: '#fff',
                borderColor: '#00d4ff',
                borderWidth: 1,
            },
            zoom: {
                zoom: {
                    enabled: true,
                    mode: 'x',
                    drag: false,
                    speed: 0.1,
                },
                pan: {
                    enabled: false,
                    mode: 'x',
                    speed: 20,
                },
                limits: {
                    x: {min: 'original', max: 'original'},
                }
            }
        },
        scales: {
            x: {
                type: 'linear',
                title: {
                    display: true,
                    text: 'Campioni',
                    color: '#888',
                },
                ticks: {
                    color: '#888',
                },
                grid: {
                    color: 'rgba(255, 255, 255, 0.1)',
                }
            },
            y: {
                title: {
                    display: true,
                    text: 'Valore',
                    color: '#888',
                },
                ticks: {
                    color: '#888',
                },
                grid: {
                    color: 'rgba(255, 255, 255, 0.1)',
                }
            }
        }
    };

    // Grafico analogico
    const analogCtx = document.getElementById('analog-chart').getContext('2d');
    analogChart = new Chart(analogCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Valore Analogico',
                data: [],
                borderColor: '#00d4ff',
                backgroundColor: 'rgba(0, 212, 255, 0.1)',
                borderWidth: 2,
                pointRadius: 0,
                pointHoverRadius: 4,
                fill: true,
                tension: 0.1,
            }]
        },
        options: {
            ...commonOptions,
            scales: {
                ...commonOptions.scales,
                y: {
                    ...commonOptions.scales.y,
                    title: {
                        ...commonOptions.scales.y.title,
                        text: 'Valore (unità ingegneristica)',
                    }
                }
            }
        }
    });

    // Grafico digitale
    const digitalCtx = document.getElementById('digital-chart').getContext('2d');
    digitalChart = new Chart(digitalCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Valore Digitale',
                data: [],
                borderColor: '#ff6b6b',
                backgroundColor: 'rgba(255, 107, 107, 0.1)',
                borderWidth: 2,
                pointRadius: 0,
                pointHoverRadius: 4,
                fill: true,
                stepped: true,
            }]
        },
        options: {
            ...commonOptions,
            scales: {
                ...commonOptions.scales,
                y: {
                    ...commonOptions.scales.y,
                    min: -0.1,
                    max: 1.1,
                    title: {
                        ...commonOptions.scales.y.title,
                        text: 'Stato (0/1)',
                    }
                }
            }
        }
    });
}

/**
 * Connette al server WebSocket
 */
function connectWebSocket() {
    socket = io();

    socket.on('connect', function() {
        console.log('[WebSocket] Connesso');
        updateConnectionStatus(true);
    });

    socket.on('disconnect', function() {
        console.log('[WebSocket] Disconnesso');
        updateConnectionStatus(false);
    });

    socket.on('new_data', function(data) {
        if (isAcquiring) {
            updateCharts(data);
            updateInfo(data);
        }
    });

    socket.on('acquisition_started', function(data) {
        console.log('[WebSocket] Acquisizione avviata');
        isAcquiring = true;
        updateButtons();
    });

    socket.on('acquisition_stopped', function(data) {
        console.log('[WebSocket] Acquisizione fermata');
        isAcquiring = false;
        updateButtons();
    });
}

/**
 * Avvia l'acquisizione
 */
function startAcquisition() {
    if (socket) {
        socket.emit('start_acquisition');
    }
}

/**
 * Ferma l'acquisizione
 */
function stopAcquisition() {
    if (socket) {
        socket.emit('stop_acquisition');
    }
    isAcquiring = false;
    updateButtons();
}

/**
 * Pulisce i grafici
 */
function clearCharts() {
    analogChart.data.labels = [];
    analogChart.data.datasets[0].data = [];
    analogChart.update();

    digitalChart.data.labels = [];
    digitalChart.data.datasets[0].data = [];
    digitalChart.update();

    document.getElementById('sample-count').textContent = '0';
    document.getElementById('last-update').textContent = '-';
}

/**
 * Aggiorna i grafici con i nuovi dati
 */
function updateCharts(data) {
    if (!data || !data.analog || !data.digital) return;

    const analogData = data.analog;
    const digitalData = data.digital;
    const labels = Array.from({length: analogData.length}, (_, i) => i);

    // Aggiorna grafico analogico
    analogChart.data.labels = labels;
    analogChart.data.datasets[0].data = analogData;
    analogChart.update('none');

    // Aggiorna grafico digitale
    digitalChart.data.labels = labels;
    digitalChart.data.datasets[0].data = digitalData;
    digitalChart.update('none');
    
    // Aggiorna contatore campioni
    document.getElementById('sample-count').textContent = analogData.length;
}

/**
 * Aggiorna le informazioni
 */
function updateInfo(data) {
    document.getElementById('sample-count').textContent = data.sample_count || 0;
    document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
}

/**
 * Aggiorna lo stato di connessione
 */
function updateConnectionStatus(connected) {
    const statusEl = document.getElementById('connection-status');
    if (connected) {
        statusEl.textContent = 'Connesso';
        statusEl.className = 'status connected';
    } else {
        statusEl.textContent = 'Disconnesso';
        statusEl.className = 'status disconnected';
    }
}

/**
 * Aggiorna i pulsanti
 */
function updateButtons() {
    const btnStart = document.getElementById('btn-start');
    const btnStop = document.getElementById('btn-stop');

    if (isAcquiring) {
        btnStart.disabled = true;
        btnStop.disabled = false;
    } else {
        btnStart.disabled = false;
        btnStop.disabled = true;
    }
}

/**
 * Aggiorna lo stato dal server
 */
function updateStatus() {
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            if (data.plc && data.plc.use_simulator) {
                document.getElementById('mode-info').textContent = 'Simulatore';
            } else {
                document.getElementById('mode-info').textContent = 'PLC Reale';
            }
        })
        .catch(error => {
            console.error('[Status] Errore:', error);
        });
}

// === Controlli Zoom e Pan ===

/**
 * Zoom avanti su entrambi i grafici
 */
function zoomIn() {
    [analogChart, digitalChart].forEach(chart => {
        if (chart) {
            chart.zoom(1.2);
        }
    });
}

/**
 * Zoom indietro su entrambi i grafici
 */
function zoomOut() {
    [analogChart, digitalChart].forEach(chart => {
        if (chart) {
            chart.zoom(0.8);
        }
    });
}

/**
 * Reset zoom su entrambi i grafici
 */
function resetZoom() {
    [analogChart, digitalChart].forEach(chart => {
        if (chart) {
            chart.resetZoom();
        }
    });
}

/**
 * Scorri a sinistra (pan)
 */
function panLeft() {
    [analogChart, digitalChart].forEach(chart => {
        if (chart) {
            chart.pan({x: -50});
        }
    });
}

/**
 * Scorri a destra (pan)
 */
function panRight() {
    [analogChart, digitalChart].forEach(chart => {
        if (chart) {
            chart.pan({x: 50});
        }
    });
}

/**
 * Imposta la modalità di interazione
 */
function setMode(mode) {
    currentMode = mode;
    
    // Aggiorna i pulsanti
    document.querySelectorAll('.btn-mode').forEach(btn => {
        btn.classList.remove('active');
    });
    
    if (mode === 'zoom') {
        document.getElementById('btn-mode-zoom').classList.add('active');
    } else if (mode === 'pan') {
        document.getElementById('btn-mode-pan').classList.add('active');
    } else if (mode === 'select') {
        document.getElementById('btn-mode-select').classList.add('active');
    }
    
    // Aggiorna le opzioni dei grafici
    [analogChart, digitalChart].forEach(chart => {
        if (chart && chart.options.plugins && chart.options.plugins.zoom) {
            // Reset di tutte le opzioni
            chart.options.plugins.zoom.zoom.enabled = false;
            chart.options.plugins.zoom.zoom.drag = false;
            chart.options.plugins.zoom.pan.enabled = false;
            
            if (mode === 'zoom') {
                // Zoom con rotellina del mouse
                chart.options.plugins.zoom.zoom.enabled = true;
                chart.options.plugins.zoom.zoom.mode = 'x';
                chart.options.plugins.zoom.zoom.wheel = { enabled: true };
                chart.options.plugins.zoom.zoom.pinch = { enabled: true };
            } else if (mode === 'pan') {
                // Pan con trascinamento
                chart.options.plugins.zoom.pan.enabled = true;
                chart.options.plugins.zoom.pan.mode = 'x';
            } else if (mode === 'select') {
                // Zoom a finestra (selezione con trascinamento)
                chart.options.plugins.zoom.zoom.enabled = true;
                chart.options.plugins.zoom.zoom.mode = 'x';
                chart.options.plugins.zoom.zoom.drag = true;
                chart.options.plugins.zoom.zoom.dragBackgroundColor = 'rgba(0, 212, 255, 0.3)';
                chart.options.plugins.zoom.zoom.dragBorderColor = '#00d4ff';
                chart.options.plugins.zoom.zoom.dragBorderWidth = 2;
            }
            
            chart.update();
        }
    });
}
