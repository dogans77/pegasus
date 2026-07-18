type Race = {
  id: number;
  race_number: number;
  race_date: string;
  scheduled_time: string | null;
  distance_meters: number;
  surface: string;
  race_class: string | null;
  status: string;
  track: { name: string; city: string };
};

type Track = { id: number; name: string; city: string };

const api = "http://127.0.0.1:8000/api/v1";

async function getJson<T>(path: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(`${api}${path}`, { cache: "no-store" });
    return response.ok ? (await response.json()) as T : fallback;
  } catch {
    return fallback;
  }
}

export const dynamic = "force-dynamic";

export default async function Home() {
  const [races, tracks] = await Promise.all([
    getJson<Race[]>("/races/", []),
    getJson<Track[]>("/tracks/", []),
  ]);
  const apiReady = races.length > 0 || tracks.length > 0;

  return (
    <main>
      <section className="hero">
        <div>
          <p className="eyebrow">PEGASUS INTELLIGENCE PLATFORM</p>
          <h1>Yarışı tahmin etmekten önce, yarışı anlayın.</h1>
          <p className="sub">Form, piyasa, tempo ve risk sinyallerini tek kontrol panelinde birleştiren at yarışı analiz altyapısı.</p>
        </div>
        <div className={`connection ${apiReady ? "online" : "offline"}`}><span /> {apiReady ? "Canlı yarış verisi bağlı" : "Veri bağlantısı bekleniyor"}</div>
      </section>

      <section className="metrics">
        <article><span>Aktif yarış</span><strong>{races.length}</strong><small>Bugün sisteme aktarılan</small></article>
        <article><span>Hipodrom</span><strong>{tracks.length}</strong><small>Veri kaynaklarında tanımlı</small></article>
        <article><span>Model durumu</span><strong>v0.1</strong><small>Baseline intelligence</small></article>
        <article><span>Crawler</span><strong>{apiReady ? "Hazır" : "Bekliyor"}</strong><small>{apiReady ? "TJK günlük program aktarıldı" : "TJK aktarımı bekleniyor"}</small></article>
      </section>

      <section className="panel-grid">
        <article className="panel races">
          <div className="panel-head"><div><p className="eyebrow">GÜNLÜK PROGRAM</p><h2>Yarışlar</h2></div><span>{races.length} kayıt</span></div>
          {races.length ? <div className="race-list">{races.map((race) => <div className="race" key={race.id}><b>{race.track.city} · {race.race_number}. Koşu</b><span>{race.scheduled_time?.slice(0, 5) ?? "—"} · {race.distance_meters}m · {race.surface}</span><em>{race.status}</em></div>)}</div> : <div className="empty">Aktarılmış yarış bulunamadı.</div>}
        </article>
        <article className="panel intelligence"><p className="eyebrow">RACE INTELLIGENCE</p><h2>Model katmanı</h2><div className="score"><span>Chaos Index</span><strong>—</strong><small>Yarış girişleri geldiğinde hesaplanır</small></div><ul><li>Handikap puanı</li><li>AGF piyasa sinyali</li><li>Kilo avantajı</li><li>Olasılık sıralaması</li></ul></article>
      </section>
    </main>
  );
}