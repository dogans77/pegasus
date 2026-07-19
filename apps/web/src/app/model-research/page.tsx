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
    if (!response.ok) return { data: null, error: `Ara\u015ft\u0131rma raporu al\u0131namad\u0131 (${response.status}).` };
    return { data: (await response.json()) as Research, error: null };
  } catch {
    return { data: null, error: "Model ara\u015ft\u0131rma servisine ba\u011flan\u0131lamad\u0131." };
  }
}

export default async function ModelResearchPage() {
  const { data, error } = await getResearch();
  return (
    <main className="research-shell">
      <header className="research-head">
        <a href="/" className="back-link">\u2190 Programa d\u00f6n</a>
        <p className="eyebrow">MODEL ARA\u015eTIRMA LABORATUVARI</p>
        <h1>Modeli test ederek geli\u015ftiriyoruz.</h1>
        <p className="research-copy">Bu ekran, modeli yaln\u0131zca ge\u00e7mi\u015f veride de\u011fil; zaman i\u00e7inde sonraki yar\u0131\u015flar \u00fczerinde de denetler.</p>
      </header>

      {!data ? <section className="research-empty">{error ?? "Rapor hen\u00fcz haz\u0131r de\u011fil."}</section> : <>
        <section className="research-kpis">
          <article><span>Model s\u00fcr\u00fcm\u00fc</span><strong>{data.model_version}</strong><small>{data.settled_races} sonu\u00e7lanm\u0131\u015f ko\u015fu</small></article>
          <article><span>Zaman ayr\u0131ml\u0131 isabet</span><strong>{pct(data.average_model_top1_accuracy)}</strong><small>Birinci aday ba\u015far\u0131s\u0131</small></article>
          <article><span>Handikap referans\u0131</span><strong>{pct(data.average_handicap_top1_accuracy)}</strong><small>Kar\u015f\u0131la\u015ft\u0131rma taban\u0131</small></article>
          <article className={data.model_beats_handicap_on_average ? "positive" : "neutral"}><span>Model sonucu</span><strong>{data.model_beats_handicap_on_average ? "\u00d6nde" : "\u0130zleniyor"}</strong><small>Referansa g\u00f6re durum</small></article>
        </section>

        <section className="research-grid">
          <article className="research-card wide"><p className="eyebrow">ZAMANSAL TESTLER</p><h2>Ge\u00e7mi\u015fe de\u011fil, sonraki yar\u0131\u015flara bakar.</h2>
            <div className="fold-list">{data.folds.map((fold) => <div className="fold-row" key={`${fold.fold}-${fold.test_through}`}><b>Test {fold.fold}</b><span>{fold.train_through} \u2192 {fold.test_through}</span><span>{fold.evaluated_races} ko\u015fu</span><strong>Model {pct(fold.model_top1_accuracy)}</strong><em>HP {pct(fold.handicap_top1_accuracy)}</em></div>)}</div>
          </article>
          <article className="research-card"><p className="eyebrow">KAL\u0130BRASYON</p><h2>Olas\u0131l\u0131k ile ger\u00e7ek sonu\u00e7</h2>
            <div className="calibration-list">{data.latest_fold_calibration.map((item) => <div key={item.bucket}><span>{item.bucket}% band\u0131</span><b>Model %{num(item.mean_predicted_probability).toFixed(1)}</b><strong>Ger\u00e7ek %{num(item.actual_win_rate).toFixed(1)}</strong></div>)}</div>
          </article>
        </section>
        <p className="research-note">{data.note}</p>
      </>}
    </main>
  );
}