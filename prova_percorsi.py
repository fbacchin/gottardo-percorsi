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

if __name__ == "__main__":
    prove = [(n, f) for n, f in sorted(globals().items()) if n.startswith("prova_") and callable(f)]
    falliti = 0
    for nome, f in prove:
        try: f(); print("ok  ", nome)
        except Exception: falliti += 1; print("NO  ", nome); traceback.print_exc()
    print(f"{len(prove) - falliti}/{len(prove)}")
    sys.exit(1 if falliti else 0)
