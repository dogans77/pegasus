type Race = { id: number; race_number: number; race_date: string; scheduled_time: string | null; distance_meters: number; surface: string; track: { city: string; name: string } };
type Entry = { id?: number; entry_id?: number; program_number: number; horse_name: string | null; jockey_name?: string | null; trainer_name?: string | null; handicap_rating: number | null; agf_percent: number | null; weight_kg: number | null; win_probability?: number };
type Intelligence = { chaos_index: number; method: string; entries: Entry[] };
type Recommendation = { model_version: string; confidence: string; chaos_index: number; primary: Entry; alternatives: Entry[]; reasons: string[]; disclaimer: string };
type ValueEntry = { program_number: number; horse_name: string; model_probability: number; agf_market_probability: number; edge_percentage_points: number; value_score: number };
type Value = { model_version: string; chaos_index: number; value_candidates: ValueEntry[]; false_favorite: ValueEntry; market_signal: string };
type Sequence = { estimated_columns: number; legs: { race_number: number; selection_count: number; selections: Entry[] }[] };
type ExplanationCandidate = { entry_id:number; program_number:number; horse_name:string; win_probability:number; strengths:{label:string;detail:string}[]; risks:{label:string;detail:string}[] };
type Explanation = { model_version:string; methodology:string; candidates:ExplanationCandidate[] };

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
  if (!race) return <main><a className="back-link" href="/">ÃƒÂ¢Ã¢â‚¬Â Ã‚Â Kontrol paneline dÃƒÆ’Ã‚Â¶n</a><section className="detail-empty"><h1>KoÃƒâ€¦Ã…Â¸u bulunamadÃƒâ€Ã‚Â±</h1><p>YarÃƒâ€Ã‚Â±Ãƒâ€¦Ã…Â¸ verisi yenilenmiÃƒâ€¦Ã…Â¸ veya bu kart artÃƒâ€Ã‚Â±k mevcut deÃƒâ€Ã…Â¸il.</p></section></main>;
  const [entries, intelligence, recommendation, value, sequence, explanation] = await Promise.all([
    getJson<Entry[]>(`/races/${raceId}/entries`, []),
    getJson<Intelligence | null>(`/races/${raceId}/intelligence`, null),
    getJson<Recommendation | null>(`/recommendations/races/${raceId}`, null),
    getJson<Value | null>(`/value/races/${raceId}`, null),
    getJson<Sequence | null>(`/decision/sequence/${raceId}?risk=balanced&max_columns=240`, null),
    getJson<Explanation | null>(`/explanations/races/${raceId}`, null),
  ]);
  const modelProbabilities = new Map<number, number>();
  if (recommendation?.primary) modelProbabilities.set(entryId(recommendation.primary), recommendation.primary.win_probability ?? 0);
  recommendation?.alternatives.forEach((entry) => modelProbabilities.set(entryId(entry), entry.win_probability ?? 0));
  const ranked = [...entries].sort((left, right) => (modelProbabilities.get(entryId(right)) ?? right.win_probability ?? 0) - (modelProbabilities.get(entryId(left)) ?? left.win_probability ?? 0));
  const primaryEntryId = recommendation?.primary ? entryId(recommendation.primary) : -1;
  const topExplanation = explanation?.candidates.find((item) => item.entry_id === primaryEntryId) ?? explanation?.candidates[0];
  const topProbability = recommendation?.primary?.win_probability;
  const topValue = value?.value_candidates?.[0];
  return <main>
    <a className="back-link" href="/">ÃƒÂ¢Ã¢â‚¬Â Ã‚Â Kontrol paneline dÃƒÆ’Ã‚Â¶n</a>
    <section className="detail-hero"><p className="eyebrow">KOÃƒâ€¦Ã‚ÂU DETAYI</p><h1>{race.track.city} {race.race_number}. KoÃƒâ€¦Ã…Â¸u</h1><p className="sub">{race.scheduled_time?.slice(0, 5) ?? "--:--"} Ãƒâ€šÃ‚Â· {race.distance_meters}m Ãƒâ€šÃ‚Â· {race.surface} Ãƒâ€šÃ‚Â· {entries.length} at</p></section>
    <section className="panel explanation-panel">
      <div className="panel-head"><div><p className="eyebrow">MODEL\u00dcN GEREK\u00c7ES\u0130</p><h2>{topExplanation ? `${topExplanation.program_number}. ${topExplanation.horse_name}` : "A\u00e7\u0131klama bekleniyor"}</h2></div><span>{explanation?.model_version ?? "--"}</span></div>
      {topExplanation ? <div className="explanation-grid"><div><small>G\u00fc\u00e7l\u00fc sinyaller</small>{topExplanation.strengths.length ? topExplanation.strengths.map((signal,index)=><p key={`${signal.label}-${index}`}><b>{signal.label}</b><span>{signal.detail}</span></p>) : <p className="muted">Yeterli olumlu ge\u00e7mi\u015f sinyali yok.</p>}</div><div><small>Riskler</small>{topExplanation.risks.length ? topExplanation.risks.map((signal,index)=><p key={`${signal.label}-${index}`}><b>{signal.label}</b><span>{signal.detail}</span></p>) : <p className="muted">Belirgin risk sinyali yok.</p>}</div></div> : <div className="empty">Bu ko\u015fu i\u00e7in model a\u00e7\u0131klamas\u0131 hen\u00fcz olu\u015fmad\u0131.</div>}
    </section>    <section className="detail-grid">
      <article className="panel recommendation"><p className="eyebrow">MODEL ÃƒÆ’Ã¢â‚¬â€œNERÃƒâ€Ã‚Â°SÃƒâ€Ã‚Â°</p><h2>{recommendation?.primary ? `${recommendation.primary.program_number}. ${recommendation.primary.horse_name}` : "Veri bekleniyor"}</h2><div className="confidence"><span>Kazanma olasÃƒâ€Ã‚Â±lÃƒâ€Ã‚Â±Ãƒâ€Ã…Â¸Ãƒâ€Ã‚Â±</span><strong>{topProbability !== undefined ? `%${topProbability.toFixed(1)}` : "--"}</strong><small>{recommendation?.model_version ?? "Model hazÃƒâ€Ã‚Â±r deÃƒâ€Ã…Â¸il"} Ãƒâ€šÃ‚Â· {recommendation?.confidence ?? "--"} gÃƒÆ’Ã‚Â¼ven</small></div><ul>{recommendation?.reasons.map((reason, index) => <li key={`${reason}-${index}`}>{reason}</li>) ?? <li>Yeterli yarÃƒâ€Ã‚Â±Ãƒâ€¦Ã…Â¸ verisi yok.</li>}</ul>{recommendation?.alternatives.length ? <p className="sub">Alternatifler: {recommendation.alternatives.map((item) => `${item.program_number}. ${item.horse_name}`).join(" Ãƒâ€šÃ‚Â· ")}</p> : null}<small>{recommendation?.disclaimer}</small></article>
      <article className="panel recommendation"><p className="eyebrow">YARIÃƒâ€¦Ã‚Â RÃƒâ€Ã‚Â°SKÃƒâ€Ã‚Â°</p><h2>Chaos Index</h2><div className="confidence"><span>SÃƒÆ’Ã‚Â¼rpriz riski</span><strong>{value ? `${value.chaos_index}/100` : intelligence ? `${intelligence.chaos_index}/100` : "--"}</strong><small>{value?.market_signal ?? intelligence?.method ?? "GiriÃƒâ€¦Ã…Â¸ler geldikten sonra hesaplanÃƒâ€Ã‚Â±r."}</small></div><p className="sub">YÃƒÆ’Ã‚Â¼ksek deÃƒâ€Ã…Â¸er, favori sÃƒâ€Ã‚Â±ralamasÃƒâ€Ã‚Â±nÃƒâ€Ã‚Â±n daha az kesin olduÃƒâ€Ã…Â¸unu gÃƒÆ’Ã‚Â¶sterir.</p></article>
    </section>
    <section className="panel explanation-panel">
      <div className="panel-head"><div><p className="eyebrow">MODEL\u00dcN GEREK\u00c7ES\u0130</p><h2>{topExplanation ? `${topExplanation.program_number}. ${topExplanation.horse_name}` : "A\u00e7\u0131klama bekleniyor"}</h2></div><span>{explanation?.model_version ?? "--"}</span></div>
      {topExplanation ? <div className="explanation-grid"><div><small>G\u00fc\u00e7l\u00fc sinyaller</small>{topExplanation.strengths.length ? topExplanation.strengths.map((signal,index)=><p key={`${signal.label}-${index}`}><b>{signal.label}</b><span>{signal.detail}</span></p>) : <p className="muted">Yeterli olumlu ge\u00e7mi\u015f sinyali yok.</p>}</div><div><small>Riskler</small>{topExplanation.risks.length ? topExplanation.risks.map((signal,index)=><p key={`${signal.label}-${index}`}><b>{signal.label}</b><span>{signal.detail}</span></p>) : <p className="muted">Belirgin risk sinyali yok.</p>}</div></div> : <div className="empty">Bu ko\u015fu i\u00e7in model a\u00e7\u0131klamas\u0131 hen\u00fcz olu\u015fmad\u0131.</div>}
    </section>    <section className="detail-grid">
      <article className="panel recommendation"><p className="eyebrow">VALUE SÃƒâ€Ã‚Â°NYALÃƒâ€Ã‚Â°</p><h2>{topValue ? `${topValue.program_number}. ${topValue.horse_name}` : "Belirgin aday yok"}</h2><div className="confidence"><span>Model - AGF farkÃƒâ€Ã‚Â±</span><strong>{topValue ? `%${topValue.edge_percentage_points.toFixed(1)}` : "--"}</strong><small>{topValue ? `Model %${topValue.model_probability.toFixed(1)} Ãƒâ€šÃ‚Â· AGF %${topValue.agf_market_probability.toFixed(1)}` : "AGF, piyasa sinyali olarak izlenir."}</small></div></article>
      <article className="panel recommendation"><p className="eyebrow">KAPSAMA PLANI</p><h2>{sequence ? `${sequence.estimated_columns} kolon` : "Plan bekleniyor"}</h2><div className="confidence"><span>Dengeli profil</span><strong>{sequence ? `${sequence.legs.length} ayak` : "--"}</strong><small>{sequence ? sequence.legs.map((leg) => `${leg.race_number}. ayak: ${leg.selection_count} at`).join(" Ãƒâ€šÃ‚Â· ") : "Yeterli koÃƒâ€¦Ã…Â¸u kartÃƒâ€Ã‚Â± bekleniyor."}</small></div></article>
    </section>
    <section className="panel detail-entries"><div className="panel-head"><div><p className="eyebrow">SIRALAMA</p><h2>Atlar ve sinyaller</h2></div><span>{ranked.length} at</span></div>{ranked.length ? <div className="entry-table"><div className="entry-table-head"><span>No</span><span>At / Jokey</span><span>HP</span><span>AGF</span><span>Kilo</span><span>Model</span></div>{ranked.map((entry, index) => { const probability = modelProbabilities.get(entryId(entry)) ?? entry.win_probability; return <div className="entry-table-row" key={`${entryId(entry)}-${index}`}><b>{entry.program_number}</b><div><strong>{entry.horse_name}</strong><small>{entry.jockey_name ?? "--"}{entry.trainer_name ? ` Ãƒâ€šÃ‚Â· ${entry.trainer_name}` : ""}</small></div><span>{entry.handicap_rating ?? "--"}</span><span>%{entry.agf_percent ?? "--"}</span><span>{entry.weight_kg ?? "--"}</span><em>%{probability?.toFixed(1) ?? "--"}</em></div> })}</div> : <div className="empty">Bu koÃƒâ€¦Ã…Â¸u iÃƒÆ’Ã‚Â§in at giriÃƒâ€¦Ã…Â¸i yok.</div>}</section>
  </main>;
}