# Banco di prova di gottardo-percorsi. Uso: python3 prova_percorsi.py
# Ogni funzione prova_* è una prova; i campioni sono risposte VERE delle fonti.
import sys, traceback

def prova_misure():
    from config import MISURE, PUNTI, VALICO
    assert len(MISURE) == 8 and len({m[0] for m in MISURE}) == 8
    for nome, o, d, percorso in MISURE:
        assert o in PUNTI and d in PUNTI and percorso in ("tunnel", "passo")
        assert nome.startswith("NS " if PUNTI[o][0] > PUNTI[d][0] else "SN ")   # nord = latitudine maggiore
    assert VALICO in PUNTI

import os, tempfile, csv
from datetime import datetime, timedelta, timezone

def prova_ritardo_ed_esiti():
    from archivio import risultato, ritardo_min, controlla_distanza
    assert ritardo_min(risultato("x", 3900, 3180, 83000)) == 12
    assert ritardo_min(risultato("x", 3000, 3180, 83000)) == -3          # di notte si scrive com'è
    assert ritardo_min(risultato("x", esito="percorso non trovato")) is None
    rif = {"x": 83000}
    assert controlla_distanza(risultato("x", 3900, 3180, 84000), rif)["esito"] == "ok"
    assert controlla_distanza(risultato("x", 3900, 3180, 97000), rif)["esito"] == "percorso diverso"
    assert ritardo_min(controlla_distanza(risultato("x", 3900, 3180, 97000), rif)) is None   # mai un tempo della strada sbagliata
    assert controlla_distanza(risultato("x", 3900, 3180, 97000), {})["esito"] == "ok"        # senza riferimento, nessun controllo

def prova_riga_sintetica():
    from archivio import risultato, riga_sintetica, INTESTAZIONE
    from config import MISURE
    rs = [risultato(m[0], 3600 + 60 * i, 3600, 80000) for i, m in enumerate(MISURE)]
    rs[1] = risultato(MISURE[1][0], esito="percorso non trovato")
    riga = riga_sintetica("2026-10-16 17:15", rs)
    assert len(riga) == len(INTESTAZIONE) and INTESTAZIONE[0] == "ora" and INTESTAZIONE[-1] == "esito"
    assert riga[0] == "2026-10-16 17:15" and riga[1] == 0 and riga[2] == "" and riga[3] == 2
    assert riga[-1] == f"{MISURE[1][0]}: percorso non trovato"
    assert riga_sintetica("t", [risultato(m[0], 60, 60, 1) for m in MISURE])[-1] == "ok"

def prova_scrittura_in_cima_e_mese():
    from archivio import aggiungi_in_cima, file_mese, ultime_24h, INTESTAZIONE
    from config import ZURIGO
    with tempfile.TemporaryDirectory() as d:
        ott = datetime(2026, 10, 31, 23, 45, tzinfo=ZURIGO)
        p = file_mese(d, "apple", ott)
        assert p.endswith("apple-2026-10.csv")
        assert file_mese(d, "apple", ott + timedelta(minutes=15)).endswith("apple-2026-11.csv")
        vuota = [""] * (len(INTESTAZIONE) - 2)
        for ora in ("2026-10-31 23:15", "2026-10-31 23:30", "2026-10-31 23:45"):
            aggiungi_in_cima(p, INTESTAZIONE, [[ora] + vuota + ["ok"]])
        righe = list(csv.reader(open(p, encoding="utf-8")))
        assert righe[0] == INTESTAZIONE
        assert [r[0] for r in righe[1:]] == ["2026-10-31 23:45", "2026-10-31 23:30", "2026-10-31 23:15"]
        # ultime 24 ore attraverso il cambio di mese: legge anche il file del mese prima
        nov = datetime(2026, 11, 1, 0, 15, tzinfo=ZURIGO)
        aggiungi_in_cima(file_mese(d, "apple", nov), INTESTAZIONE, [["2026-11-01 00:15"] + vuota + ["ok"]])
        assert [r["ora"] for r in ultime_24h(d, "apple", nov)] == ["2026-11-01 00:15", "2026-10-31 23:45", "2026-10-31 23:30", "2026-10-31 23:15"]

