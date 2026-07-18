"use client";

import { useEffect, useState } from "react";

type Race = { id: number; race_number: number; race_date: string; distance_meters: number; surface: string; status: string; track: { name: string; city: string } };
type Track = { id: number; name: string; city: string };

const apiOrigin = process.env.NEXT_PUBLIC_API_ORIGIN ?? "http://127.0.0.1:8000";
const api = `${apiOrigin}/api/v1`;

export default function Home() {
  const [races, setRaces] = useState<Race[]>([]);
  const [tracks, setTracks] = useState<Track[]>([]);
  const [online, setOnline] = useState(false);
  const [message, setMessage] = useState("Veri baÄŸlantÄ±sÄ± bekleniyor");

  useEffect(() => {
    Promise.all([
      fetch(`${apiOrigin}/health`).then((r) => r.ok),
      fetch(`${api}/races/`).then((r) => r.ok ? r.json() : []),
      fetch(`${api}/tracks/`).then((r) => r.ok ? r.json() : []),
    ]).then(([healthy, nextRaces, nextTracks]) => {
      setOnline(Boolean(healthy));
      setRaces(nextRaces);
      setTracks(nextTracks);
      setMessage(healthy ? "API baÄŸlantÄ±sÄ± aktif" : "API baÄŸlantÄ±sÄ± kurulamadÄ±");
    }).catch(() => setMessage("API baÅŸlatÄ±ldÄ±ÄŸÄ±nda canlÄ± veriler burada gÃ¶rÃ¼necek"));
  }, []);

  return (
    <main>
      <section className="hero">
        <div>
          <p className="eyebrow">PEGASUS INTELLIGENCE PLATFORM</p>
          <h1>YarÄ±ÅŸÄ± tahmin etmekten Ã¶nce, yarÄ±ÅŸÄ± anlayÄ±n.</h1>
          <p className="sub">Form, piyasa, tempo ve risk sinyallerini tek kontrol panelinde birleÅŸtiren at yarÄ±ÅŸÄ± analiz altyapÄ±sÄ±.</p>
        </div>
        <div className={`connection ${online ? "online" : "offline"}`}><span /> {message}</div>
      </section>

      <section className="metrics">
        <article><span>Aktif yarÄ±ÅŸ</span><strong>{races.length}</strong><small>BugÃ¼n sisteme aktarÄ±lan</small></article>
        <article><span>Hipodrom</span><strong>{tracks.length}</strong><small>Veri kaynaklarÄ±nda tanÄ±mlÄ±</small></article>
        <article><span>Model durumu</span><strong>v0.1</strong><small>Baseline intelligence</small></article>
        <article><span>Crawler</span><strong>{online ? "HazÄ±r" : "Bekliyor"}</strong><small>TJK manuel iÃ§e aktarÄ±m</small></article>
      </section>

      <section className="panel-grid">
        <article className="panel races"><div className="panel-head"><div><p className="eyebrow">GÃœNLÃœK PROGRAM</p><h2>YarÄ±ÅŸlar</h2></div><span>{races.length} kayÄ±t</span></div>
          {races.length ? <div className="race-list">{races.map((race) => <div className="race" key={race.id}><b>{race.race_number}. KoÅŸu</b><span>{race.track.city} Â· {race.distance_meters}m {race.surface}</span><em>{race.status}</em></div>)}</div> : <div className="empty">TJK programÄ± iÃ§e aktarÄ±ldÄ±ÄŸÄ±nda yarÄ±ÅŸlar burada gÃ¶rÃ¼necek.</div>}
        </article>
        <article className="panel intelligence"><p className="eyebrow">RACE INTELLIGENCE</p><h2>Model katmanÄ±</h2><div className="score"><span>Chaos Index</span><strong>â€”</strong><small>YarÄ±ÅŸ giriÅŸleri geldiÄŸinde hesaplanÄ±r</small></div><ul><li>Handikap puanÄ±</li><li>AGF piyasa sinyali</li><li>Kilo avantajÄ±</li><li>OlasÄ±lÄ±k sÄ±ralamasÄ±</li></ul></article>
      </section>
    </main>
  );
}
