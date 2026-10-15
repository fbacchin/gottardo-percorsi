# Mappe e pagine: si devono capire al volo, anche dall'app GitHub sul telefono.
from datetime import datetime, timedelta
from config import COLORI, MISURE, SOGLIE, ZURIGO

LEGENDA = (("🟢", "meno di 1 min"), ("🟡", "meno di 10"), ("🟠", "meno di 40"), ("🔴", "40 o più"), ("⚪", "nessun dato"))

def pallino(v):
    if v is None or v == "":
        return "⚪"
    for soglia, simbolo in SOGLIE:
        if int(v) < soglia:
            return simbolo
    return "🔴"

# ---------------------------------------------------------------------------------------------
# Mappa della strada: dove c'è traffico in un dato momento. Una corsia per senso di marcia,
# tra Göschenen e Airolo due rami: galleria (in alto) e passo (in basso).

X = {"Erstfeld": 110, "Amsteg": 230, "Göschenen": 370, "Airolo": 680, "Faido": 820, "Biasca": 950}
LAT = [("Erstfeld", 46.834), ("Amsteg", 46.772), ("Göschenen", 46.672), ("Airolo", 46.527), ("Faido", 46.466), ("Biasca", 46.355)]
RAMO_PASSO = [(46.672, 370), (46.636, 440), (46.5588, 520), (46.527, 680)]   # Göschenen, Andermatt, Passo, Airolo
Y_GALLERIA, Y_PASSO, CORSIA = 78, 158, 14            # y della corsia «verso sud»; quella «verso nord» è CORSIA più in basso
LIVELLO_WAZE = {1: "🟡", 2: "🟡", 3: "🟠", 4: "🔴", 5: "🔴"}

def _nome(senso, tratta, percorso):
    lunga = {"NS": "NS Erstfeld-Biasca", "SN": "SN Biasca-Erstfeld"}
    corta = {"NS": "NS Amsteg-Faido", "SN": "SN Faido-Amsteg"}
    return f"{(lunga if tratta == 'lunga' else corta)[senso]} {percorso}"

def _valore(riga, nome):
    v = (riga or {}).get(nome, "")
    return None if v in ("", None) else int(v)

def situazione(righe_per_fonte, fonte_colore="apple"):
    """Ritardi per tratto di strada da una riga per fonte (stesso momento).
    centro = Amsteg–Faido; esterni = Erstfeld–Biasca meno Amsteg–Faido (i due estremi insieme)."""
    riga = righe_per_fonte.get(fonte_colore)
    s = {}
    for senso in ("NS", "SN"):
        for percorso in ("tunnel", "passo"):
            s[(senso, percorso)] = _valore(riga, _nome(senso, "corta", percorso))
        lunga, corta = _valore(riga, _nome(senso, "lunga", "tunnel")), _valore(riga, _nome(senso, "corta", "tunnel"))
        s[(senso, "esterni")] = None if lunga is None or corta is None else lunga - corta
    return s

def _x_da_lat(lat, punti):
    """Posizione orizzontale sullo schema per interpolazione sulle latitudini (la strada corre da nord a sud)."""
    for (la1, x1), (la2, x2) in zip(punti, punti[1:]):
        if la1 >= lat >= la2:
            return x1 + (x2 - x1) * (la1 - lat) / (la1 - la2)
    return None

def _senso_waze(strada):
    """Il senso si legge dalla destinazione nel nome della strada («A2 > Zürich / Luzern …» = verso nord)."""
    # ponytail: euristica sul testo di Waze; se non c'è una destinazione nota la coda va su entrambe le corsie
    s = (strada or "").lower()
    if any(n in s for n in ("zürich", "zurich", "luzern", "basel", "altdorf")):
        return "SN"
    if any(n in s for n in ("chiasso", "lugano", "bellinzona", "milano", "biasca")):
        return "NS"
    return None