def prova_quote():
    from archivio import consenti, registra
    from config import ZURIGO
    uso, ott = {}, datetime(2026, 10, 20, 12, 0, tzinfo=ZURIGO)
    for _ in range(95):
        assert consenti(uso, "openwebninja", 1, ott); registra(uso, "openwebninja", 1, ott)
    assert not consenti(uso, "openwebninja", 1, ott)                       # tetto raggiunto
    assert consenti(uso, "openwebninja", 1, datetime(2026, 11, 1, 0, 0, tzinfo=ZURIGO))   # mese nuovo
    for _ in range(108): registra(uso, "apify", 0.041, ott)               # 4,428 $
    assert consenti(uso, "apify", 0.041, ott) is True and (registra(uso, "apify", 0.041, ott) or True)
    assert not consenti(uso, "apify", 0.041, ott)                          # 4,51 $ > 4,50 $
    registra(uso, "tomtom", 2000, ott)
    assert not consenti(uso, "tomtom", 8, ott) and consenti(uso, "tomtom", 8, ott + timedelta(days=1))   # tetto giornaliero
    assert consenti(uso, "apple", 5, ott)                                  # nessun tetto

import json as _json
def _campione(nome):
    return _json.load(open(nome, encoding="utf-8"))

def prova_pem_su_una_riga():
    from fonti import pem
    corpo = "MIGTAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBHkwdwIBAQQg" + "A" * 80
    completo = pem(corpo)
    assert completo.startswith("-----BEGIN PRIVATE KEY-----\n") and completo.endswith("-----END PRIVATE KEY-----\n")
    assert pem(completo) == completo and pem(completo.replace("\n", " ")) == completo

def prova_apple_coppie():
    from fonti import richieste_apple
    r = richieste_apple()
    assert len(r) == 9 and sum(len(d) for _, d in r) == 12 and all(len(d) <= 10 for _, d in r)

def prova_apple_campione():
    from fonti import apple
    from config import MISURE, PUNTI
    c = _campione("privati/campioni/apple-etas.json")
    origine = "origin=%s,%s" % PUNTI["Erstfeld"]
    chiama = lambda metodo, url, intestazioni=None, corpo=None: (c["codice"], c["risposta"]) if origine in url else (200, {"etas": []})
    rs = apple("t", chiama)
    assert [r["misura"] for r in rs] == [m[0] for m in MISURE]
    tunnel = [r for r in rs if r["misura"] == "NS Erstfeld-Biasca tunnel"][0]   # nel campione
    assert tunnel["esito"] == "ok" and tunnel["con_traffico_s"] >= tunnel["senza_traffico_s"] > 0 and tunnel["distanza_m"] > 50000
    per_nome = {r["misura"]: r for r in rs}
    assert per_nome["NS Erstfeld-Biasca passo"]["esito"] == "percorso non trovato"   # manca Passo→Biasca: mai un tempo a metà
    assert per_nome["SN Biasca-Erstfeld tunnel"]["esito"] == "percorso non trovato"

def prova_apple_errore():
    from fonti import apple
    rs = apple("t", lambda *a, **k: (503, None))
    assert all(r["esito"] == "errore 503" and r["con_traffico_s"] is None for r in rs)

def prova_tomtom_campioni():
    from fonti import da_tomtom
    t = _campione("privati/campioni/tomtom-tunnel.json"); p = _campione("privati/campioni/tomtom-passo.json")
    rt, rp = da_tomtom("a", t["codice"], t["risposta"]), da_tomtom("b", p["codice"], p["risposta"])
    assert rt["esito"] == rp["esito"] == "ok" and rp["distanza_m"] > rt["distanza_m"] + 8000
    assert da_tomtom("c", 400, {"detailedError": {"code": "NO_ROUTE_FOUND"}})["esito"] == "percorso non trovato"
    assert da_tomtom("c", 403, None)["esito"] == "errore 403"

