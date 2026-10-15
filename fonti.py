# Chiamate alle fonti. Mai un URL o una risposta grezza nei messaggi: contengono chiavi.
import base64, json, time, urllib.error, urllib.request
from config import MISURE, PUNTI, VALICO
from archivio import risultato

def http(metodo, url, intestazioni=None, corpo=None):
    dati = json.dumps(corpo).encode() if corpo is not None else None
    req = urllib.request.Request(url, data=dati, method=metodo, headers=dict(intestazioni or {}))
    if dati:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            testo = r.read()
            return r.status, (json.loads(testo) if testo else None)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"null")
        except ValueError:
            return e.code, None
    except Exception:
        return 0, None

def pem(testo):
    """La casella dei segreti può perdere gli a capo del .p8: si ricostruisce il PEM dal corpo."""
    corpo = "".join(testo.replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "").split())
    righe = [corpo[i:i + 64] for i in range(0, len(corpo), 64)]
    return "-----BEGIN PRIVATE KEY-----\n" + "\n".join(righe) + "\n-----END PRIVATE KEY-----\n"

def token_apple(key_id, team_id, chiave, chiama=http):
    """JWT ES256 firmato con la chiave Maps, scambiato con un token d'accesso (30 min)."""
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec, utils
    b64 = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=").decode()
    adesso = int(time.time())
    testa = b64(json.dumps({"alg": "ES256", "kid": key_id, "typ": "JWT"}).encode())
    carico = b64(json.dumps({"iss": team_id, "iat": adesso, "exp": adesso + 1800}).encode())
    privata = serialization.load_pem_private_key(pem(chiave).encode(), password=None)
    r, s = utils.decode_dss_signature(privata.sign(f"{testa}.{carico}".encode(), ec.ECDSA(hashes.SHA256())))
    jwt = f"{testa}.{carico}.{b64(r.to_bytes(32, 'big') + s.to_bytes(32, 'big'))}"
    codice, d = chiama("GET", "https://maps-api.apple.com/v1/token", {"Authorization": "Bearer " + jwt})
    return d.get("accessToken") if codice == 200 and isinstance(d, dict) else None

def unisci(nome, a, b):
    """Passo = salita al valico + discesa. Se una tratta manca, manca la misura: mai un tempo a metà."""
    for tratta in (a, b):
        if tratta["esito"] != "ok":
            return {**tratta, "misura": nome}
    return risultato(nome, a["con_traffico_s"] + b["con_traffico_s"], a["senza_traffico_s"] + b["senza_traffico_s"],
                     a["distanza_m"] + b["distanza_m"])

def componi(nome, origine, destinazione, percorso, tratte):
    if percorso == "tunnel":
        return {**tratte[(origine, destinazione)], "misura": nome}
    return unisci(nome, tratte[(origine, VALICO)], tratte[(VALICO, destinazione)])

def coppie_apple():
    """Origine → destinazioni per le otto misure: 5 richieste a giro (l'API accetta fino a 10 destinazioni)."""
    tratte = set()
    for _, o, d, percorso in MISURE:
        tratte |= {(o, d)} if percorso == "tunnel" else {(o, VALICO), (VALICO, d)}
    per_origine = {}
    for o, d in sorted(tratte):
        per_origine.setdefault(o, []).append(d)
    return per_origine

def _vicino(a, b):
    return abs(a[0] - b[0]) < 0.01 and abs(a[1] - b[1]) < 0.01

def apple(token, chiama=http):
    tratte = {}
    for o, destinazioni in coppie_apple().items():
        q = "origin=%s,%s&destinations=%s&transportType=Automobile" % (*PUNTI[o], "|".join("%s,%s" % PUNTI[d] for d in destinazioni))
        codice, r = chiama("GET", "https://maps-api.apple.com/v1/etas?" + q, {"Authorization": "Bearer " + token})
        for d in destinazioni:
            if codice != 200 or not isinstance(r, dict):
                tratte[(o, d)] = risultato("", esito=f"errore {codice}")
                continue
            # Abbinamento per coordinate, non per posizione: una destinazione irraggiungibile può mancare.
            e = next((e for e in r.get("etas", []) if _vicino((e["destination"]["latitude"], e["destination"]["longitude"]), PUNTI[d])), None)
            tratte[(o, d)] = (risultato("", e["expectedTravelTimeSeconds"], e["staticTravelTimeSeconds"], e["distanceMeters"])
                              if e else risultato("", esito="percorso non trovato"))
    return [componi(nome, o, d, p, tratte) for nome, o, d, p in MISURE]

def _luogo(tappe):
    return ":".join("%s,%s" % PUNTI[t] for t in tappe)

def da_tomtom(nome, codice, r):
    if codice == 200 and isinstance(r, dict) and r.get("routes"):
        s = r["routes"][0]["summary"]
        return risultato(nome, s["travelTimeInSeconds"], s["noTrafficTravelTimeInSeconds"], s["lengthInMeters"])
    if codice == 400 and "NO_ROUTE_FOUND" in json.dumps(r or {}):
        return risultato(nome, esito="percorso non trovato")
    return risultato(nome, esito=f"errore {codice}")

