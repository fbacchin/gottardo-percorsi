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

def richieste_apple():
    """(origine, destinazioni) per le otto misure. Le tratte che toccano il valico vanno in richieste a sé:
    col passo chiuso Apple potrebbe rifiutare l'intera richiesta, e si perderebbero anche le misure della galleria."""
    tunnel, salite, discese = {}, set(), []
    for _, o, d, percorso in MISURE:
        if percorso == "tunnel":
            tunnel.setdefault(o, []).append(d)
        else:
            salite.add(o)
            discese.append(d)
    return ([(o, sorted(set(ds))) for o, ds in sorted(tunnel.items())] + [(o, [VALICO]) for o in sorted(salite)]
            + [(VALICO, sorted(set(discese)))])

def _vicino(a, b):
    return abs(a[0] - b[0]) < 0.01 and abs(a[1] - b[1]) < 0.01

def apple(token, chiama=http):
    tratte = {}
    for o, destinazioni in richieste_apple():
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