def prova_tomtom_otto_misure():
    from fonti import tomtom
    from config import MISURE
    rs = tomtom("k", lambda *a, **k: (500, None))
    assert [r["misura"] for r in rs] == [m[0] for m in MISURE] and all(r["esito"] == "errore 500" for r in rs)

def prova_google_campioni():
    from fonti import da_google
    t = _campione("privati/campioni/google-tunnel.json"); p = _campione("privati/campioni/google-passo.json")
    rt, rp = da_google("a", t["codice"], t["risposta"]), da_google("b", p["codice"], p["risposta"])
    assert rt["esito"] == rp["esito"] == "ok" and isinstance(rt["con_traffico_s"], int) and rp["distanza_m"] > rt["distanza_m"] + 8000
    assert da_google("c", 200, {})["esito"] == "percorso non trovato"
    assert da_google("c", 429, None)["esito"] == "errore 429"

def prova_google_otto_misure():
    from fonti import google
    from config import MISURE
    rs = google("k", lambda *a, **k: (500, None))
    assert [r["misura"] for r in rs] == [m[0] for m in MISURE] and all(r["esito"] == "errore 500" for r in rs)

def prova_waze_campioni():
    from fonti import righe_openwebninja, riga_apify, CAMPI_WAZE
    o = _campione("privati/campioni/openwebninja.json")["risposta"]
    a = _campione("privati/campioni/apify.json")["risposta"]
    for righe in (righe_openwebninja(o), [riga_apify(x) for x in a]):
        assert righe, "nessuna riga: area vuota o nomi dei campi sbagliati"
        assert all(set(r) == set(CAMPI_WAZE) for r in righe)
        assert all(r["tipo"] in ("coda", "segnalazione") for r in righe)
        assert all(isinstance(r["lat"], (int, float)) and 46.3 < r["lat"] < 46.9 for r in righe)   # dentro l'area
        code = [r for r in righe if r["tipo"] == "coda"]
        assert code and all(r["lunghezza_m"] is not None and r["id"] for r in code)

def prova_waze_errori():
    from fonti import waze_openwebninja, waze_apify
    assert waze_openwebninja("k", lambda *a, **k: (429, None)) == (None, "errore 429")
    assert waze_apify("k", lambda *a, **k: (402, {"error": "x"})) == (None, "errore 402")

def prova_pallini():
    from pagina import pallino
    assert [pallino(v) for v in ("", "0", "-2", "1", "9", "10", "39", "40", "120")] == ["⚪", "🟢", "🟢", "🟡", "🟡", "🟠", "🟠", "🔴", "🔴"]

def prova_tempi_totali():
    from archivio import aggiungi_in_cima, file_mese, righe_dettaglio, risultato, ultimi_totali, INTESTAZIONE_DETTAGLIO
    from config import MISURE, ZURIGO
    adesso = datetime(2026, 10, 16, 17, 15, tzinfo=ZURIGO)
    with tempfile.TemporaryDirectory() as d:
        p = file_mese(d, "apple", adesso, "-dettaglio")
        vecchi = [risultato(m[0], 3000, 2900, 75000) for m in MISURE]
        nuovi = [risultato(m[0], 3840, 3120, 75000) for m in MISURE]
        nuovi[1] = risultato(MISURE[1][0], esito="errore 503")
        aggiungi_in_cima(p, INTESTAZIONE_DETTAGLIO, righe_dettaglio("2026-10-16 17:00", "x", vecchi))
        aggiungi_in_cima(p, INTESTAZIONE_DETTAGLIO, righe_dettaglio("2026-10-16 17:15", "x", nuovi))
        totali = ultimi_totali(d, "apple", adesso)
        assert totali[MISURE[0][0]] == 64 and MISURE[1][0] not in totali     # solo l'ultimo giro, senza le misure fallite

def prova_situazione():
    from pagina import situazione
    from config import MISURE
    riga = {m[0]: "0" for m in MISURE}
    riga.update({"SN Biasca-Erstfeld tunnel": "58", "SN Faido-Amsteg tunnel": "50", "SN Faido-Amsteg passo": "6", "NS Amsteg-Faido tunnel": ""})
    s = situazione({"apple": riga})
    assert s[("SN", "tunnel")] == 50 and s[("SN", "esterni")] == 8 and s[("SN", "passo")] == 6
    assert s[("NS", "tunnel")] is None and s[("NS", "esterni")] is None       # manca il centro: niente differenza inventata
    assert situazione({}) == {k: None for k in s}                               # fonte assente: tutto grigio