def _parallela(punti, d):
    """La stessa linea spostata di d a destra del verso di percorrenza (giunti ad angolo), per affiancare le corsie."""
    import math
    if d == 0:
        return punti
    normali = []
    for (x1, y1), (x2, y2) in zip(punti, punti[1:]):
        l = math.hypot(x2 - x1, y2 - y1)
        normali.append((-(y2 - y1) / l, (x2 - x1) / l))
    out = []
    for i, (x, y) in enumerate(punti):
        a, b = normali[max(i - 1, 0)], normali[min(i, len(normali) - 1)]
        nx, ny = a[0] + b[0], a[1] + b[1]
        scala = d * 2 / (nx * nx + ny * ny)                       # spostamento d da entrambi i segmenti nel giunto
        out.append((x + nx * scala, y + ny * scala))
    return out

def mappa(titolo, sit, code_waze=(), numeri=(), sottotitolo=""):
    W, H = 1000, 250 + 16 * len(numeri)
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
         f'font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif" font-size="12">',
         f"<title>{titolo}</title>", f'<rect width="{W}" height="{H}" rx="8" fill="#ffffff"/>',
         f'<text x="16" y="26" fill="#202124" font-size="15" font-weight="700">{titolo}</text>']
    if sottotitolo:
        o.append(f'<text x="16" y="44" fill="#5f6368" font-size="11">{sottotitolo}</text>')
    colore = (lambda v: "#e3e5e8") if sit is None else (lambda v: COLORI[pallino("" if v is None else v)])
    sit = sit or {}

    def corsie(punti, y, chiave_sud, chiave_nord):
        for k, (senso, chiave) in enumerate((("NS", chiave_sud), ("SN", chiave_nord))):
            pts = " ".join(f"{x:.1f},{yy:.1f}" for x, yy in _parallela(punti, k * CORSIA))
            o.append(f'<polyline points="{pts}" fill="none" stroke="{colore(sit.get(chiave))}" stroke-width="10" stroke-linejoin="round"/>')

    # Rami: prima il passo (sotto), poi la strada principale e la galleria.
    corsie([(X["Göschenen"], Y_GALLERIA), (X["Göschenen"] + 30, Y_PASSO), (X["Airolo"] - 30, Y_PASSO), (X["Airolo"], Y_GALLERIA)],
           0, ("NS", "passo"), ("SN", "passo"))
    o.append(f'<rect x="{X["Göschenen"] + 20}" y="{Y_GALLERIA - 10}" width="{X["Airolo"] - X["Göschenen"] - 40}" height="{CORSIA + 20}" rx="6" fill="#3c4043"/>')
    for a, b, chiave in (("Erstfeld", "Amsteg", "esterni"), ("Amsteg", "Göschenen", "tunnel"), ("Göschenen", "Airolo", "tunnel"),
                         ("Airolo", "Faido", "tunnel"), ("Faido", "Biasca", "esterni")):
        corsie([(X[a], Y_GALLERIA), (X[b], Y_GALLERIA)], 0, ("NS", chiave), ("SN", chiave))
    o.append(f'<text x="{(X["Göschenen"] + X["Airolo"]) / 2:.0f}" y="{Y_GALLERIA - 16}" text-anchor="middle" fill="#202124" font-size="11" font-weight="600">Galleria 17 km</text>')
    xp = RAMO_PASSO[2][1]
    o.append(f'<path d="M{xp - 11},{Y_PASSO + CORSIA + 22} L{xp},{Y_PASSO + CORSIA + 8} L{xp + 11},{Y_PASSO + CORSIA + 22} Z" fill="#3c4043"/>')
    o.append(f'<text x="{xp}" y="{Y_PASSO + CORSIA + 36}" text-anchor="middle" fill="#202124" font-size="11" font-weight="600">Passo 2106 m</text>')
    o.append(f'<text x="{RAMO_PASSO[1][1]}" y="{Y_PASSO + CORSIA + 22}" text-anchor="middle" fill="#5f6368" font-size="11">Andermatt</text>')
    for n, x in X.items():
        o.append(f'<line x1="{x}" y1="{Y_GALLERIA - 12}" x2="{x}" y2="{Y_GALLERIA + CORSIA + 6}" stroke="#ffffff" stroke-width="2"/>')
        o.append(f'<text x="{x}" y="{Y_GALLERIA - 16 if n not in ("Göschenen", "Airolo") else Y_GALLERIA - 30}" text-anchor="middle" fill="#5f6368" font-size="11">{n}</text>')
    o.append(f'<text x="96" y="{Y_GALLERIA + 4}" text-anchor="end" fill="#5f6368" font-size="11">verso sud →</text>')
    o.append(f'<text x="96" y="{Y_GALLERIA + CORSIA + 4}" text-anchor="end" fill="#5f6368" font-size="11">← verso nord</text>')

    # Code segnalate da Waze, nel punto in cui sono: barra con bordo scuro sopra la corsia.
    for c in code_waze:
        try:
            lat, lon = float(c["lat"]), float(c["lon"])
        except (TypeError, ValueError):
            continue                                              # coda senza coordinate: non si sa dove disegnarla
        sul_passo = lon < 8.60 and 46.535 < lat < 46.66
        x = _x_da_lat(lat, RAMO_PASSO if sul_passo else [(la, X[n]) for n, la in LAT])
        if x is None:
            continue
        y0 = Y_PASSO if sul_passo else Y_GALLERIA
        # Alla scala della mappa (~11,6 punti per km) una coda di 1-2 km sarebbe invisibile sul telefono: larghezza minima 18.
        largo = max(18, float(c.get("lunghezza_m") or 0) / 1000 * 11.6)
        sensi = [_senso_waze(c.get("strada"))] if _senso_waze(c.get("strada")) else ["NS", "SN"]
        for senso in sensi:
            y = y0 + (CORSIA if senso == "SN" else 0)
            o.append(f'<rect x="{x - largo / 2:.0f}" y="{y - 8}" width="{largo:.0f}" height="16" rx="4" '
                     f'fill="{COLORI[LIVELLO_WAZE.get(int(c.get("livello") or 3), "🟠")]}" stroke="#202124" stroke-width="2"/>')

    y = 232
    for riga in numeri:
        o.append(f'<text x="16" y="{y}" fill="#3c4043" font-size="11">{riga}</text>')
        y += 16
    x = 560                                                      # legenda in alto a destra
    for simbolo, testo in LEGENDA[:4]:
        o.append(f'<rect x="{x}" y="16" width="12" height="9" fill="{COLORI[simbolo]}"/>')
        o.append(f'<text x="{x + 16}" y="25" fill="#5f6368" font-size="10">{testo}</text>')
        x += 24 + 6 * len(testo)
    o.append("</svg>")
    return "\n".join(o) + "\n"


