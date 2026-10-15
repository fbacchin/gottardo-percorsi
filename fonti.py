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