def prova_waze_posizione_e_senso():
    from pagina import _senso_waze, _x_da_lat, X, LAT, RAMO_PASSO
    assert _senso_waze("A2 > Zürich / Luzern / San Gottardo") == "SN" and _senso_waze("A2 > Chiasso / Lugano") == "NS"
    assert _senso_waze("Via Cantonale") is None
    corridoio = [(la, X[n]) for n, la in LAT]
    assert _x_da_lat(46.672, corridoio) == X["Göschenen"] and X["Göschenen"] < _x_da_lat(46.60, corridoio) < X["Airolo"]
    assert _x_da_lat(47.10, corridoio) is None                                  # fuori dalla strada: non si disegna
    assert _x_da_lat(46.5588, RAMO_PASSO) == RAMO_PASSO[2][1]

def prova_corsie_parallele():
    from pagina import _parallela
    assert _parallela([(0, 0), (10, 0)], 14) == [(0, 14), (10, 14)]
    assert [tuple(round(v, 6) for v in p) for p in _parallela([(0, 0), (10, 0), (10, 10)], 2)] == [(0, 2), (8, 2), (8, 10)]

def prova_mappe_per_fonte():
    from pagina import mappa_fonte
    from config import MISURE, ZURIGO
    q = datetime(2026, 10, 18, 15, 15, tzinfo=ZURIGO)
    riga = {m[0]: "12" for m in MISURE}
    svg = mappa_fonte("google", q, riga, {"NS Erstfeld-Biasca tunnel": 64}, ora_misura="2026-10-18 15:00")
    assert "Google — 15:15" in svg and "misura delle 2026-10-18 15:00" in svg and "+12 min · totale 64 min" in svg and "#ff6f00" in svg
    assert "misura delle" not in mappa_fonte("apple", q, riga, ora_misura="2026-10-18 15:15")
    assert "nessun dato in questo quarto d'ora" in mappa_fonte("tomtom", q)
    coda = {"strada": "A2 > Zürich", "lat": 46.50, "lon": 8.66, "lunghezza_m": 2100, "livello": 4}
    w = mappa_fonte("apify", q, code_waze=[coda])
    assert "1 coda segnalata da Waze" in w and "Waze 2,1 km" in w and "#c62828" in w
    assert "nessuna coda segnalata da Waze" in mappa_fonte("openwebninja", q, code_waze=[])

def prova_pagine_e_link():
    from pagina import pagine, nome_mappa, PASSI_STORIA
    from config import ZURIGO
    adesso = datetime(2026, 10, 18, 15, 0, tzinfo=ZURIGO)
    p = pagine(adesso, lambda m: "-apify" not in m)                              # mappe Apify mancanti
    assert set(p) == {"README.md"} | {f"storia/{15 * k}.md" for k in range(1, PASSI_STORIA)}
    assert "[◀ 15 minuti prima](storia/15.md)" in p["README.md"] and "15 minuti dopo" not in p["README.md"]
    assert f"![Apple Maps]({nome_mappa(adesso, 'apple')})" in p["README.md"]
    s15 = p["storia/15.md"]
    assert "[◀ 15 minuti prima](30.md)" in s15 and "[15 minuti dopo ▶](../README.md)" in s15 and "[Adesso](../README.md)" in s15
    assert "](../mappe/2026-10-18-1445-apple.svg)" in s15 and "_nessuna mappa per questo quarto d'ora_" in s15
    ultima = p[f"storia/{15 * (PASSI_STORIA - 1)}.md"]
    assert "15 minuti prima" not in ultima and f"[15 minuti dopo ▶]({15 * (PASSI_STORIA - 2)}.md)" in ultima

import io, contextlib, glob, json

