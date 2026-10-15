// Logica pura della pagina, condivisa dal Worker e dalle prove (node sito/prova_sito.mjs).

export const FONTI = [
  ["apple", "Apple Maps"], ["tomtom", "TomTom"], ["google", "Google"],   // Waze tolto dal pannello (15.10): solo dati nei CSV
];
const NOME_MAPPA = /^(\d{4}-\d{2}-\d{2})-(\d{2})(\d{2})-(apple|tomtom|google)\.svg$/;

// Solo nomi di mappa validi: niente percorsi arbitrari verso il repository.
export function mappaValida(nome) {
  return NOME_MAPPA.test(nome);
}

// Elenco dei file → momenti, dal più recente: [{ quando: "2026-10-15 18:00", file: { apple: "…svg", … } }]
export function momenti(nomi) {
  const per = new Map();
  for (const nome of nomi) {
    const m = NOME_MAPPA.exec(nome);
    if (!m) continue;
    const quando = `${m[1]} ${m[2]}:${m[3]}`;
    if (!per.has(quando)) per.set(quando, {});
    per.get(quando)[m[4]] = nome;
  }
  return [...per.entries()].sort((a, b) => (a[0] < b[0] ? 1 : -1)).map(([quando, file]) => ({ quando, file }));
}

// «adesso», «15 minuti fa», «1 h 30 min fa» rispetto al momento più recente.
export function quanto(indice) {
  if (indice === 0) return "adesso";
  const min = indice * 15;
  if (min < 60) return `${min} minuti fa`;
  const h = Math.floor(min / 60), r = min % 60;
  return r ? `${h} h ${r} min fa` : `${h} h fa`;
}
