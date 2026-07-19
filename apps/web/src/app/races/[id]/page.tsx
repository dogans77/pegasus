type Race = { id: number; race_number: number; race_date: string; scheduled_time: string | null; distance_meters: number; surface: string; track: { city: string; name: string } };
type Entry = { id: number; program_number: number; horse_name: string | null; jockey_name: string | null; trainer_name?: string | null; handicap_rating: number | null; agf_percent: number | null; weight_kg: number | null; win_probability?: number };
type Intelligence = { chaos_index: number; method: string; entries: Entry[] };
type Recommendation = { confidence: string; primary: Entry; alternatives: Entry[]; reasons: string[]; disclaimer: string };

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
  if (!race) return <main><a className="back-link" href="/">\u2190 Kontrol paneline don</a><section className="detail-empty"><h1>Kosu bulunamadi</h1><p>Yaris verisi yenilenmis veya bu kart artik mevcut degil.</p></section></main>;
  const [entries, intelligence, recommendation] = await Promise.all([
    getJson<Entry[]>(`/races/${raceId}/entries`, []),
    getJson<Intelligence | null>(`/races/${raceId}/intelligence`, null),
    getJson<Recommendation | null>(`/recommendations/races/${raceId}`, null),
  ]);
  const ranked = intelligence?.entries ?? entries;
  return <main>
    <a className="back-link" href="/">\u2190 Kontrol paneline don</a>
    <section className="detail-hero"><p className="eyebrow">KOSU DETAYI</p><h1>{race.track.city} {race.race_number}. Kosu</h1><p className="sub">{race.scheduled_time?.slice(0, 5) ?? "--:--"} \u00b7 {race.distance_meters}m \u00b7 {race.surface} \u00b7 {entries.length} at</p></section>
    <section className="detail-grid">
      <article className="panel recommendation"><p className="eyebrow">BASELINE ONERI</p><h2>{recommendation?.primary ? `${recommendation.primary.program_number}. ${recommendation.primary.horse_name}` : "Veri bekleniyor"}</h2><div className="confidence"><span>Guven</span><strong>{recommendation?.confidence ?? "--"}</strong></div><ul>{recommendation?.reasons.map((reason) => <li key={reason}>{reason}</li>) ?? <li>Yeterli yaris verisi yok.</li>}</ul><small>{recommendation?.disclaimer}</small></article>
      <article className="panel recommendation"><p className="eyebrow">YARIS RISKI</p><h2>Chaos Index</h2><div className="confidence"><span>Surpriz riski</span><strong>{intelligence ? `${intelligence.chaos_index}/100` : "--"}</strong></div><p className="sub">{intelligence?.method ?? "Girisler geldikten sonra hesaplanir."}</p></article>
    </section>
    <section className="panel detail-entries"><div className="panel-head"><div><p className="eyebrow">SIRALAMA</p><h2>Atlar ve sinyaller</h2></div><span>{ranked.length} at</span></div>{ranked.length ? <div className="entry-table"><div className="entry-table-head"><span>No</span><span>At / Jokey</span><span>HP</span><span>AGF</span><span>Kilo</span><span>Olasilik</span></div>{ranked.map((entry) => <div className="entry-table-row" key={entry.id}><b>{entry.program_number}</b><div><strong>{entry.horse_name}</strong><small>{entry.jockey_name ?? "--"}{entry.trainer_name ? ` \u00b7 ${entry.trainer_name}` : ""}</small></div><span>{entry.handicap_rating ?? "--"}</span><span>%{entry.agf_percent ?? "--"}</span><span>{entry.weight_kg ?? "--"}</span><em>%{entry.win_probability?.toFixed(1) ?? "--"}</em></div>)}</div> : <div className="empty">Bu kosu icin at girisi yok.</div>}</section>
  </main>;
}