SEGRETI_FINTI = {"APPLE_MAPS_KEY_ID": "SEGRETO-KID", "APPLE_TEAM_ID": "SEGRETO-TEAM", "APPLE_MAPS_PRIVATE_KEY": "SEGRETO-PEM",
                 "TOMTOM_KEY": "SEGRETO-TOMTOM", "GOOGLE_ROUTES_KEY": "SEGRETO-GOOGLE", "OPENWEBNINJA_KEY": "SEGRETO-OWN", "APIFY_TOKEN": "SEGRETO-APIFY"}

def _giro_finto(adesso, chiama, env=SEGRETI_FINTI, d=None):
    from giro import giro
    d = d or tempfile.mkdtemp()
    pub, priv = os.path.join(d, "pub"), os.path.join(d, "priv")
    uscita = io.StringIO()
    with contextlib.redirect_stdout(uscita), contextlib.redirect_stderr(uscita):
        giro(adesso, env, pub, priv, chiama)
    return pub, priv, uscita.getvalue()

def _tutti_i_file(*cartelle):
    return "".join(open(p, encoding="utf-8").read() for c in cartelle for p in glob.glob(c + "/**/*", recursive=True) if os.path.isfile(p))

def prova_giro_segreti_mai_in_uscita():
    from config import ZURIGO
    def chiama_che_fallisce(metodo, url, intestazioni=None, corpo=None):
        raise RuntimeError("errore con dentro " + url + str(intestazioni))   # il caso peggiore: un'eccezione che si porta dietro l'URL
    pub, priv, uscita = _giro_finto(datetime(2026, 10, 16, 17, 0, tzinfo=ZURIGO), chiama_che_fallisce)
    tutto = uscita + _tutti_i_file(pub, priv)
    assert not any(s in tutto for s in SEGRETI_FINTI.values()), "un segreto è finito in uscita o nei file"

def prova_giro_cosa_e_dove():
    from config import ZURIGO
    risposte = lambda metodo, url, intestazioni=None, corpo=None: (503, None)
    pub, priv, _ = _giro_finto(datetime(2026, 10, 16, 17, 16, 30, tzinfo=ZURIGO), risposte, {"TOMTOM_KEY": "k", "GOOGLE_ROUTES_KEY": "g"})
    assert os.path.exists(f"{priv}/dati/tomtom-2026-10.csv") and os.path.exists(f"{priv}/dati/tomtom-2026-10-dettaglio.csv")
    assert "2026-10-16 17:15" in open(f"{priv}/dati/tomtom-2026-10.csv", encoding="utf-8").read()   # ora del quarto d'ora
    assert not glob.glob(f"{priv}/dati/apple-*")                               # senza chiave la fonte non gira
    assert not glob.glob(f"{priv}/dati/google-*")                              # :15, non è il giro dell'ora
    assert not os.path.exists(pub) or not _tutti_i_file(pub)                   # nel pubblico non si scrive niente
    assert os.path.exists(f"{priv}/mappe/2026-10-16-1715-tomtom.svg") and not glob.glob(f"{priv}/mappe/*-apple.svg")
    assert os.path.exists(f"{priv}/README.md") and os.path.exists(f"{priv}/storia/15.md")
    pub, priv, _ = _giro_finto(datetime(2026, 10, 16, 18, 0, tzinfo=ZURIGO), risposte, {"GOOGLE_ROUTES_KEY": "g", "OPENWEBNINJA_KEY": "o"})
    assert os.path.exists(f"{priv}/dati/google-2026-10.csv") and os.path.exists(f"{priv}/dati/waze-openwebninja-2026-10.csv")
    uso = json.load(open(f"{priv}/uso.json"))
    assert uso["google"]["2026-10"] == 8 and uso["openwebninja"]["2026-10"] == 1