# ---------------------------------------------------------------------------------------------
# Pagine: il README mostra l'ultimo rilievo, una mappa per fonte; «◀ 15 minuti prima» porta alle pagine precedenti.
# Ogni mappa ha l'orario nel nome e non cambia più: a ogni giro si aggiungono solo le mappe nuove.

FONTI_MAPPA = (("apple", "Apple Maps"), ("tomtom", "TomTom"), ("google", "Google"),
               ("openwebninja", "Waze (OpenWeb Ninja)"), ("apify", "Waze (Apify)"))
PASSI_STORIA = 12                      # 3 ore di quarti d'ora

def nome_mappa(quando, fonte):
    return f"mappe/{quando:%Y-%m-%d-%H%M}-{fonte}.svg"

def numeri_fonte(riga, totali):
    """Righe di testo sotto la mappa: ritardo e tempo totale su Erstfeld–Biasca, per senso e percorso."""
    out = []
    for senso, testo in (("NS", "verso sud"), ("SN", "verso nord")):
        parti = []
        for perc, nome_p in (("tunnel", "galleria"), ("passo", "passo")):
            n = _nome(senso, "lunga", perc)
            v, t = _valore(riga, n), (totali or {}).get(n)
            parti.append(f"{nome_p} " + ("nessun dato" if v is None else f"{'+' if v > 0 else ''}{v} min" + (f" · totale {t} min" if t is not None else "")))
        out.append(f"Erstfeld–Biasca {testo}: " + "   |   ".join(parti))
    return out

