type Report = {
  selected_shrinkage: number;
  tune_races: number;
  holdout_races: number;
  raw_holdout_brier: number;
  candidate_holdout_brier: number;
  raw_holdout_top1: number;
  candidate_holdout_top1: number;
  eligible_for_manual_promotion: boolean;
  note: string;
};

const tx = {
  back: "← Programa dön",
  eyebrow: "MODEL ARAŞTIRMA",
  title: "Kalibrasyon kontrolü",
  intro: "Olasılık modelini yayına almak için ayrılmış zaman penceresinde yapılan bağımsız test.",
  unavailable: "Kalibrasyon raporu henüz hazır değil.",
  raw: "Mevcut model",
  candidate: "Kalibrasyon adayı",
  brier: "Brier skoru",
  top1: "Birinci aday isabeti",
  tune: "Ayar yarışları",
  holdout: "Görülmemiş test yarışları",
  shrinkage: "Seçilen yumuşatma",
  approved: "Manuel inceleme için uygun",
  blocked: "Yayına alma eşiğini geçmedi",
  warning: "Bu ekran model değiştirmez. Sonuç, bahis veya getiri vaadi değildir.",
};

async function getReport(): Promise<Report | null> {
  const base = process.env.PEGASUS_API_URL ?? "http://127.0.0.1:8042/api/v1";
  try {
    const response = await fetch(`${base}/ml/calibration-promotion`, { cache: "no-store" });
    if (!response.ok) return null;
    return (await response.json()) as Report;
  } catch { return null; }
}

function pct(value: number) { return `%${(value * 100).toFixed(1)}`; }
function score(value: number) { return value.toFixed(4); }

export default async function CalibrationPage() {
  const report = await getReport();
  return <main className="page-shell">
    <nav className="topbar"><a href="/">{tx.back}</a></nav>
    <section className="hero compact"><p className="eyebrow">{tx.eyebrow}</p><h1>{tx.title}</h1><p>{tx.intro}</p></section>
    {!report ? <section className="empty"><strong>{tx.unavailable}</strong><p>{tx.warning}</p></section> : <>
      <section className={`status-card ${report.eligible_for_manual_promotion ? "pass" : "review"}`}>
        <p className="eyebrow">GATE</p><h2>{report.eligible_for_manual_promotion ? tx.approved : tx.blocked}</h2><p>{report.note}</p>
      </section>
      <section className="metrics-grid">
        <article><p>{tx.raw}</p><strong>{score(report.raw_holdout_brier)}</strong><small>{tx.brier}</small><b>{pct(report.raw_holdout_top1)}</b><small>{tx.top1}</small></article>
        <article><p>{tx.candidate}</p><strong>{score(report.candidate_holdout_brier)}</strong><small>{tx.brier}</small><b>{pct(report.candidate_holdout_top1)}</b><small>{tx.top1}</small></article>
        <article><p>{tx.shrinkage}</p><strong>{report.selected_shrinkage.toFixed(2)}</strong><small>{tx.tune}: {report.tune_races}</small><b>{report.holdout_races}</b><small>{tx.holdout}</small></article>
      </section>
      <p className="disclaimer">{tx.warning}</p>
    </>}
  </main>;
}