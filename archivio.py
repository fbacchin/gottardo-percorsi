# Ritardi, esiti e file CSV. Righe più recenti in cima, subito sotto l'intestazione.
import csv, os
from datetime import timedelta
from config import MISURE, RIFERIMENTI_M, TOLLERANZA

def risultato(misura, con=None, senza=None, distanza=None, esito="ok"):
    return {"misura": misura, "con_traffico_s": con, "senza_traffico_s": senza, "distanza_m": distanza, "esito": esito}

def ritardo_min(r):
    """Minuti di ritardo sulla strada libera; None se la misura non è riuscita. Mai un tempo inventato."""
    if r["esito"] != "ok":
        return None
    return round((r["con_traffico_s"] - r["senza_traffico_s"]) / 60)

def controlla_distanza(r, riferimenti=RIFERIMENTI_M, tolleranza=TOLLERANZA):
    """Distanza lontana dal riferimento = la fonte ha calcolato un'altra strada (tunnel o passo chiusi)."""
    rif = riferimenti.get(r["misura"])
    if r["esito"] == "ok" and rif and abs(r["distanza_m"] - rif) / rif > tolleranza:
        return {**r, "esito": "percorso diverso"}
    return r

INTESTAZIONE = ["ora"] + [m[0] for m in MISURE] + ["esito"]

def riga_sintetica(ora, risultati):
    per_nome = {r["misura"]: r for r in risultati}
    valori = [ritardo_min(per_nome[m[0]]) if m[0] in per_nome else None for m in MISURE]   # misura che la fonte non fa: cella vuota
    problemi = [f'{r["misura"]}: {r["esito"]}' for r in risultati if r["esito"] != "ok"]
    return [ora] + ["" if v is None else v for v in valori] + ["; ".join(problemi) or "ok"]

INTESTAZIONE_DETTAGLIO = ["ora", "ora_utc", "misura", "con_traffico_s", "senza_traffico_s", "distanza_m", "esito"]

def righe_dettaglio(ora, ora_utc, risultati):
    vuoto = lambda x: "" if x is None else x
    return [[ora, ora_utc, r["misura"], vuoto(r["con_traffico_s"]), vuoto(r["senza_traffico_s"]), vuoto(r["distanza_m"]), r["esito"]]
            for r in risultati]

def file_mese(cartella, nome, quando, suffisso=""):
    return os.path.join(cartella, f"{nome}-{quando:%Y-%m}{suffisso}.csv")

def aggiungi_in_cima(percorso, intestazione, righe):
    vecchie = []
    if os.path.exists(percorso):
        with open(percorso, newline="", encoding="utf-8") as f:
            r = csv.reader(f)
            testa = next(r, intestazione)
            # Colonne nuove (16.10, Göschenen–Airolo): le righe vecchie si riallineano per nome, le celle mancanti restano vuote.
            vecchie = [row if testa == intestazione else [dict(zip(testa, row)).get(c, "") for c in intestazione] for row in r]
    os.makedirs(os.path.dirname(percorso) or ".", exist_ok=True)
    with open(percorso, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(intestazione)
        w.writerows(righe)
        w.writerows(vecchie)

def ultime_24h(cartella, nome, adesso):
    """Righe delle ultime 24 ore (ora svizzera), più recenti prima, anche a cavallo di due mesi."""
    # ponytail: confronto su testo «AAAA-MM-GG HH:MM»; nella notte del cambio d'ora d'autunno un'ora si ripete, ininfluente per un grafico di 24 ore
    limite = f"{adesso - timedelta(hours=24):%Y-%m-%d %H:%M}"
    righe = []
    for quando in (adesso, adesso.replace(day=1) - timedelta(days=1)):
        p = file_mese(cartella, nome, quando)
        if os.path.exists(p):
            with open(p, newline="", encoding="utf-8") as f:
                righe += [r for r in csv.DictReader(f) if r["ora"] > limite]
    return sorted(righe, key=lambda r: r["ora"], reverse=True)

from config import TETTI

def _periodo(fonte, adesso):
    return f"{adesso:%Y-%m-%d}" if TETTI[fonte][0] == "giorno" else f"{adesso:%Y-%m}"

def consenti(uso, fonte, quanto, adesso):
    """Vero se la richiesta resta sotto il tetto. Le fonti senza tetto passano sempre."""
    if fonte not in TETTI:
        return True
    return uso.get(fonte, {}).get(_periodo(fonte, adesso), 0) + quanto <= TETTI[fonte][1] + 1e-9

def registra(uso, fonte, quanto, adesso):
    """Si registra PRIMA della chiamata: una richiesta fallita può essere addebitata lo stesso."""
    if fonte in TETTI:
        k = _periodo(fonte, adesso)
        uso.setdefault(fonte, {})[k] = round(uso.get(fonte, {}).get(k, 0) + quanto, 4)

def ultimi_totali(cartella, nome, adesso):
    """Tempo totale di percorrenza (minuti, con traffico) dell'ultimo giro, per misura; solo le misure riuscite."""
    righe = []
    for quando in (adesso, adesso.replace(day=1) - timedelta(days=1)):
        p = file_mese(cartella, nome, quando, "-dettaglio")
        if os.path.exists(p):
            with open(p, newline="", encoding="utf-8") as f:
                righe += list(csv.DictReader(f))
    if not righe:
        return {}
    ultima = max(r["ora"] for r in righe)
    return {r["misura"]: round(int(r["con_traffico_s"]) / 60) for r in righe if r["ora"] == ultima and r["esito"] == "ok"}