def elenco_waze(code, massimo=8):
    """Una riga per coda, la più lunga prima: «Airolo, verso nord: coda 2,1 km a 8 km/h»."""
    def km(c):
        try:
            return float(c.get("lunghezza_m") or 0)
        except ValueError:
            return 0.0
    righe = []
    for c in sorted(code, key=km, reverse=True)[:massimo]:
        senso = {"NS": "verso sud", "SN": "verso nord"}.get(_senso_waze(c.get("strada")), "senso non indicato")
        luogo = c.get("citta") or c.get("strada") or "luogo non indicato"
        cosa = "chiusura" if "CLOSED" in str(c.get("sottotipo") or "") else "coda"
        riga = f"{luogo}, {senso}: {cosa} {km(c) / 1000:.1f} km".replace(".", ",")
        try:
            if cosa == "coda" and c.get("velocita_kmh") not in (None, ""):
                riga += f" a {round(float(c['velocita_kmh']))} km/h"
        except ValueError:
            pass
        righe.append(riga)
    return righe

def mappa_fonte(fonte, quando, riga=None, totali=None, code_waze=None, ora_misura=None):
    etichetta = dict(FONTI_MAPPA)[fonte]
    titolo = f"{etichetta} — {quando:%H:%M}"
    sotto = f"misura delle {ora_misura}" if ora_misura and ora_misura != f"{quando:%Y-%m-%d %H:%M}" else ""
    if code_waze is not None:
        n = len(code_waze)
        titolo_elenco = "nessuna coda segnalata da Waze" if n == 0 else "1 coda segnalata da Waze:" if n == 1 else f"{n} code segnalate da Waze:"
        return mappa(titolo, None, code_waze, [titolo_elenco] + elenco_waze(code_waze), sotto)
    if riga is None:
        return mappa(titolo, {}, (), ["nessun dato in questo quarto d'ora"], sotto)
    return mappa(titolo, situazione({fonte: riga}, fonte), (), numeri_fonte(riga, totali), sotto)

def pagine(adesso, esiste):
    """{percorso: testo markdown} per il README e le pagine storia/<minuti>.md; esiste(percorso) dice se una mappa c'è."""
    out = {}
    for k in range(PASSI_STORIA):
        quando = adesso - timedelta(minutes=15 * k)
        su = "" if k == 0 else "../"
        quanto = "adesso" if k == 0 else f"{15 * k} minuti fa" if k < 4 else (f"{k // 4} h {15 * (k % 4)} min fa" if k % 4 else f"{k // 4} h fa")
        link = []
        if k < PASSI_STORIA - 1:
            link.append(f"[◀ 15 minuti prima]({'storia/' if k == 0 else ''}{15 * (k + 1)}.md)")
        if k > 0:
            link.append(f"[Adesso]({su}README.md)")
            link.append(f"[15 minuti dopo ▶]({'../README.md' if k == 1 else f'{15 * (k - 1)}.md'})")
        righe = [f"# Gottardo — traffico alle {quando:%H:%M}", "", f"**{quando:%d.%m.%Y %H:%M}** (ora svizzera, {quanto})", "",
                 " · ".join(link), "",
                 " · ".join(f"{p} {t}" for p, t in LEGENDA[:4]) + " · le barre con bordo nero sono code segnalate da Waze", ""]
        for fonte, etichetta in FONTI_MAPPA:
            m = nome_mappa(quando, fonte)
            righe += [f"### {etichetta}", "", f"![{etichetta}]({su}{m})" if esiste(m) else "_nessuna mappa per questo quarto d'ora_", ""]
        righe += [" · ".join(link), ""]
        out["README.md" if k == 0 else f"storia/{15 * k}.md"] = "\n".join(righe)
    return out
