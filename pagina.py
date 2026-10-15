# README e grafico: si devono capire al volo, anche dall'app GitHub sul telefono.
from datetime import datetime, timedelta
from config import COLORI, MISURE, SOGLIE, ZURIGO

ORARIE_SLOT = {"google": 4}   # una misura all'ora copre quattro quarti d'ora nel grafico
# Località da nord a sud; «*» è il tratto Göschenen–Airolo, che cambia col percorso.
STRADA = ["Erstfeld", "Amsteg", "Göschenen", "*", "Airolo", "Faido", "Biasca"]
VALICO_TAPPE = {"tunnel": ["Galleria"], "passo": ["Andermatt", "Passo"]}

def tappe(origine, destinazione, percorso):
    """Località attraversate, nel senso di marcia, con la galleria o il passo in mezzo."""
    strada = []
    for n in STRADA:
        strada += VALICO_TAPPE[percorso] if n == "*" else [n]
    i, j = strada.index(origine), strada.index(destinazione)
    return strada[i:j + 1] if i < j else strada[j:i + 1][::-1]

def _percorso(o, d, percorso, x0, x1, y):
    """Schema del percorso: località come punti su una riga; la galleria è un tratto scuro, il passo una vetta."""
    nomi = tappe(o, d, percorso)
    passo_x = (x1 - x0) / (len(nomi) - 1)
    xs = [x0 + k * passo_x for k in range(len(nomi))]
    out = []
    for k in range(len(nomi) - 1):
        galleria = "Galleria" in (nomi[k], nomi[k + 1])
        out.append(f'<line x1="{xs[k]:.0f}" y1="{y}" x2="{xs[k + 1]:.0f}" y2="{y}" stroke="{"#3c4043" if galleria else "#bdc1c6"}" '
                   f'stroke-width="{6 if galleria else 2}" stroke-linecap="round"/>')
    for k, (n, x) in enumerate(zip(nomi, xs)):
        ancora = "start" if k == 0 else "end" if k == len(nomi) - 1 else "middle"
        if n == "Galleria":
            out.append(f'<text x="{x:.0f}" y="{y - 7}" text-anchor="middle" fill="#202124" font-size="10" font-weight="600">Galleria 17 km</text>')
        elif n == "Passo":
            out.append(f'<path d="M{x - 9:.0f},{y + 1} L{x:.0f},{y - 10} L{x + 9:.0f},{y + 1} Z" fill="#3c4043"/>')
            out.append(f'<text x="{x:.0f}" y="{y - 13}" text-anchor="middle" fill="#202124" font-size="10" font-weight="600">Passo 2106 m</text>')
        else:
            out.append(f'<circle cx="{x:.0f}" cy="{y}" r="3.5" fill="#ffffff" stroke="#5f6368" stroke-width="1.5"/>')
            out.append(f'<text x="{x:.0f}" y="{y - 7}" text-anchor="{ancora}" fill="#5f6368" font-size="10">{n}</text>')
    return out

LEGENDA = (("🟢", "meno di 1 min"), ("🟡", "meno di 10"), ("🟠", "meno di 40"), ("🔴", "40 o più"), ("⚪", "nessun dato"))

def pallino(v):
    if v is None or v == "":
        return "⚪"
    for soglia, simbolo in SOGLIE:
        if int(v) < soglia:
            return simbolo
    return "🔴"

def _cella(v):
    if v is None or v == "":
        return "⚪ —"
    return f"{pallino(v)} {'+' if int(v) > 0 else ''}{int(v)}"

def readme(serie, fonti, ora, extra=""):
    ultime = {f: (serie.get(f) or [{}])[0] for f in fonti}
    righe = ["# Gottardo — tempi di percorrenza", "",
             f"Aggiornato alle **{ora}** (ora svizzera). Ritardo in minuti rispetto alla strada libera, tunnel e passo del San Gottardo.", "",
             "## Adesso", "",
             "| Misura | " + " | ".join(fonti) + " |",
             "|---|" + "---|" * len(fonti)]
    for nome, *_ in MISURE:
        righe.append(f"| {nome} | " + " | ".join(_cella(ultime[f].get(nome)) for f in fonti) + " |")
    righe += ["", " · ".join(f"{p} {t}" for p, t in LEGENDA) + " (il motivo è nella colonna «esito» del CSV)", "",
              "## Ultime 24 ore", "", "![Ultime 24 ore](grafico.svg)", ""]
    if extra:
        righe += [extra, ""]
    righe += ["I dati completi sono nella cartella `dati/`, un file per fonte e per mese, righe più recenti in cima.", ""]
    return "\n".join(righe)

