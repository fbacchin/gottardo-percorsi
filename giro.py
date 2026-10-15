# Un giro di gottardo-percorsi: misura, scrive i CSV, disegna le mappe del quarto d'ora e aggiorna le pagine.
# Uso: python3 giro.py  (dal repository pubblico, con il privato clonato in ./privati)
# REGOLA: niente in uscita che possa contenere una chiave. Si stampano solo fonte ed esito.
import csv, json, os, re
from datetime import datetime, timedelta, timezone
import fonti
from archivio import (INTESTAZIONE, INTESTAZIONE_DETTAGLIO, aggiungi_in_cima, consenti, controlla_distanza, file_mese,
                      registra, riga_sintetica, righe_dettaglio, risultato, ultime_24h, ultimi_totali)
from config import COSTO_APIFY, MISURE, ORARIE, PUBBLICHE, ZURIGO
from fonti import CAMPI_WAZE
from pagina import PASSI_STORIA, mappa_fonte, nome_mappa, pagine

CHIAVI = {"apple": "APPLE_MAPS_PRIVATE_KEY", "tomtom": "TOMTOM_KEY", "google": "GOOGLE_ROUTES_KEY",
          "openwebninja": "OPENWEBNINJA_KEY", "apify": "APIFY_TOKEN"}

def _tutte(esito):
    return [risultato(m[0], esito=esito) for m in MISURE]

def _sicura(funzione):
    """Un'eccezione diventa un esito col solo nome: il messaggio potrebbe contenere l'URL con la chiave."""
    try:
        return funzione()
    except Exception as e:
        return _tutte(f"errore {type(e).__name__}")

def _totali(rs):
    return {r["misura"]: round(r["con_traffico_s"] / 60) for r in rs if r["esito"] == "ok"}