def tomtom(chiave, chiama=http, attesa=time.sleep):
    """Una richiesta per misura; il passo con il punto del valico come tappa.
    Il piano gratuito rifiuta con 429 le richieste troppo ravvicinate (15.10.2026: le ultime 3 di 8):
    si lascia una pausa tra le richieste e dopo un 429 si riprova, al massimo due volte."""
    out = []
    for nome, o, d, percorso in MISURE:
        tappe = [o, VALICO, d] if percorso == "passo" else [o, d]
        for tentativo in range(3):
            attesa(0.3 if tentativo == 0 else 1.5)
            codice, r = chiama("GET", f"https://api.tomtom.com/routing/1/calculateRoute/{_luogo(tappe)}/json"
                                      f"?traffic=true&computeTravelTimeFor=all&travelMode=car&key={chiave}")
            if codice != 429:
                break
        out.append(da_tomtom(nome, codice, r))
    return out

def _punto(n):
    return {"location": {"latLng": {"latitude": PUNTI[n][0], "longitude": PUNTI[n][1]}}}

def da_google(nome, codice, r):
    if codice != 200:
        return risultato(nome, esito=f"errore {codice}")
    if not isinstance(r, dict) or not r.get("routes"):
        return risultato(nome, esito="percorso non trovato")
    x = r["routes"][0]
    return risultato(nome, int(x["duration"].rstrip("s")), int(x["staticDuration"].rstrip("s")), x["distanceMeters"])

def google(chiave, chiama=http):
    """Chiave nell'intestazione, mai nell'URL. Il passo con il punto del valico come tappa obbligata (via)."""
    out = []
    for nome, o, d, percorso in MISURE:
        corpo = {"origin": _punto(o), "destination": _punto(d), "travelMode": "DRIVE", "routingPreference": "TRAFFIC_AWARE"}
        if percorso == "passo":
            corpo["intermediates"] = [{**_punto(VALICO), "via": True}]
        codice, r = chiama("POST", "https://routes.googleapis.com/directions/v2:computeRoutes",
                           {"X-Goog-Api-Key": chiave, "X-Goog-FieldMask": "routes.duration,routes.staticDuration,routes.distanceMeters"}, corpo)
        out.append(da_google(nome, codice, r))
    return out

from config import AREA_WAZE

CAMPI_WAZE = ["tipo", "sottotipo", "strada", "citta", "lunghezza_m", "velocita_kmh", "livello", "ritardo_s", "lat", "lon", "id"]

def _riga(**campi):
    return {k: campi.get(k) for k in CAMPI_WAZE}

def _coda(j):
    inizio = (j.get("line_coordinates") or [{}])[0]
    return _riga(tipo="coda", sottotipo=j.get("block_alert_type") or j.get("type") or "", strada=j.get("street") or "",
                 citta=j.get("city") or "", lunghezza_m=j.get("length_meters"), velocita_kmh=j.get("speed_kmh"),
                 livello=j.get("level"), ritardo_s=j.get("delay_seconds"), lat=inizio.get("lat"), lon=inizio.get("lon"), id=j.get("jam_id"))

def _segnalazione(a):
    return _riga(tipo="segnalazione", sottotipo=a.get("subtype") or a.get("type") or "", strada=a.get("street") or "",
                 citta=a.get("city") or "", lat=a.get("latitude"), lon=a.get("longitude"), id=a.get("alert_id"))

def righe_openwebninja(r):
    d = r.get("data", r) if isinstance(r, dict) else {}
    return [_coda(j) for j in d.get("jams", [])] + [_segnalazione(a) for a in d.get("alerts", [])]

def riga_apify(x):
    """Apify restituisce gli stessi campi di OpenWeb Ninja, un elemento per riga con recordType «jam» o «alert»."""
    return _coda(x) if x.get("recordType") == "jam" else _segnalazione(x)

def waze_openwebninja(chiave, chiama=http):
    bl, tr = AREA_WAZE
    codice, r = chiama("GET", f"https://api.openwebninja.com/waze/alerts-and-jams?bottom_left={bl}&top_right={tr}&max_alerts=200&max_jams=800",
                       {"x-api-key": chiave})
    return (righe_openwebninja(r), "ok") if codice == 200 and isinstance(r, dict) else (None, f"errore {codice}")

def waze_apify(token, chiama=http):
    bl, tr = AREA_WAZE
    codice, r = chiama("POST", "https://api.apify.com/v2/acts/sian.agency~waze-traffic-scraper/run-sync-get-dataset-items?memory=256",
                       {"Authorization": "Bearer " + token},
                       {"operation": "alertsAndJams", "bottomLeft": bl, "topRight": tr, "maxAlerts": 100, "maxJams": 100})
    return ([riga_apify(x) for x in r], "ok") if codice in (200, 201) and isinstance(r, list) else (None, f"errore {codice}")