def _slot(righe, nome, inizio, ampiezza):
    """Quarti d'ora (0-95) → valore, dalle righe del CSV sintetico (più recenti prima)."""
    valori = {}
    for r in righe:
        if r.get(nome, "") == "":
            continue
        t = datetime.strptime(r["ora"], "%Y-%m-%d %H:%M").replace(tzinfo=ZURIGO)
        i = int((t - inizio).total_seconds() // 900)
        for k in range(i, i + ampiezza):
            if 0 <= k < 96:
                valori.setdefault(k, r[nome])
    return valori

def grafico(serie, fonti, adesso):
    inizio = adesso - timedelta(hours=24) + timedelta(minutes=15)   # l'ultimo quarto d'ora (indice 95) è quello di adesso
    ETICHETTE, LARGO, ALTO, SPAZIO, TITOLO = 210, 8, 9, 2, 34
    blocco = TITOLO + len(fonti) * (ALTO + SPAZIO) + 10
    W = ETICHETTE + 96 * LARGO + 16
    H = 20 + len(MISURE) * blocco + 56
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
           f'font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif" font-size="12">',
           "<title>Ritardo nelle ultime 24 ore, per misura e per fonte</title>",
           f'<rect width="{W}" height="{H}" rx="8" fill="#ffffff"/>']
    for i in range(0, 97, 12):                                    # una tacca ogni 3 ore
        x, t = ETICHETTE + i * LARGO, inizio + timedelta(minutes=15 * i)
        out.append(f'<line x1="{x}" y1="16" x2="{x}" y2="{H - 52}" stroke="#eceef1"/>')
        out.append(f'<text x="{x}" y="{H - 38}" text-anchor="{"end" if i == 96 else "middle"}" fill="#5f6368">{"adesso" if i == 96 else f"{t:%H:%M}"}</text>')
    y = 20
    for nome, o, d, percorso in MISURE:
        out.append(f'<text x="10" y="{y + 24}" fill="#202124" font-weight="600">{nome}</text>')
        # Fondo bianco sotto lo schema: la griglia delle ore non deve far sembrare le località degli orari.
        out.append(f'<rect x="{ETICHETTE - 4}" y="{y + 2}" width="{96 * LARGO + 8}" height="{TITOLO - 4}" fill="#ffffff"/>')
        out += _percorso(o, d, percorso, ETICHETTE + 6, ETICHETTE + 96 * LARGO - 6, y + 20)
        y += TITOLO
        for f in fonti:
            out.append(f'<text x="{ETICHETTE - 8}" y="{y + 8}" text-anchor="end" fill="#5f6368" font-size="10">{f}</text>')
            out.append(f'<rect x="{ETICHETTE}" y="{y}" width="{96 * LARGO}" height="{ALTO}" fill="{COLORI["⚪"]}"/>')
            # Quarti d'ora consecutivi dello stesso colore in un solo rettangolo: niente righine tra un tratto e l'altro.
            tratti = []
            for i, v in sorted(_slot(serie.get(f, []), nome, inizio, ORARIE_SLOT.get(f, 1)).items()):
                colore = COLORI[pallino(v)]
                if tratti and tratti[-1][2] == colore and tratti[-1][0] + tratti[-1][1] == i:
                    tratti[-1][1] += 1
                else:
                    tratti.append([i, 1, colore])
            for i, n, colore in tratti:
                out.append(f'<rect x="{ETICHETTE + i * LARGO}" y="{y}" width="{n * LARGO}" height="{ALTO}" fill="{colore}"/>')
            y += ALTO + SPAZIO
        y += 10
    x = ETICHETTE                                                 # legenda: il colore non è mai da solo
    for simbolo, testo in LEGENDA:
        out.append(f'<rect x="{x}" y="{H - 22}" width="12" height="9" fill="{COLORI[simbolo]}"/>')
        out.append(f'<text x="{x + 16}" y="{H - 14}" fill="#5f6368" font-size="11">{testo}</text>')
        x += 28 + 7 * len(testo)
    out.append("</svg>")
    return "\n".join(out) + "\n"
