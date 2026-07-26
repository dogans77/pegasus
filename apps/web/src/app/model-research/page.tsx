type Fold = {
  fold: number;
  train_through: string;
  test_through: string;
  evaluated_races: number;
  model_top1_accuracy: number | null;
  model_top3_coverage: number | null;
  handicap_top1_accuracy: number | null;
};

type Calibration = {
  bucket: string;
  entries: number;
  mean_predicted_probability: number;
  actual_win_rate: number;
};

type Research = {
  model_version: string;
  settled_races: number;
  folds: Fold[];
  average_model_top1_accuracy: number | null;
  average_handicap_top1_accuracy: number | null;
  model_beats_handicap_on_average: boolean;
  latest_fold_calibration: Calibration[];
  note: string;
};

export const dynamic = "force-dynamic";

const apiRoot = process.env.PEGASUS_API_URL ?? "http://127.0.0.1:8042/api/v1";
const num = (value: unknown) => Number(value ?? 0);
const pct = (value: unknown) => `%${(num(value) * 100).toFixed(1)}`;

async function getResearch(): Promise<{ data: Research | null; error: string | null }> {
  try {
    const response = await fetch(`${apiRoot}/ml/research`, { cache: "no-store" });
    if (!response.ok) return { data: null, error: `Araştırma raporu alınamadı (${response.status}).` };
    return { data: (await response.json()) as Research, error: null };
  } catch {
    return { data: null, error: "Model araştırma servisine bağlanılamadı." };
  }
}

export default async function ModelResearchPage() {
  const { data, error } = await getResearch();
  return (
    <main className="research-shell">
      <header className="research-head">
        <a href="/" className="back-link">← Programa dön</a>
        <p className="eyebrow">MODEL ARAŞTIRMA LABORATUVARI</p>
        <h1>Modeli test ederek geliştiriyoruz.</h1>
        <p className="research-copy">Bu ekran, modeli yalnızca geçmiş veride değil; zaman içinde sonraki yarışlar üzerinde de denetler.</p>
      </header>

      {!data ? <section className="research-empty">{error ?? "Rapor henüz hazır değil."}</section> : <>
        <section className="research-kpis">
          <article><span>Model sürümü</span><strong>{data.model_version}</strong><small>{data.settled_races} sonuçlanmış koşu</small></article>
          <article><span>Zaman ayrımlı isabet</span><strong>{pct(data.average_model_top1_accuracy)}</strong><small>Birinci aday başarısı</small></article>
          <article><span>Handikap referansı</span><strong>{pct(data.average_handicap_top1_accuracy)}</strong><small>Karşılaştırma tabanı</small></article>
          <article className={data.model_beats_handicap_on_average ? "positive" : "neutral"}><span>Model sonucu</span><strong>{data.model_beats_handicap_on_average ? "Önde" : "İzleniyor"}</strong><small>Referansa göre durum</small></article>
        </section>

        <section className="research-grid">
          <article className="research-card wide"><p className="eyebrow">ZAMANSAL TESTLER</p><h2>Geçmişe değil, sonraki yarışlara bakar.</h2>
            <div className="fold-list">{data.folds.map((fold) => <div className="fold-row" key={`${fold.fold}-${fold.test_through}`}><b>Test {fold.fold}</b><span>{fold.train_through} → {fold.test_through}</span><span>{fold.evaluated_races} koşu</span><strong>Model {pct(fold.model_top1_accuracy)}</strong><em>HP {pct(fold.handicap_top1_accuracy)}</em></div>)}</div>
          </article>
          <article className="research-card"><p className="eyebrow">KALİBRASYON</p><h2>Olasılık ile gerçek sonuç</h2>
            <div className="calibration-list">{data.latest_fold_calibration.map((item) => <div key={item.bucket}><span>{item.bucket}% bandı</span><b>Model %{num(item.mean_predicted_probability).toFixed(1)}</b><strong>Gerçek %{num(item.actual_win_rate).toFixed(1)}</strong></div>)}</div>
          </article>
        </section>
        <p className="research-note">{data.note}</p>
      </>}
    </main>
  );
}