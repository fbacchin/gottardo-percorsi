// Pagina delle mappe su percorsi.bacchin.app. Legge le mappe dal repository PRIVATO a ogni richiesta
// (token in sola lettura nel segreto GITHUB_TOKEN). Davanti c'è Cloudflare Access con l'email dell'utente.
import { FONTI, mappaValida, momenti, quanto } from "./logica.mjs";

const REPO = "https://api.github.com/repos/fbacchin/gottardo-percorsi-privati/contents/mappe";

function github(env, percorso, accetta) {
  return fetch(REPO + percorso, {
    headers: { Authorization: `Bearer ${env.GITHUB_TOKEN}`, Accept: accetta, "User-Agent": "gottardo-percorsi-sito" },
  });
}

export default {
  async fetch(richiesta, env) {
    // Seconda difesa: senza Access (header messo da Cloudflare) non si serve niente, nemmeno per errore di configurazione.
    // ponytail: si controlla la presenza dell'header, non la firma del JWT di Access; workers.dev è spento in wrangler.toml
    if (!richiesta.headers.get("cf-access-authenticated-user-email")) {
      return new Response("Accesso solo tramite Cloudflare Access.", { status: 403 });
    }
    const url = new URL(richiesta.url);

    if (url.pathname === "/") {
      return new Response(PAGINA, { headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" } });
    }
    if (url.pathname === "/api/momenti") {
      const r = await github(env, "", "application/vnd.github+json");
      if (!r.ok) return Response.json({ errore: r.status }, { status: 502 });
      const elenco = momenti((await r.json()).map((f) => f.name)).map((m, i) => ({ ...m, quanto: quanto(i) }));
      return Response.json({ fonti: FONTI, momenti: elenco }, { headers: { "cache-control": "no-store" } });
    }
    const nome = url.pathname.replace(/^\/mappe\//, "");
    if (url.pathname.startsWith("/mappe/") && mappaValida(nome)) {
      const r = await github(env, "/" + nome, "application/vnd.github.raw");
      if (!r.ok) return new Response("Mappa non trovata", { status: 404 });
      // Le mappe non cambiano più dopo essere state create: si possono tenere in cache.
      return new Response(r.body, { headers: { "content-type": "image/svg+xml", "cache-control": "private, max-age=86400" } });
    }
    return new Response("Non trovato", { status: 404 });
  },
};

const PAGINA = `<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gottardo — traffico</title>
<style>
  :root { --fondo: #eef1f4; --testo: #1d2125; --tenue: #5f6670; --scheda: #ffffff; --bordo: #d9dee4; --accento: #1f5f8b; }
  @media (prefers-color-scheme: dark) { :root { --fondo: #15191d; --testo: #e8ebee; --tenue: #9aa3ad; --scheda: #1f252b; --bordo: #303840; --accento: #7fb6dc; } }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--fondo); color: var(--testo); font: 16px/1.45 -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; }
  header { position: sticky; top: 0; z-index: 1; background: var(--fondo); border-bottom: 1px solid var(--bordo); padding: 12px 16px; }
  .riga { max-width: 1040px; margin: 0 auto; display: flex; flex-wrap: wrap; align-items: center; gap: 8px 16px; }
  h1 { font-size: 15px; font-weight: 600; margin: 0; color: var(--tenue); letter-spacing: .02em; }
  .ora { font-size: 28px; font-weight: 700; font-variant-numeric: tabular-nums; }
  .quanto { color: var(--tenue); }
  nav { margin-left: auto; display: flex; gap: 8px; }
  button { font: inherit; font-size: 15px; padding: 8px 14px; border-radius: 8px; border: 1px solid var(--bordo); background: var(--scheda); color: var(--testo); cursor: pointer; }
  button:disabled { opacity: .4; cursor: default; }
  button:focus-visible { outline: 2px solid var(--accento); outline-offset: 2px; }
  main { max-width: 1040px; margin: 0 auto; padding: 16px; display: grid; gap: 16px; }
  figure { margin: 0; }
  figure img { width: 100%; height: auto; display: block; border-radius: 8px; border: 1px solid var(--bordo); }
  .vuota { padding: 24px 16px; border: 1px dashed var(--bordo); border-radius: 8px; color: var(--tenue); }
  .nota { color: var(--tenue); font-size: 13px; max-width: 1040px; margin: 0 auto; padding: 0 16px 24px; }
</style>
</head>
<body>
<header><div class="riga">
  <div><h1>Gottardo — traffico</h1><span class="ora" id="ora">…</span> <span class="quanto" id="quanto"></span></div>
  <nav>
    <button id="prima" aria-label="15 minuti prima">◀ 15 min prima</button>
    <button id="adesso">Adesso</button>
    <button id="dopo" aria-label="15 minuti dopo">15 min dopo ▶</button>
  </nav>
</div></header>
<main id="mappe"></main>
<p class="nota">Una mappa per fonte. Corsia in alto verso sud, in basso verso nord; tra Göschenen e Airolo la galleria (sopra) e il passo (sotto). Le barre con bordo nero sono code segnalate da Waze. Google e Waze misurano una volta all'ora. La pagina si aggiorna da sola quando arriva un rilievo nuovo.</p>
<script>
  let fonti = [], momenti = [], i = 0;
  const el = (id) => document.getElementById(id);
  function mostra() {
    const m = momenti[i];
    if (!m) { el("ora").textContent = "nessun dato"; return; }
    el("ora").textContent = m.quando.slice(11);
    el("quanto").textContent = m.quando.slice(8, 10) + "." + m.quando.slice(5, 7) + " · " + m.quanto;
    el("prima").disabled = i >= momenti.length - 1;
    el("dopo").disabled = el("adesso").disabled = i === 0;
    el("mappe").replaceChildren(...fonti.map(([fonte, etichetta]) => {
      const f = document.createElement("figure");
      if (m.file[fonte]) {
        const img = document.createElement("img");
        img.src = "/mappe/" + m.file[fonte]; img.alt = etichetta + " alle " + m.quando.slice(11); img.loading = "lazy";
        f.append(img);
      } else {
        const d = document.createElement("div"); d.className = "vuota"; d.textContent = etichetta + ": nessuna mappa per questo quarto d'ora"; f.append(d);
      }
      return f;
    }));
  }
  async function carica() {
    const r = await fetch("/api/momenti", { cache: "no-store" });
    if (!r.ok) return;
    const d = await r.json();
    const corrente = momenti[i] && momenti[i].quando;
    fonti = d.fonti; momenti = d.momenti;
    i = i === 0 || !corrente ? 0 : Math.max(0, momenti.findIndex((m) => m.quando === corrente));
    mostra();
  }
  el("prima").onclick = () => { i = Math.min(i + 1, momenti.length - 1); mostra(); };
  el("dopo").onclick = () => { i = Math.max(i - 1, 0); mostra(); };
  el("adesso").onclick = () => { i = 0; mostra(); };
  carica();
  setInterval(() => { if (i === 0) carica(); }, 60000);
</script>
</body>
</html>`;
