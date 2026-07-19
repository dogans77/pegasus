type Race = { id: number; race_number: number; race_date: string; scheduled_time: string | null; distance_meters: number; surface: string; track: { city: string; name: string } };
type Entry = { id?: number; entry_id?: number; program_number: number; horse_name: string | null; jockey_name?: string | null; trainer_name?: string | null; handicap_rating: number | null; agf_percent: number | null; weight_kg: number | null; win_probability?: number };
type Intelligence = { chaos_index: number; method: string; entries: Entry[] };
type Recommendation = { model_version: string; confidence: string; chaos_index: number; primary: Entry; alternatives: Entry[]; reasons: string[]; disclaimer: string };
type ValueEntry = { program_number: number; horse_name: string; model_probability: number; agf_market_probability: number; edge_percentage_points: number; value_score: number };
type Value = { model_version: string; chaos_index: number; value_candidates: ValueEntry[]; false_favorite: ValueEntry; market_signal: string };
type Sequence = { estimated_columns: number; legs: { race_number: number; selection_count: number; selections: Entry[] }[] };

const api = "http://127.0.0.1:8042/api/v1";
const entryId = (entry: Entry) => entry.entry_id ?? entry.id ?? entry.program_number;

async function getJson<T>(path: string, fallback: T): Promise<T> {
  try { const response = await fetch(`${api}${path}`, { cache: "no-store" }); return response.ok ? await response.json() as T : fallback; } catch { return fallback; }
}

export const dynamic = "force-dynamic";

