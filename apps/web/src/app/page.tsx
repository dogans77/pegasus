"use client";

import { useEffect, useState } from "react";

type Race = {
  id: number;
  race_number: number;
  race_date: string;
  distance_meters: number;
  surface: string;
  status: string;
  track: { name: string; city: string };
};

type Track = { id: number; name: string; city: string };

const apiOrigin = "/backend";
const api = `${apiOrigin}/api/v1`;

export default function Home() {
  const [races, setRaces] = useState<Race[]>([]);
  const [tracks, setTracks] = useState<Track[]>([]);
  const [online, setOnline] = useState(false);
  const [message, setMessage] = useState("Veri bağlantısı bekleniyor");

  useEffect(() => {
    Promise.all([
      fetch(`${apiOrigin}/health`).then((response) => response.ok),
      fetch(`${api}/races/`).then((response) => response.ok ? response.json() : []),
      fetch(`${api}/tracks/`).then((response) => response.ok ? response.json() : []),
    ])
      .then(([healthy, nextRaces, nextTracks]) => {
        setOnline(Boolean(healthy));
        setRaces(nextRaces);
        setTracks(nextTracks);
        setMessage(healthy ? "API bağlantısı aktif" : "API bağlantısı kurulamadı");
      })
      .catch(() => setMessage("API başlatıldığında canlı veriler burada görünecek"));
  }, []);

  return (
    <main>
      <section className="hero">
        <div>
          <p className="eyebrow">PEGASUS INTELLIGENCE PLATFORM</p>
          <h1>Yarışı tahmin etmekten önce, yarışı anlayın.</h1>
          <p className="sub">
            Form, piyasa, tempo ve risk sinyallerini tek kontrol panelinde birleştiren
            at yarışı analiz altyapısı.
          </p>
        </div>
        <div className={`connection ${online ? "online" : "offline"}`}>
          <span /> {message}
        </div>
      </section>

      <section className="metrics">
        <article><span>Aktif yarış</span><strong>{races.length}</strong><small>Bugün sisteme aktarılan</small></article>
        <article><span>Hipodrom</span><strong>{tracks.length}</strong><small>Veri kaynaklarında tanımlı</small></article>
        <article><span>Model durumu</span><strong>v0.1</strong><small>Baseline intelligence</small></article>
        <article><span>Crawler</span><strong>{online ? "Hazır" : "Bekliyor"}</strong><small>TJK manuel içe aktarım</small></article>
      </section>

      <section className="panel-grid">
        <article className="panel races">
          <div className="panel-head">
            <div><p className="eyebrow">GÜNLÜK PROGRAM</p><h2>Yarışlar</h2></div>
            <span>{races.length} kayıt</span>
          </div>
          {races.length ? (
            <div className="race-list">
              {races.map((race) => (
                <div className="race" key={race.id}>
                  <b>{race.race_number}. Koşu</b>
                  <span>{race.track.city} · {race.distance_meters}m {race.surface}</span>
                  <em>{race.status}</em>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty">TJK programı içe aktarıldığında yarışlar burada görünecek.</div>
          )}
        </article>

        <article className="panel intelligence">
          <p className="eyebrow">RACE INTELLIGENCE</p>
          <h2>Model katmanı</h2>
          <div className="score">
            <span>Chaos Index</span>
            <strong>—</strong>
            <small>Yarış girişleri geldiğinde hesaplanır</small>
          </div>
          <ul>
            <li>Handikap puanı</li>
            <li>AGF piyasa sinyali</li>
            <li>Kilo avantajı</li>
            <li>Olasılık sıralaması</li>
          </ul>
        </article>
      </section>
    </main>
  );
}