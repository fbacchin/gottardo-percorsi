# Salva una risposta VERA di una fonte come campione per le prove.
# Uso: set -a; source /Users/fabrizio/Xcode/Gotthard/.env; set +a; python3 cattura.py <fonte>
# Stampa solo il codice HTTP e il file scritto. Il token d'accesso di Apple non viene mai salvato.
import json, os, sys
import fonti
from config import PUNTI, VALICO

def salva(percorso, codice, dati):
    os.makedirs(os.path.dirname(percorso), exist_ok=True)
    json.dump({"codice": codice, "risposta": dati}, open(percorso, "w"), ensure_ascii=False, indent=1)
    print(codice, percorso)

if sys.argv[1] == "apple":
    t = fonti.token_apple(os.environ["APPLE_MAPS_KEY_ID"], os.environ["APPLE_TEAM_ID"], os.environ["APPLE_MAPS_PRIVATE_KEY"])
    print("token", "ok" if t else "NON ottenuto")
    if t:
        o, dest = "Erstfeld", ["Biasca", VALICO]
        q = "origin=%s,%s&destinations=%s&transportType=Automobile" % (*PUNTI[o], "|".join("%s,%s" % PUNTI[d] for d in dest))
        salva("privati/campioni/apple-etas.json", *fonti.http("GET", "https://maps-api.apple.com/v1/etas?" + q, {"Authorization": "Bearer " + t}))
