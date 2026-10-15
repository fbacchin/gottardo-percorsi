# Configurazione di gottardo-percorsi (ADEV-773). Specifica: Doc/ADEV-773/spec.md nel progetto Gotthard.
from zoneinfo import ZoneInfo

ZURIGO = ZoneInfo("Europe/Zurich")

# Punti dove la rampa d'uscita dell'A2 incontra la strada locale (OpenStreetMap, 15.10.2026).
# Il passo è un punto sulla strada 2 al valico, non l'Ospizio (che sta su un piazzale a lato).
PUNTI = {
    "Erstfeld": (46.83446, 8.63694),
    "Amsteg":   (46.77208, 8.66830),
    "Faido":    (46.46584, 8.82325),
    "Biasca":   (46.35530, 8.96100),   # strada locale a est dello svincolo: sulla rampa Apple lo agganciava alla carreggiata verso sud (Biasca→Faido 52,8 km)
    "Passo":    (46.55880, 8.56210),
}
VALICO = "Passo"   # punto obbligato del percorso «passo»

# (nome = intestazione CSV, origine, destinazione, percorso). NS = nord→sud, SN = sud→nord.
MISURE = [   # prima i percorsi col tunnel, poi quelli sul passo (richiesta dell'utente)
    ("NS Erstfeld-Biasca tunnel", "Erstfeld", "Biasca", "tunnel"),
    ("SN Biasca-Erstfeld tunnel", "Biasca", "Erstfeld", "tunnel"),
    ("NS Amsteg-Faido tunnel",    "Amsteg", "Faido", "tunnel"),
    ("SN Faido-Amsteg tunnel",    "Faido", "Amsteg", "tunnel"),
    ("NS Erstfeld-Biasca passo",  "Erstfeld", "Biasca", "passo"),
    ("SN Biasca-Erstfeld passo",  "Biasca", "Erstfeld", "passo"),
    ("NS Amsteg-Faido passo",     "Amsteg", "Faido", "passo"),
    ("SN Faido-Amsteg passo",     "Faido", "Amsteg", "passo"),
]

# Fonti i cui dati possono stare nel repository pubblico. Vuoto: Apple vieta di pubblicare i suoi dati,
# le condizioni di TomTom non sono verificate (Doc/ADEV-773/preliminari.md).
PUBBLICHE = set()
ORARIE = {"google", "openwebninja", "apify"}          # le altre girano ogni 15 minuti

# Soglie dell'app (HistoryChartView.livello): < 1 verde, < 10 giallo, < 40 arancione, oltre rosso.
SOGLIE = ((1, "🟢"), (10, "🟡"), (40, "🟠"))
COLORI = {"🟢": "#2fb350", "🟡": "#ffcc00", "🟠": "#ff6f00", "🔴": "#c62828", "⚪": "#d5d8dc"}

# Tetti sotto le quote gratuite: (periodo, limite). Apify si conta in dollari.
TETTI = {"tomtom": ("giorno", 2000), "google": ("mese", 4800), "openwebninja": ("mese", 95), "apify": ("mese", 4.50)}
COSTO_APIFY = 0.041   # avvio 0,02 $ + interrogazione area 0,021 $ (livello gratuito, 15.10.2026)

AREA_WAZE = ("46.33,8.50", "46.85,9.00")   # angolo in basso a sinistra, in alto a destra: Erstfeld–Biasca, passo compreso

# Distanza di riferimento per misura (metri), fissata dal primo giro riuscito e controllata a mano.
# Vuota = nessun controllo. Oltre TOLLERANZA la fonte ha calcolato un'altra strada.
RIFERIMENTI_M = {}
TOLLERANZA = 0.05
