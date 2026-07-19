type Race = { id: number; race_number: number; race_date: string; scheduled_time: string | null; distance_meters: number; surface: string; track: { name: string; city: string } };
type Track = { id: number; name: string; city: string };
type Entry = { id?: number; entry_id?: number; program_number: number; horse_name: string | null; jockey_name?: string | null; handicap_rating: number | null; agf_percent: number | null; weight_kg: number | null; win_probability?: number };
type RaceCard = Race & { entries: Entry[] };
type DailySummary = { race_id: number; city: string; race_number: number; scheduled_time: string | null; chaos_index: number; method: string; top_entry: Entry };
type Performance = { evaluated_races: number; top1_accuracy: number | null; top3_coverage: number | null };
type ModelStatus = { trained: boolean; model_version?: string; metrics?: { top1_accuracy?: number | null; top3_coverage?: number | null } };
type ModelHealth = { trained: boolean; candidate_model?: string; deployed_model?: string; candidate_top1_accuracy?: number | null; handicap_benchmark_top1_accuracy?: number | null; decision?: string };

const api = "http://127.0.0.1:8042/api/v1";
const entryKey = (entry: Entry, index = 0) => `${entry.entry_id ?? entry.id ?? entry.program_number}-${index}`;

async function getJson<T>(path: string, fallback: T): Promise<T> {
  try { const response = await fetch(`${api}${path}`, { cache: "no-store" }); return response.ok ? (await response.json()) as T : fallback; } catch { return fallback; }
}

export const dynamic = "force-dynamic";

export default async function Home() {
  const [allRaces, tracks, performance, model, modelHealth] = await Promise.all([
    getJson<Race[]>("/races/", []), getJson<Track[]>("/tracks/", []),
    getJson<Performance>("/results/performance", { evaluated_races: 0, top1_accuracy: null, top3_coverage: null }),
    getJson<ModelStatus>("/ml/status", { trained: false }),
    getJson<ModelHealth>("/decision/model-health", { trained: false }),
  ]);
  const activeDate = allRaces.reduce((latest, race) => !latest || race.race_date > latest ? race.race_date : latest, "");
  const races = activeDate ? allRaces.filter((race) => race.race_date === activeDate) : [];
  const cards: RaceCard[] = await Promise.all(races.map(async (race) => ({ ...race, entries: await getJson<Entry[]>(`/races/${race.id}/entries`, []) })));
  const daily = activeDate ? await getJson<DailySummary[]>(`/races/daily-intelligence?race_date=${activeDate}`, []) : [];
  const featured = daily[0];
  const runnerCount = cards.reduce((total, card) => total + card.entries.length, 0);
  const statusText = races.length ? "Veri güncel" : "Veri bekleniyor";

  return <main className="dashboard-shell">
    <header className="dashboard-nav"><a className="brand" href="/"><span>PEGASUS</span><small>RACE INTELLIGENCE</small></a><div className="nav-meta"><span>{activeDate || "Tarih bekleniyor"}</span><b className={races.length ? "live" : "idle"}>{statusText}</b></div></header>
    <section className="decision-hero">
      <div><p className="eyebrow">GÜNLÜK KARAR MERKEZİ</p><h1>Yarışı anlamak, tahmin etmekten daha önemli.</h1><p>Form, piyasa ve risk sinyallerini tek bir sade kontrol panelinde takip edin.</p>{featured ? <a className="primary-action" href={`/races/${featured.race_id}`}>Günün ilk analizini aç <span>→</span></a> : <span className="primary-action disabled">Yarış kartı bekleniyor</span>}</div>
      <aside className="featured-card"><p>ÖNE ÇIKAN ANALİZ</p>{featured ? (<div className="featured-content"><b>{featured.city} · {featured.race_number}. Koşu</b><strong>{featured.top_entry.program_number}. {featured.top_entry.horse_name}</strong><div className="featured-probability"><span>Gösterge olasılığı</span><em>%{featured.top_entry.win_probability?.toFixed(1) ?? "--"}</em></div><small>Chaos {featured.chaos_index}/100 · {featured.scheduled_time?.slice(0, 5) ?? "--:--"}</small></div>) : (<span>Güncel yarış verisi alındığında burada görünecek.</span>)}</aside>
    </section>
    <section className="signal-row"><article><span>Güncel yarış</span><strong>{races.length}</strong><small>{runnerCount} at girişi</small></article><article><span>Hipodrom</span><strong>{tracks.length}</strong><small>Veri kaynağında tanımlı</small></article><article><span>Sonuç doğrulaması</span><strong>{performance.evaluated_races}</strong><small>Top 1: %{Math.round((performance.top1_accuracy ?? 0) * 100)}</small></article><article><span>Yayındaki karar modeli</span><strong>{modelHealth.deployed_model ?? model.model_version ?? "--"}</strong><small>{modelHealth.decision ?? "Model doğrulaması bekleniyor"}</small></article></section>
    <section className="workspace">
      <section className="panel race-board"><div className="panel-head"><div><p className="eyebrow">BUGÜNÜN PROGRAMI</p><h2>Yarış kartları</h2></div><span>{activeDate || "--"}</span></div>{cards.length ? <div className="race-board-list">{cards.map((race) => <a className="race-board-row" key={race.id} href={`/races/${race.id}`}><div><b>{race.track.city} · {race.race_number}. Koşu</b><small>{race.scheduled_time?.slice(0, 5) ?? "--:--"} · {race.distance_meters}m · {race.surface}</small></div><div className="runner-preview">{race.entries.slice(0, 3).map((entry, index) => <span key={entryKey(entry, index)}>{entry.program_number}. {entry.horse_name}</span>)}</div><em>{race.entries.length} at <i>→</i></em></a>)}</div> : <div className="empty">TJK programı aktarıldığında yarışlar burada görünecek.</div>}</section>
      <aside className="model-side"><article className="panel model-card"><p className="eyebrow">MODEL SAĞLIĞI</p><h2>{modelHealth.trained ? "Doğrulanmış karar" : "Model bekleniyor"}</h2><div className="model-score">{modelHealth.trained ? `%${Math.round((modelHealth.candidate_top1_accuracy ?? 0) * 100)}` : "--"}</div><p>Temporal test Top 1 isabet oranı</p><dl><div><dt>Aday model</dt><dd>{modelHealth.candidate_model ?? "--"}</dd></div><div><dt>Handikap referansı</dt><dd>%{Math.round((modelHealth.handicap_benchmark_top1_accuracy ?? 0) * 100)}</dd></div></dl></article><article className="panel guide-card"><p className="eyebrow">NASIL OKUNUR?</p><ul><li><b>Chaos:</b> Yarışın belirsizlik seviyesi.</li><li><b>Value:</b> Model ile AGF arasındaki ayrışma.</li><li><b>Kapsama:</b> Risk seviyesine göre aday sayısı.</li></ul></article></aside>
    </section>
  </main>;
}