def giro(adesso, env, pubblico, privato, chiama=fonti.http):
    locale = adesso.astimezone(ZURIGO)
    quarto = locale.replace(minute=locale.minute // 15 * 15, second=0, microsecond=0)
    ora, ora_utc = f"{quarto:%Y-%m-%d %H:%M}", f"{adesso.astimezone(timezone.utc):%Y-%m-%dT%H:%MZ}"
    un_ora_fa = f"{quarto - timedelta(hours=1):%Y-%m-%d %H:%M}"
    dell_ora = quarto.minute == 0
    os.makedirs(privato, exist_ok=True)
    p_uso = os.path.join(privato, "uso.json")
    uso = json.load(open(p_uso)) if os.path.exists(p_uso) else {}
    cartella = lambda fonte: os.path.join(pubblico if fonte in PUBBLICHE else privato, "dati")
    attiva = lambda fonte: bool(env.get(CHIAVI[fonte]))
    misurate = {}

    def conta(fonte, quanto):
        """Il conteggio si salva subito: se il giro si rompe dopo, le richieste fatte restano contate."""
        registra(uso, fonte, quanto, quarto)
        json.dump(uso, open(p_uso, "w"), indent=1, sort_keys=True)

    def percorsi(fonte, richieste, funzione):
        if not attiva(fonte) or (fonte in ORARIE and not dell_ora):
            return
        try:
            if consenti(uso, fonte, richieste, quarto):
                conta(fonte, richieste)
                rs = [controlla_distanza(r) for r in _sicura(funzione)]
            else:
                rs = _tutte("quota esaurita")
            aggiungi_in_cima(file_mese(cartella(fonte), fonte, quarto), INTESTAZIONE, [riga_sintetica(ora, rs)])
            aggiungi_in_cima(file_mese(cartella(fonte), fonte, quarto, "-dettaglio"), INTESTAZIONE_DETTAGLIO, righe_dettaglio(ora, ora_utc, rs))
            misurate[fonte] = rs
            print(fonte, sum(r["esito"] == "ok" for r in rs), "/", len(rs), "ok")
        except Exception as e:                                   # una fonte rotta non ferma le altre; solo il tipo, mai il messaggio
            print(fonte, "errore", type(e).__name__)

    def apple():
        token = fonti.token_apple(env["APPLE_MAPS_KEY_ID"], env["APPLE_TEAM_ID"], env["APPLE_MAPS_PRIVATE_KEY"], chiama)
        return fonti.apple(token, chiama) if token else _tutte("errore token")

    percorsi("apple", len(fonti.richieste_apple()), apple)
    percorsi("tomtom", len(MISURE), lambda: fonti.tomtom(env["TOMTOM_KEY"], chiama))
    percorsi("google", len(MISURE), lambda: fonti.google(env["GOOGLE_ROUTES_KEY"], chiama))

    for fonte, costo, funzione in (("openwebninja", 1, fonti.waze_openwebninja), ("apify", COSTO_APIFY, fonti.waze_apify)):
        if not attiva(fonte) or not dell_ora:
            continue
        try:
            if not consenti(uso, fonte, costo, quarto):
                righe, esito = None, "quota esaurita"
            else:
                conta(fonte, costo)
                try:
                    righe, esito = funzione(env[CHIAVI[fonte]], chiama)
                except Exception as e:
                    righe, esito = None, f"errore {type(e).__name__}"
            # Una riga «vuota» con l'esito (nella colonna tipo) quando non arriva niente: così il buco si vede nel file.
            dati = ([[ora] + ["" if r[k] is None else r[k] for k in CAMPI_WAZE] for r in righe] if righe
                    else [[ora, "nessuna coda" if righe == [] else esito] + [""] * (len(CAMPI_WAZE) - 1)])
            aggiungi_in_cima(file_mese(os.path.join(privato, "dati"), f"waze-{fonte}", quarto), ["ora"] + CAMPI_WAZE, dati)
            print(fonte, esito, len(righe or []), "righe")
        except Exception as e:
            print(fonte, "errore", type(e).__name__)

    json.dump(uso, open(p_uso, "w"), indent=1, sort_keys=True)

    # Mappe del quarto d'ora, una per fonte attiva. Le fonti orarie, tra un'ora e l'altra, mostrano l'ultima misura.
    for fonte in ("apple", "tomtom", "google"):
        if not attiva(fonte):
            continue
        try:
            if fonte in misurate:
                rs = misurate[fonte]
                svg = mappa_fonte(fonte, quarto, dict(zip(INTESTAZIONE, riga_sintetica(ora, rs))), _totali(rs), ora_misura=ora)
            else:
                ultime = [r for r in ultime_24h(cartella(fonte), fonte, quarto) if r["ora"] > un_ora_fa]
                svg = (mappa_fonte(fonte, quarto, ultime[0], ultimi_totali(cartella(fonte), fonte, quarto), ora_misura=ultime[0]["ora"])
                       if ultime else mappa_fonte(fonte, quarto))
            _scrivi(privato, nome_mappa(quarto, fonte), svg)
        except Exception as e:
            print("mappa", fonte, "errore", type(e).__name__)
    for fonte in ("openwebninja", "apify"):
        if not attiva(fonte):
            continue
        try:
            righe, ora_misura = _ultime_waze(privato, fonte, quarto, un_ora_fa)
            svg = (mappa_fonte(fonte, quarto, code_waze=[r for r in righe if r["tipo"] == "coda"], ora_misura=ora_misura)
                   if ora_misura else mappa_fonte(fonte, quarto))
            _scrivi(privato, nome_mappa(quarto, fonte), svg)
        except Exception as e:
            print("mappa", fonte, "errore", type(e).__name__)

    _togli_mappe_vecchie(privato, quarto)
    for percorso, testo in pagine(quarto, lambda m: os.path.exists(os.path.join(privato, m))).items():
        _scrivi(privato, percorso, testo)

def _ultime_waze(privato, fonte, quarto, un_ora_fa):
    """Righe dell'ultimo rilevamento Waze dell'ultima ora (con la sua ora), oppure ([], None)."""
    p = file_mese(os.path.join(privato, "dati"), f"waze-{fonte}", quarto)
    if not os.path.exists(p):
        return [], None
    with open(p, newline="", encoding="utf-8") as f:
        tutte = list(csv.DictReader(f))
    if not tutte or tutte[0]["ora"] <= un_ora_fa:
        return [], None
    ultima = tutte[0]["ora"]
    if tutte[0]["tipo"] not in ("coda", "segnalazione", "nessuna coda"):
        return [], None                                               # l'ultimo rilevamento è fallito
    return [r for r in tutte if r["ora"] == ultima], ultima

def _togli_mappe_vecchie(privato, quarto):
    """Le pagine arrivano a 3 ore fa: le mappe più vecchie non servono più."""
    limite = f"{quarto - timedelta(minutes=15 * (PASSI_STORIA - 1)):%Y-%m-%d-%H%M}"
    cartella = os.path.join(privato, "mappe")
    for nome in os.listdir(cartella) if os.path.isdir(cartella) else []:
        m = re.match(r"^(\d{4}-\d{2}-\d{2}-\d{4})-[a-z]+\.svg$", nome)
        if m and m.group(1) < limite:
            os.remove(os.path.join(cartella, nome))

def _scrivi(radice, percorso, testo):
    p = os.path.join(radice, percorso)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(testo)

if __name__ == "__main__":
    # Il log delle Actions è pubblico: in caso di errore si stampa solo il tipo, mai messaggio né traccia.
    try:
        giro(datetime.now(timezone.utc), dict(os.environ), ".", "privati")
    except Exception as e:
        print("giro fallito:", type(e).__name__)
        raise SystemExit(1)
