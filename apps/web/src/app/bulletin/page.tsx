type Race = {
  id: number; race_number?: number | null; scheduled_time?: string | null; start_time?: string | null;
  distance_meters?: number | null; surface?: string | null; status?: string | null;
  track?: { id?: number; name?: string | null } | null;
};
type Entry = {
  id: number; program_number?: number | null; horse_id?: number | null; horse_name?: string | null;
  jockey_name?: string | null; trainer_name?: string | null; weight_kg?: number | string | null;
  handicap_rating?: number | string | null; agf_percent?: number | string | null;
};
type Candidate = { program_number?: number | null; horse_name?: string | null; win_probability?: number | string | null; strengths?: string[]; risks?: string[] };
type Explanation = { primary?: Candidate | null; alternatives?: Candidate[]; chaos_index?: number | string | null };
type ValueItem = { program_number?: number | null; horse_name?: string | null; edge_percentage_points?: number | string | null };
type Value = { chaos_index?: number | string | null; value_candidates?: ValueItem[]; false_favorite?: ValueItem | null };

export const dynamic = 'force-dynamic';

const api = process.env.PEGASUS_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8042/api/v1';
const t = {
  title: 'G\u00fcnl\u00fck b\u00fclten',
  intro: 'Resmi program, model sinyali ve ko\u015fu kart\u0131 tek ekranda.',
  today: 'Bug\u00fcn', city: 'Hipodrom', race: 'Ko\u015fu', races: 'ko\u015fu', runners: 'at',
  no: 'No', horse: 'At', model: 'Model', hp: 'HP', agf: 'AGF', weight: 'Kilo', jockey: 'Jokey', trainer: 'Antren\u00f6r',
  card: 'Ko\u015fu kart\u0131', details: 'Detayl\u0131 incele', featured: '\u00d6ne \u00e7\u0131kan aday',
  analysis: 'Analiz notu', chaos: 'S\u00fcrpriz riski', value: 'De\u011fer sinyali',
  unavailable: 'Bug\u00fcn i\u00e7in aktar\u0131lm\u0131\u015f resmi program bulunamad\u0131.',
  waiting: 'G\u00fcncel program aktar\u0131ld\u0131\u011f\u0131nda b\u00fclten burada g\u00f6r\u00fcnecek.',
  profile: 'At profili', surface: 'Pist', distance: 'Mesafe', time: 'Saat', source: 'Kaynak: resmi program aktar\u0131m\u0131',
  caution: 'Bu ekran olas\u0131l\u0131k tabanl\u0131 karar deste\u011fidir; kesin sonu\u00e7 iddias\u0131 ta\u015f\u0131maz.',
  back: 'Programa d\u00f6n', unavailableData: 'Veri yok',
};

async function getJson<T>(path: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(`${api}${path}`, { cache: 'no-store' });
    return response.ok ? await response.json() as T : fallback;
  } catch { return fallback; }
}
function items<T>(value: unknown): T[] { return Array.isArray(value) ? value as T[] : Array.isArray((value as { items?: T[] })?.items) ? (value as { items: T[] }).items : []; }
function text(value: unknown): string { return value === null || value === undefined || value === '' ? '--' : String(value); }
function number(value: unknown): number | null { const result = Number(value); return Number.isFinite(result) ? result : null; }
function pct(value: unknown): string { const result = number(value); return result === null ? '--' : `%${result.toFixed(1)}`; }
function raceTime(race: Race): string { return text(race.scheduled_time ?? race.start_time); }
function cityName(race: Race): string { return text(race.track?.name).replace(/\s+/g, ' ').trim(); }

