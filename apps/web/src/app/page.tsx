type Race = { id: number; race_number: number; race_date: string; scheduled_time: string | null; distance_meters: number; surface: string; track: { name: string; city: string } };
type Track = { id: number; name: string; city: string };
type Entry = { id?: number; program_number: number; barrier?: number | null; weight_kg: number | null; handicap_rating: number | null; agf_percent: number | null; horse_name: string | null; jockey_name?: string | null; score?: number; win_probability?: number };
type RaceCard = Race & { entries: Entry[] };
type Intelligence = { race_id: number; chaos_index: number; method: string; entries: Entry[] };
type DailySummary = { race_id: number; city: string; race_number: number; scheduled_time: string | null; chaos_index: number; method: string; top_entry: Entry };
// PEGASUS_PERFORMANCE_DASHBOARD
// PEGASUS_RACE_DETAIL_LINKS
type Performance = { evaluated_races: number; top1_accuracy: number | null; top3_coverage: number | null };
type ModelStatus = { trained: boolean; model_version?: string; metrics?: { top1_accuracy?: number | null; top3_coverage?: number | null } };

const api = "http://127.0.0.1:8042/api/v1";
const copy = {
  title: "Yar\u0131\u015f\u0131 tahmin etmekten \u00f6nce, yar\u0131\u015f\u0131 anlay\u0131n.",
  subtitle: "Form, piyasa, tempo ve risk sinyallerini tek kontrol panelinde birle\u015ftiren at yar\u0131\u015f\u0131 analiz altyap\u0131s\u0131.",
  connected: "Canl\u0131 yar\u0131\u015f verisi ba\u011fl\u0131", waiting: "Veri ba\u011flant\u0131s\u0131 bekleniyor", active: "Aktif yar\u0131\u015f", imported: "Bug\u00fcn sisteme aktar\u0131lan",
  entries: "At giri\u015fi", parsed: "Yar\u0131\u015f kart\u0131ndan ayr\u0131\u015ft\u0131r\u0131lan", tracks: "Hipodrom", source: "Veri kaynaklar\u0131nda tan\u0131ml\u0131",
  crawler: "Crawler", ready: "Haz\u0131r", waitingShort: "Bekliyor", importedProgram: "TJK program\u0131 ve at giri\u015fleri aktar\u0131ld\u0131", importWaiting: "TJK aktar\u0131m\u0131 bekleniyor",
  program: "G\u00dcNL\u00dcK PROGRAM", cards: "Yar\u0131\u015f kartlar\u0131", race: "Ko\u015fu", empty: "Aktar\u0131lm\u0131\u015f yar\u0131\u015f bulunamad\u0131.",
  daily: "G\u00dcN\u00dcN BASELINE \u00d6ZET\u0130", chaos: "Chaos", probability: "G\u00f6sterge olas\u0131l\u0131\u011f\u0131", hp: "HP", agf: "AGF", weight: "Kilo", dot: "\u00b7", dash: "\u2014",
  model: "MODEL", trained: "Temporal test", card: "KO\u015eU KARTI", waitEntries: "Yar\u0131\u015f giri\u015fleri geldi\u011finde hesaplan\u0131r", performance: "PERFORMANS", top1: "Top 1 isabet", top3: "ilk 3 kapsama", awaitingResults: "Resmi sonuc bekleniyor",
};

async function getJson<T>(path: string, fallback: T): Promise<T> {
  try { const response = await fetch(`${api}${path}`, { cache: "no-store" }); return response.ok ? (await response.json()) as T : fallback; } catch { return fallback; }
}

export const dynamic = "force-dynamic";