def prova_giro_orarie_tra_un_ora_e_l_altra():
    """Alle :15 la mappa di Google e quelle di Waze usano la misura delle :00, con l'ora scritta sotto il titolo."""
    from config import ZURIGO
    c = _campione("privati/campioni/google-tunnel.json")
    w = _campione("privati/campioni/openwebninja.json")
    def risposte(metodo, url, intestazioni=None, corpo=None):
        if "googleapis" in url: return c["codice"], c["risposta"]
        if "openwebninja" in url: return w["codice"], w["risposta"]
        return 503, None
    d = tempfile.mkdtemp()
    env = {"GOOGLE_ROUTES_KEY": "g", "OPENWEBNINJA_KEY": "o"}
    _giro_finto(datetime(2026, 10, 16, 18, 0, tzinfo=ZURIGO), risposte, env, d)
    _, priv, _ = _giro_finto(datetime(2026, 10, 16, 18, 15, tzinfo=ZURIGO), risposte, env, d)
    g = open(f"{priv}/mappe/2026-10-16-1815-google.svg", encoding="utf-8").read()
    assert "misura delle 2026-10-16 18:00" in g and "totale" in g
    o = open(f"{priv}/mappe/2026-10-16-1815-openwebninja.svg", encoding="utf-8").read()
    assert "misura delle 2026-10-16 18:00" in o and "Waze" in o
    assert json.load(open(f"{priv}/uso.json"))["google"]["2026-10"] == 8   # alle :15 Google non è stato chiamato

def prova_giro_cancella_mappe_vecchie():
    from config import ZURIGO
    d = tempfile.mkdtemp(); priv = os.path.join(d, "priv"); os.makedirs(f"{priv}/mappe")
    for nome in ("2026-10-16-1415-apple.svg", "2026-10-16-1430-apple.svg", "appunti.txt"):   # 12 pagine: la più vecchia è 14:30
        open(f"{priv}/mappe/{nome}", "w").write("x")
    _giro_finto(datetime(2026, 10, 16, 17, 15, tzinfo=ZURIGO), lambda *a, **k: (503, None), {"TOMTOM_KEY": "k"}, d)
    rimaste = sorted(os.listdir(f"{priv}/mappe"))
    assert "2026-10-16-1415-apple.svg" not in rimaste and "2026-10-16-1430-apple.svg" in rimaste and "appunti.txt" in rimaste

def prova_giro_quota_esaurita():
    from config import ZURIGO
    from giro import giro
    d = tempfile.mkdtemp(); priv = os.path.join(d, "priv"); os.makedirs(priv)
    json.dump({"google": {"2026-10": 4800}}, open(f"{priv}/uso.json", "w"))
    chiamate = []
    giro(datetime(2026, 10, 16, 18, 0, tzinfo=ZURIGO), {"GOOGLE_ROUTES_KEY": "g"}, os.path.join(d, "pub"), priv,
         lambda *a, **k: chiamate.append(1) or (200, {}))
    assert not chiamate                                                        # nessuna richiesta oltre il tetto
    assert "quota esaurita" in open(f"{priv}/dati/google-2026-10.csv", encoding="utf-8").read()

def prova_tomtom_429_si_riprova():
    """15.10.2026: 8 richieste di fila → le ultime 3 con 429 (troppe al secondo per il piano gratuito)."""
    from fonti import tomtom
    c = _campione("privati/campioni/tomtom-tunnel.json")
    chiamate, pause = [], []
    def chiama(metodo, url, intestazioni=None, corpo=None):
        chiamate.append(url)
        return (429, None) if len(chiamate) in (5, 6) else (c["codice"], c["risposta"])
    rs = tomtom("k", chiama, attesa=pause.append)
    assert all(r["esito"] == "ok" for r in rs) and len(chiamate) == 10       # due 429 riprovati
    assert pause and all(p > 0 for p in pause)
    sempre = tomtom("k", lambda *a, **k: (429, None), attesa=lambda s: None)
    assert all(r["esito"] == "errore 429" for r in sempre)                 # dopo i tentativi si arrende, senza inventare