export default async function Bulletin({ searchParams }: { searchParams: Promise<{ city?: string; race?: string }> }) {
  const query = await searchParams;
  const allRaces = items<Race>(await getJson<unknown>('/races/', []));
  const localDate = new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Istanbul' }).format(new Date());
  const dates = Array.from(new Set(allRaces.map((race) => String((race as Race & { race_date?: string }).race_date ?? '').slice(0, 10)).filter(Boolean)));
  const activeDate = dates.includes(localDate) ? localDate : '';
  const dayRaces = activeDate ? allRaces.filter((race) => String((race as Race & { race_date?: string }).race_date ?? '').slice(0, 10) === activeDate) : [];
  const cities = Array.from(new Set(dayRaces.map(cityName).filter((name) => name !== '--'))).sort((a, b) => a.localeCompare(b, 'tr'));
  const selectedCity = cities.includes(query.city ?? '') ? String(query.city) : (cities[0] ?? '');
  const cityRaces = dayRaces.filter((race) => cityName(race) === selectedCity).sort((a, b) => (a.race_number ?? 999) - (b.race_number ?? 999));
  const requestedRace = Number(query.race);
  const selectedRace = cityRaces.find((race) => race.id === requestedRace) ?? cityRaces[0] ?? null;
  const [rawEntries, rawExplanation, rawValue] = selectedRace ? await Promise.all([
    getJson<unknown>(`/races/${selectedRace.id}/entries`, []),
    getJson<Explanation | null>(`/explanations/races/${selectedRace.id}`, null),
    getJson<Value | null>(`/value/races/${selectedRace.id}`, null),
  ]) : [[], null, null];
  const entries = items<Entry>(rawEntries).sort((a, b) => (a.program_number ?? 999) - (b.program_number ?? 999));
  const explanation = rawExplanation as Explanation | null;
  const value = rawValue as Value | null;
  const candidates = [explanation?.primary, ...(explanation?.alternatives ?? [])].filter(Boolean) as Candidate[];
  const candidateByNo = new Map(candidates.map((candidate) => [candidate.program_number, candidate]));
  const lead = explanation?.primary ?? candidates[0] ?? null;
  const valueLead = value?.value_candidates?.[0] ?? null;
  const makeHref = (city: string, raceId?: number) => `/bulletin?city=${encodeURIComponent(city)}${raceId ? `&race=${raceId}` : ''}`;

  return <main className="bulletin-shell">
    <header className="bulletin-top"><div><a href="/">PEGASUS</a><span>{t.title}</span></div><a href="/program">{t.back}</a></header>
    <section className="bulletin-hero"><div><p className="eyebrow">{t.today.toUpperCase()}</p><h1>{t.title}</h1><p>{t.intro}</p></div><div className="bulletin-source"><b>{activeDate || '--'}</b><span>{t.source}</span></div></section>
    {!selectedRace ? <section className="bulletin-empty"><h2>{t.unavailable}</h2><p>{t.waiting}</p></section> : <>
      <section className="bulletin-city-tabs" aria-label={t.city}>{cities.map((city) => <a key={city} className={city === selectedCity ? 'active' : ''} href={makeHref(city)}>{city}</a>)}</section>
      <section className="bulletin-race-tabs" aria-label={t.race}>{cityRaces.map((race) => <a key={race.id} className={race.id === selectedRace.id ? 'active' : ''} href={makeHref(selectedCity, race.id)}><b>{race.race_number}. {t.race}</b><span>{raceTime(race)}</span></a>)}</section>
      <section className="bulletin-race-meta"><div><p className="eyebrow">{selectedCity} / {selectedRace.race_number}. {t.race}</p><h2>{t.card}</h2><p>{raceTime(selectedRace)} Â· {selectedRace.distance_meters ?? '--'}m Â· {text(selectedRace.surface)} Â· {entries.length} {t.runners}</p></div><a className="bulletin-detail-link" href={`/races/${selectedRace.id}`}>{t.details} â†’</a></section>
      <section className="bulletin-grid">
        <div className="bulletin-table-card"><div className="panel-heading"><div><p className="eyebrow">{t.card.toUpperCase()}</p><h2>{entries.length} {t.runners}</h2></div><small>{t.caution}</small></div><div className="bulletin-table-wrap"><table className="bulletin-table"><thead><tr><th>{t.no}</th><th>{t.horse}</th><th>{t.model}</th><th>{t.hp}</th><th>{t.agf}</th><th>{t.weight}</th><th>{t.jockey}</th><th>{t.trainer}</th></tr></thead><tbody>{entries.map((entry) => { const candidate = candidateByNo.get(entry.program_number); return <tr key={entry.id}><td>{text(entry.program_number)}</td><td><b>{text(entry.horse_name)}</b>{entry.horse_id ? <a href={`/horses/${entry.horse_id}`}>{t.profile} â†’</a> : null}</td><td>{pct(candidate?.win_probability)}</td><td>{text(entry.handicap_rating)}</td><td>{pct(entry.agf_percent)}</td><td>{text(entry.weight_kg)}</td><td>{text(entry.jockey_name)}</td><td>{text(entry.trainer_name)}</td></tr>; })}</tbody></table></div></div>
        <aside className="bulletin-insights"><section><p className="eyebrow">{t.featured.toUpperCase()}</p><h2>{lead ? `${lead.program_number}. ${text(lead.horse_name)}` : t.unavailableData}</h2><strong>{pct(lead?.win_probability)}</strong><p>{lead?.strengths?.slice(0, 3).join(' Â· ') || t.unavailableData}</p></section><section><p className="eyebrow">{t.chaos.toUpperCase()}</p><h2>{number(value?.chaos_index ?? explanation?.chaos_index)?.toFixed(1) ?? '--'}/100</h2><p>{t.caution}</p></section><section><p className="eyebrow">{t.value.toUpperCase()}</p><h2>{valueLead ? `${valueLead.program_number}. ${text(valueLead.horse_name)}` : t.unavailableData}</h2><p>{valueLead ? `${pct(valueLead.edge_percentage_points)} model-AGF farkÄ±` : t.unavailableData}</p></section></aside>
      </section>
    </>}
  </main>;
}