export default async function RaceDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const raceId = Number(id);
  const races = await getJson<Race[]>("/races/", []);
  const race = races.find((item) => item.id === raceId);
  if (!race) return <main><a className="back-link" href="/">â† Kontrol paneline dÃ¶n</a><section className="detail-empty"><h1>KoÅŸu bulunamadÄ±</h1><p>YarÄ±ÅŸ verisi yenilenmiÅŸ veya bu kart artÄ±k mevcut deÄŸil.</p></section></main>;
  const [entries, intelligence, recommendation, value, sequence] = await Promise.all([
    getJson<Entry[]>(`/races/${raceId}/entries`, []),
    getJson<Intelligence | null>(`/races/${raceId}/intelligence`, null),
    getJson<Recommendation | null>(`/recommendations/races/${raceId}`, null),
    getJson<Value | null>(`/value/races/${raceId}`, null),
    getJson<Sequence | null>(`/decision/sequence/${raceId}?risk=balanced&max_columns=240`, null),
  ]);
  const modelProbabilities = new Map<number, number>();
  if (recommendation?.primary) modelProbabilities.set(entryId(recommendation.primary), recommendation.primary.win_probability ?? 0);
  recommendation?.alternatives.forEach((entry) => modelProbabilities.set(entryId(entry), entry.win_probability ?? 0));
  const ranked = [...entries].sort((left, right) => (modelProbabilities.get(entryId(right)) ?? right.win_probability ?? 0) - (modelProbabilities.get(entryId(left)) ?? left.win_probability ?? 0));
  const topProbability = recommendation?.primary?.win_probability;
  const topValue = value?.value_candidates?.[0];
  return <main>
    <a className="back-link" href="/">â† Kontrol paneline dÃ¶n</a>
    <section className="detail-hero"><p className="eyebrow">KOÅU DETAYI</p><h1>{race.track.city} {race.race_number}. KoÅŸu</h1><p className="sub">{race.scheduled_time?.slice(0, 5) ?? "--:--"} Â· {race.distance_meters}m Â· {race.surface} Â· {entries.length} at</p></section>
    <section className="detail-grid">
      <article className="panel recommendation"><p className="eyebrow">MODEL Ã–NERÄ°SÄ°</p><h2>{recommendation?.primary ? `${recommendation.primary.program_number}. ${recommendation.primary.horse_name}` : "Veri bekleniyor"}</h2><div className="confidence"><span>Kazanma olasÄ±lÄ±ÄŸÄ±</span><strong>{topProbability !== undefined ? `%${topProbability.toFixed(1)}` : "--"}</strong><small>{recommendation?.model_version ?? "Model hazÄ±r deÄŸil"} Â· {recommendation?.confidence ?? "--"} gÃ¼ven</small></div><ul>{recommendation?.reasons.map((reason, index) => <li key={`${reason}-${index}`}>{reason}</li>) ?? <li>Yeterli yarÄ±ÅŸ verisi yok.</li>}</ul>{recommendation?.alternatives.length ? <p className="sub">Alternatifler: {recommendation.alternatives.map((item) => `${item.program_number}. ${item.horse_name}`).join(" Â· ")}</p> : null}<small>{recommendation?.disclaimer}</small></article>
      <article className="panel recommendation"><p className="eyebrow">YARIÅ RÄ°SKÄ°</p><h2>Chaos Index</h2><div className="confidence"><span>SÃ¼rpriz riski</span><strong>{value ? `${value.chaos_index}/100` : intelligence ? `${intelligence.chaos_index}/100` : "--"}</strong><small>{value?.market_signal ?? intelligence?.method ?? "GiriÅŸler geldikten sonra hesaplanÄ±r."}</small></div><p className="sub">YÃ¼ksek deÄŸer, favori sÄ±ralamasÄ±nÄ±n daha az kesin olduÄŸunu gÃ¶sterir.</p></article>
    </section>
    <section className="detail-grid">
      <article className="panel recommendation"><p className="eyebrow">VALUE SÄ°NYALÄ°</p><h2>{topValue ? `${topValue.program_number}. ${topValue.horse_name}` : "Belirgin aday yok"}</h2><div className="confidence"><span>Model - AGF farkÄ±</span><strong>{topValue ? `%${topValue.edge_percentage_points.toFixed(1)}` : "--"}</strong><small>{topValue ? `Model %${topValue.model_probability.toFixed(1)} Â· AGF %${topValue.agf_market_probability.toFixed(1)}` : "AGF, piyasa sinyali olarak izlenir."}</small></div></article>
      <article className="panel recommendation"><p className="eyebrow">KAPSAMA PLANI</p><h2>{sequence ? `${sequence.estimated_columns} kolon` : "Plan bekleniyor"}</h2><div className="confidence"><span>Dengeli profil</span><strong>{sequence ? `${sequence.legs.length} ayak` : "--"}</strong><small>{sequence ? sequence.legs.map((leg) => `${leg.race_number}. ayak: ${leg.selection_count} at`).join(" Â· ") : "Yeterli koÅŸu kartÄ± bekleniyor."}</small></div></article>
    </section>
    <section className="panel detail-entries"><div className="panel-head"><div><p className="eyebrow">SIRALAMA</p><h2>Atlar ve sinyaller</h2></div><span>{ranked.length} at</span></div>{ranked.length ? <div className="entry-table"><div className="entry-table-head"><span>No</span><span>At / Jokey</span><span>HP</span><span>AGF</span><span>Kilo</span><span>Model</span></div>{ranked.map((entry, index) => { const probability = modelProbabilities.get(entryId(entry)) ?? entry.win_probability; return <div className="entry-table-row" key={`${entryId(entry)}-${index}`}><b>{entry.program_number}</b><div><strong>{entry.horse_name}</strong><small>{entry.jockey_name ?? "--"}{entry.trainer_name ? ` Â· ${entry.trainer_name}` : ""}</small></div><span>{entry.handicap_rating ?? "--"}</span><span>%{entry.agf_percent ?? "--"}</span><span>{entry.weight_kg ?? "--"}</span><em>%{probability?.toFixed(1) ?? "--"}</em></div> })}</div> : <div className="empty">Bu koÅŸu iÃ§in at giriÅŸi yok.</div>}</section>
  </main>;
}