type Race = { id: number; race_number: number; race_date: string; scheduled_time: string | null; distance_meters: number; surface: string; track: { city: string; name: string } };
type Entry = { id: number; program_number: number; horse_name: string | null; jockey_name: string | null; trainer_name?: string | null; handicap_rating: number | null; agf_percent: number | null; weight_kg: number | null; win_probability?: number };
type Intelligence = { chaos_index: number; method: string; entries: Entry[] };
type Recommendation = { model_version: string; confidence: string; chaos_index: number; primary: Entry; alternatives: Entry[]; reasons: string[]; disclaimer: string };

const api = "http://127.0.0.1:8042/api/v1";

async function getJson<T>(path: string, fallback: T): Promise<T> {
  try { const response = await fetch(`${api}${path}`, { cache: "no-store" }); return response.ok ? await response.json() as T : fallback; } catch { return fallback; }
}

export const dynamic = "force-dynamic";

export default async function RaceDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const raceId = Number(id);
  const races = await getJson<Race[]>("/races/", []);
  const race = races.find((item) => item.id === raceId);
  if (!race) return <main><a className="back-link" href="/">\u2190 Kontrol paneline d\u00f6n</a><section className="detail-empty"><h1>Ko\u015fu bulunamad\u0131</h1><p>Yar\u0131\u015f verisi yenilenmi\u015f veya bu kart art\u0131k mevcut de\u011fil.</p></section></main>;
  const [entries, intelligence, recommendation] = await Promise.all([
    getJson<Entry[]>(`/races/${raceId}/entries`, []),
    getJson<Intelligence | null>(`/races/${raceId}/intelligence`, null),
    getJson<Recommendation | null>(`/recommendations/races/${raceId}`, null),
  ]);
  const modelProbabilities = new Map<number, number>();
  if (recommendation?.primary) modelProbabilities.set(recommendation.primary.id, recommendation.primary.win_probability ?? 0);
  recommendation?.alternatives.forEach((entry) => modelProbabilities.set(entry.id, entry.win_probability ?? 0));
  const ranked = [...entries].sort((left, right) => (modelProbabilities.get(right.id) ?? right.win_probability ?? 0) - (modelProbabilities.get(left.id) ?? left.win_probability ?? 0));
  const topProbability = recommendation?.primary?.win_probability;
  return <main>
    <a className="back-link" href="/">\u2190 Kontrol paneline d\u00f6n</a>
    <section className="detail-hero"><p className="eyebrow">KO\u015eU DETAYI</p><h1>{race.track.city} {race.race_number}. Ko\u015fu</h1><p className="sub">{race.scheduled_time?.slice(0, 5) ?? "--:--"} \u00b7 {race.distance_meters}m \u00b7 {race.surface} \u00b7 {entries.length} at</p></section>
    <section className="detail-grid">
      <article className="panel recommendation"><p className="eyebrow">MODEL \u00d6NER\u0130S\u0130</p><h2>{recommendation?.primary ? `${recommendation.primary.program_number}. ${recommendation.primary.horse_name}` : "Veri bekleniyor"}</h2><div className="confidence"><span>Kazanma olas\u0131l\u0131\u011f\u0131</span><strong>{topProbability !== undefined ? `%${topProbability.toFixed(1)}` : "--"}</strong><small>{recommendation?.model_version ?? "Model haz\u0131r de\u011fil"} \u00b7 {recommendation?.confidence ?? "--"} g\u00fcven</small></div><ul>{recommendation?.reasons.map((reason) => <li key={reason}>{reason}</li>) ?? <li>Yeterli yar\u0131\u015f verisi yok.</li>}</ul>{recommendation?.alternatives.length ? <p className="sub">Alternatifler: {recommendation.alternatives.map((item) => `${item.program_number}. ${item.horse_name}`).join(" \u00b7 ")}</p> : null}<small>{recommendation?.disclaimer}</small></article>
      <article className="panel recommendation"><p className="eyebrow">YARI\u015e R\u0130SK\u0130</p><h2>Chaos Index</h2><div className="confidence"><span>S\u00fcrpriz riski</span><strong>{intelligence ? `${intelligence.chaos_index}/100` : "--"}</strong><small>{intelligence?.method ?? "Giri\u015fler geldikten sonra hesaplan\u0131r."}</small></div><p className="sub">Y\u00fcksek de\u011fer, favori s\u0131ralamas\u0131n\u0131n daha az kesin oldu\u011funu g\u00f6sterir.</p></article>
    </section>
    <section className="panel detail-entries"><div className="panel-head"><div><p className="eyebrow">SIRALAMA</p><h2>Atlar ve sinyaller</h2></div><span>{ranked.length} at</span></div>{ranked.length ? <div className="entry-table"><div className="entry-table-head"><span>No</span><span>At / Jokey</span><span>HP</span><span>AGF</span><span>Kilo</span><span>Model</span></div>{ranked.map((entry) => { const probability = modelProbabilities.get(entry.id) ?? entry.win_probability; return <div className="entry-table-row" key={entry.id}><b>{entry.program_number}</b><div><strong>{entry.horse_name}</strong><small>{entry.jockey_name ?? "--"}{entry.trainer_name ? ` \u00b7 ${entry.trainer_name}` : ""}</small></div><span>{entry.handicap_rating ?? "--"}</span><span>%{entry.agf_percent ?? "--"}</span><span>{entry.weight_kg ?? "--"}</span><em>%{probability?.toFixed(1) ?? "--"}</em></div> })}</div> : <div className="empty">Bu ko\u015fu i\u00e7in at giri\u015fi yok.</div>}</section>
  </main>;
}