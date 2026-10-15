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
    from fonti import coppie_apple
    c = coppie_apple()
    assert len(c) == 5 and sum(len(v) for v in c.values()) == 12 and all(len(v) <= 10 for v in c.values())

def prova_apple_campione():
    from fonti import apple
    from config import MISURE, PUNTI
    c = _campione("privati/campioni/apple-etas.json")
    origine = "origin=%s,%s" % PUNTI["Erstfeld"]
    chiama = lambda metodo, url, intestazioni=None, corpo=None: (c["codice"], c["risposta"]) if origine in url else (200, {"etas": []})
    rs = apple("t", chiama)
    assert [r["misura"] for r in rs] == [m[0] for m in MISURE]
    tunnel = rs[0]                                               # NS Erstfeld-Biasca tunnel: nel campione
    assert tunnel["esito"] == "ok" and tunnel["con_traffico_s"] >= tunnel["senza_traffico_s"] > 0 and tunnel["distanza_m"] > 50000
    assert rs[1]["esito"] == "percorso non trovato"             # passo: manca Passo→Biasca, mai un tempo a metà
    assert rs[2]["esito"] == "percorso non trovato"

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

if __name__ == "__main__":
    prove = [(n, f) for n, f in sorted(globals().items()) if n.startswith("prova_") and callable(f)]
    falliti = 0
    for nome, f in prove:
        try: f(); print("ok  ", nome)
        except Exception: falliti += 1; print("NO  ", nome); traceback.print_exc()
    print(f"{len(prove) - falliti}/{len(prove)}")
    sys.exit(1 if falliti else 0)