export default async function Home() {
  const [allRaces, tracks, performance, model] = await Promise.all([getJson<Race[]>("/races/", []), getJson<Track[]>("/tracks/", []), getJson<Performance>("/results/performance", { evaluated_races: 0, top1_accuracy: null, top3_coverage: null }), getJson<ModelStatus>("/ml/status", { trained: false })]);
  // PEGASUS_ACTIVE_RACE_DAY: show the newest card set; historical data stays available through detail links and APIs.
  const activeRaceDate = allRaces.reduce((latest, race) => !latest || race.race_date > latest ? race.race_date : latest, "");
  const races = activeRaceDate ? allRaces.filter((race) => race.race_date === activeRaceDate) : [];
  const raceCards: RaceCard[] = await Promise.all(races.map(async (race) => ({ ...race, entries: await getJson<Entry[]>(`/races/${race.id}/entries`, []) })));
  const runnerCount = raceCards.reduce((total, race) => total + race.entries.length, 0);
  const raceDate = races[0]?.race_date;
  const daily = raceDate ? await getJson<DailySummary[]>(`/races/daily-intelligence?race_date=${raceDate}`, []) : [];
  const featuredRace = raceCards[0];
  const intelligence = featuredRace ? await getJson<Intelligence | null>(`/races/${featuredRace.id}/intelligence`, null) : null;
  const featuredEntries = intelligence?.entries ?? [];
  const apiReady = races.length > 0 || tracks.length > 0;

  return <main>
    <section className="hero"><div><p className="eyebrow">PEGASUS INTELLIGENCE PLATFORM</p><h1>{copy.title}</h1><p className="sub">{copy.subtitle}</p></div><div className={`connection ${apiReady ? "online" : "offline"}`}><span /> {apiReady ? copy.connected : copy.waiting}</div></section>
    <section className="metrics"><article><span>{copy.active}</span><strong>{races.length}</strong><small>{copy.imported}</small></article><article><span>{copy.entries}</span><strong>{runnerCount}</strong><small>{copy.parsed}</small></article><article><span>{copy.tracks}</span><strong>{tracks.length}</strong><small>{copy.source}</small></article><article><span>{copy.crawler}</span><strong>{apiReady ? copy.ready : copy.waitingShort}</strong><small>{apiReady ? copy.importedProgram : copy.importWaiting}</small></article><article><span>{copy.performance}</span><strong>{performance.evaluated_races ? `%${performance.top1_accuracy ?? 0}` : copy.dash}</strong><small>{performance.evaluated_races ? `${copy.top1} ${copy.dot} ${copy.top3} %${performance.top3_coverage ?? 0}` : copy.awaitingResults}</small></article><article><span>{copy.model}</span><strong>{model.trained ? `%${Math.round((model.metrics?.top1_accuracy ?? 0) * 100)}` : copy.dash}</strong><small>{model.trained ? `${model.model_version} ${copy.dot} ${copy.trained}` : copy.awaitingResults}</small></article></section>
    {daily.length ? <section className="daily-strip"><div className="panel-head"><div><p className="eyebrow">{copy.daily}</p><h2>Race Intelligence</h2></div><span>{daily.length} {copy.race.toLowerCase()}</span></div><div className="daily-grid">{daily.map((item) => <article className="daily-pick" key={item.race_id}><small>{item.city} {copy.dot} {item.race_number}. {copy.race}</small><b>{item.top_entry.program_number}. {item.top_entry.horse_name}</b><span>{copy.probability} %{item.top_entry.win_probability?.toFixed(1) ?? copy.dash}</span><em>{copy.chaos} {item.chaos_index}/100</em></article>)}</div></section> : null}
    <section className="panel-grid"><article className="panel races"><div className="panel-head"><div><p className="eyebrow">{copy.program}</p><h2>{copy.cards}</h2></div><span>{races.length} {copy.race.toLowerCase()} {copy.dot} {runnerCount} at</span></div>{raceCards.length ? <div className="race-list">{raceCards.map((race) => <a className="race race-link" key={race.id} href={`/races/${race.id}`}><b>{race.track.city} {copy.dot} {race.race_number}. {copy.race}</b><span>{race.scheduled_time?.slice(0, 5) ?? copy.dash} {copy.dot} {race.distance_meters}m {copy.dot} {race.surface}</span><em>{race.entries.length} at</em></a>)}</div> : <div className="empty">{copy.empty}</div>}</article>
    <article className="panel intelligence"><p className="eyebrow">{copy.card}</p><h2>{featuredRace ? `${featuredRace.track.city} ${copy.dot} ${featuredRace.race_number}. ${copy.race}` : "Race Intelligence"}</h2><div className="score"><span>{copy.chaos}</span><strong>{intelligence ? `${intelligence.chaos_index}/100` : copy.dash}</strong><small>{intelligence?.method ?? copy.waitEntries}</small></div>{featuredEntries.length ? <div className="entry-list">{featuredEntries.slice(0, 6).map((entry) => <div className="entry" key={entry.id}><b>{entry.program_number}. {entry.horse_name}</b><span>{entry.jockey_name ?? copy.dash}</span><small>{copy.hp} {entry.handicap_rating ?? copy.dash} {copy.dot} {copy.agf} %{entry.agf_percent ?? copy.dash} {copy.dot} {copy.weight} {entry.weight_kg ?? copy.dash} {copy.dot} {copy.probability} %{entry.win_probability?.toFixed(1) ?? copy.dash}</small></div>)}</div> : <div className="empty">{copy.waitEntries}</div>}</article></section>
  </main>;
}