def prova_riferimenti():
    from config import RIFERIMENTI_M, MISURE
    from archivio import risultato, controlla_distanza
    assert set(RIFERIMENTI_M) == {m[0] for m in MISURE}
    for m in MISURE:
        if m[3] == "passo":
            assert RIFERIMENTI_M[m[0]] > RIFERIMENTI_M[m[0].replace("passo", "tunnel")] * 1.05   # le due strade si distinguono
    # 15.10.2026 17:30, TomTom: «galleria» verso nord sul passo (90,9 km) e «passo» verso sud con 16 km in più (106 km)
    assert controlla_distanza(risultato("SN Biasca-Erstfeld tunnel", 4553, 4434, 90948))["esito"] == "percorso diverso"
    assert controlla_distanza(risultato("NS Erstfeld-Biasca passo", 5363, 5245, 105999))["esito"] == "percorso diverso"
    assert controlla_distanza(risultato("NS Erstfeld-Biasca tunnel", 2928, 2914, 75536))["esito"] == "ok"

def prova_apple_valico_in_richieste_separate():
    """Revisione: col passo chiuso Apple potrebbe rifiutare tutta la richiesta; il valico non va mescolato alle altre destinazioni."""
    from fonti import apple, richieste_apple
    from config import VALICO, MISURE
    for origine, destinazioni in richieste_apple():
        assert VALICO not in destinazioni or destinazioni == [VALICO] or origine == VALICO
    c = _campione("privati/campioni/apple-etas.json")["risposta"]["etas"][0]      # Erstfeld→Biasca
    def chiama(metodo, url, intestazioni=None, corpo=None):
        if "46.5588,8.5621" in url: return 400, {"error": "no route"}           # tutto ciò che tocca il valico
        n = url.split("destinations=")[1].split("&")[0].count("|") + 1
        return 200, {"etas": [{**c, "destination": {"latitude": float(d.split(",")[0]), "longitude": float(d.split(",")[1])}}
                              for d in url.split("destinations=")[1].split("&")[0].split("|")]}
    rs = {r["misura"]: r for r in apple("t", chiama)}
    assert all(rs[m[0]]["esito"] == "ok" for m in MISURE if m[3] == "tunnel")
    assert all(rs[m[0]]["esito"] == "errore 400" for m in MISURE if m[3] == "passo")

def prova_giro_errore_a_meta_conta_le_quote():
    """Revisione: un'eccezione dopo registra() non deve far perdere il conteggio né fermare le altre fonti."""
    from config import ZURIGO
    import fonti
    d = tempfile.mkdtemp()
    vero = fonti.da_google
    from config import RIFERIMENTI_M
    fonti.da_google = lambda nome, codice, r: {"misura": nome, "con_traffico_s": None, "senza_traffico_s": 1,
                                               "distanza_m": RIFERIMENTI_M[nome], "esito": "ok"}   # ok ma senza tempo: TypeError più avanti
    try:
        _, priv, uscita = _giro_finto(datetime(2026, 10, 16, 18, 0, tzinfo=ZURIGO), lambda *a, **k: (503, None),
                                      {"GOOGLE_ROUTES_KEY": "g", "OPENWEBNINJA_KEY": "o"}, d)
    finally:
        fonti.da_google = vero
    uso = json.load(open(f"{priv}/uso.json"))
    assert uso["google"]["2026-10"] == 8 and uso["openwebninja"]["2026-10"] == 1   # contato, e Waze è andato avanti
    assert "google errore TypeError" in uscita and os.path.exists(f"{priv}/README.md")

def prova_waze_coda_senza_coordinate():
    from pagina import mappa_fonte
    from config import ZURIGO
    q = datetime(2026, 10, 18, 15, 15, tzinfo=ZURIGO)
    svg = mappa_fonte("openwebninja", q, code_waze=[{"strada": "A2", "lat": "", "lon": "", "lunghezza_m": "300", "livello": "3"}])
    assert svg.rstrip().endswith("</svg>")                                       # si salta, non si blocca la pagina

if __name__ == "__main__":
    prove = [(n, f) for n, f in sorted(globals().items()) if n.startswith("prova_") and callable(f)]
    falliti = 0
    for nome, f in prove:
        try: f(); print("ok  ", nome)
        except Exception: falliti += 1; print("NO  ", nome); traceback.print_exc()
    print(f"{len(prove) - falliti}/{len(prove)}")
    sys.exit(1 if falliti else 0)
