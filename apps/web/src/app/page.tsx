type Race={id:number;race_number:number;race_date:string;scheduled_time:string|null;distance_meters:number;surface:string;track:{name:string;city:string}};
type Entry={id?:number;entry_id?:number;program_number:number;horse_name:string|null;handicap_rating:number|null;agf_percent:number|null;weight_kg:number|null;win_probability?:number};
type Daily={race_id:number;city:string;race_number:number;scheduled_time:string|null;chaos_index:number;top_entry:Entry};
type Health={trained:boolean;deployed_model?:string;candidate_top1_accuracy?:number|null;handicap_benchmark_top1_accuracy?:number|null;decision?:string};
type Explanation={candidates:{program_number:number;strengths:{label:string;detail:string}[]}[]};
const api=process.env.PEGASUS_API_URL ?? 'http://127.0.0.1:8042/api/v1';
const t={live:'Canl\u0131 program',waiting:'Veri bekleniyor',todayDesk:'BUG\u00dcN\u00dcN YARI\u015e MASASI',headline:'Net sinyal, sakin karar.',intro:'Bug\u00fcn\u00fcn resmi program\u0131nda',races:'ko\u015fu',horses:'at',ready:'incelenmeye haz\u0131r. Yar\u0131\u015f kart\u0131ndan adaylar\u0131, riski ve piyasa ayr\u0131\u015fmas\u0131n\u0131 birlikte g\u00f6r.',featured:'\u00d6NE \u00c7IKAN KART',probability:'model olas\u0131l\u0131\u011f\u0131',open:'Kart\u0131 a\u00e7 \u2192',active:'Aktif ko\u015fu',entries:'At giri\u015fi',tracks:'Hipodrom',model:'Model kontrol\u00fc',todayCards:'Bug\u00fcn\u00fcn kartlar\u0131',readyText:'Haz\u0131r',daily:'RESM\u0130 G\u00dcNL\u00dcK PROGRAM',where:'Bug\u00fcn hangi hipodromlarda ko\u015fu var?',cards:'kart',empty:'Bug\u00fcn i\u00e7in aktar\u0131lm\u0131\u015f ko\u015fu bulunamad\u0131.',review:'Kart\u0131 incele',modelStatus:'MODEL DURUMU',test:'Zaman ayr\u0131ml\u0131 testte birinci aday isabeti.',result:'Model sonucu',benchmark:'Handikap referans\u0131',guide:'KISA REHBER',cityIstanbul:'\u0130stanbul',cityIzmir:'\u0130zmir',dot:'\u00b7',arrow:'\u2192'};
async function getJson<T>(path:string,fallback:T):Promise<T>{try{const response=await fetch(`${api}${path}`,{cache:'no-store'});return response.ok?await response.json() as T:fallback}catch{return fallback}}
function clean(value:string|null|undefined){let text=(value??'').replace(/\\u([0-9a-f]{4})/gi,(_,code)=>String.fromCharCode(parseInt(code,16)));for(let i=0;i<4;i+=1){if(!/[\u00c3\u00c2\u00e2]/.test(text))break;try{text=decodeURIComponent(escape(text))}catch{break}}return text}
function city(value:string){
 const name=clean(value);
 const labels:Record<string,string>={
  Istanbul:t.cityIstanbul,
  Izmir:t.cityIzmir,
  Elazig:'Elaz\u0131\u011f',
  Diyarbakir:'Diyarbak\u0131r'
 };
 return labels[name]??name
}
const entryKey=(entry:Entry,index:number)=>`${entry.entry_id??entry.id??entry.program_number}-${index}`;
export const dynamic='force-dynamic';
export default async function Home(){
 const [allRaces,health]=await Promise.all([getJson<Race[]>('/races/',[]),getJson<Health>('/decision/model-health',{trained:false})]);
 const localToday=new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Istanbul'}).format(new Date());
 const dates=[...new Set(allRaces.map(race=>race.race_date))].sort();
 const activeDate=dates.includes(localToday)?localToday:(dates.at(-1)??'');
 const races=allRaces.filter(race=>race.race_date===activeDate).sort((a,b)=>`${a.scheduled_time??''}-${a.track.city}`.localeCompare(`${b.scheduled_time??''}-${b.track.city}`));
 const cards=await Promise.all(races.map(async race=>({...race,entries:await getJson<Entry[]>(`/races/${race.id}/entries`,[])})));
 const daily=activeDate?await getJson<Daily[]>(`/races/daily-intelligence?race_date=${activeDate}`,[]):[];
 const dailyByRace=new Map(daily.map(item=>[item.race_id,item]));
 const featured=daily[0];
 const featuredExplanation=featured?await getJson<Explanation|null>(`/explanations/races/${featured.race_id}`,null):null;
 const featuredSignals=featuredExplanation?.candidates.find(item=>item.program_number===featured?.top_entry.program_number)?.strengths.slice(0,2)??[];
 const runnerCount=cards.reduce((total,card)=>total+card.entries.length,0);
 return <main className="dashboard-shell bright-dashboard">
  <header className="dashboard-nav"><a className="brand" href="/"><span>PEGASUS</span><small>RACE INTELLIGENCE</small></a><nav><a href="/program">Program</a><a href="/shortlist">K\u0131sa Liste</a><a href="/decision">Plan</a><a href="/coverage">Kapsam</a><a href="/model">Model</a><a href="/monitoring">\u0130zleme</a><a href="/performance">Performans</a><a href="/data-health">Veri</a></nav><div className="nav-meta"><span>{activeDate||'--'}</span><b className={races.length?'live':'idle'}>{races.length?t.live:t.waiting}</b></div></header>
  <section className="welcome"><div><p className="eyebrow">{t.todayDesk}</p><h1>{t.headline}</h1><p>{t.intro} <b>{races.length} {t.races}</b> {t.horses} <b>{runnerCount} {t.horses}</b> {t.ready}</p></div><aside className="today-highlight"><small>{t.featured}</small>{featured?<><b>{city(featured.city)} {t.dot} {featured.race_number}. {t.races}</b><strong>{featured.top_entry.program_number}. {clean(featured.top_entry.horse_name)}</strong><span>%{featured.top_entry.win_probability?.toFixed(1)??'--'} {t.probability}</span>{featuredSignals.length?<ul className="featured-signals">{featuredSignals.map((signal,index)=><li key={`${signal.label}-${index}`}>{clean(signal.label)}: {clean(signal.detail)}</li>)}</ul>:null}<a href={`/races/${featured.race_id}`}>{t.open}</a></>:<span>{t.waiting}</span>}</aside></section>
  <section className="signal-row"><article><span>{t.active}</span><strong>{races.length}</strong><small>{activeDate||'--'}</small></article><article><span>{t.entries}</span><strong>{runnerCount}</strong><small>{t.todayCards}</small></article><article><span>{t.tracks}</span><strong>{new Set(races.map(race=>race.track.city)).size}</strong><small>{[...new Set(races.map(race=>city(race.track.city)))].join(' \u00b7 ')||'--'}</small></article><article><span>{t.model}</span><strong>{health.trained?t.readyText:t.waiting}</strong><small>{clean(health.decision)||health.deployed_model||t.waiting}</small></article></section>
  <section className="workspace"><section className="panel race-board" id="program"><div className="panel-head"><div><p className="eyebrow">{t.daily}</p><h2>{t.where}</h2></div><span>{cards.length} {t.cards}</span></div>{cards.length?<div className="race-board-list">{cards.map(race=>{const intelligence=dailyByRace.get(race.id);return <a className="race-board-row" key={race.id} href={`/races/${race.id}`}><div className="race-time">{race.scheduled_time?.slice(0,5)??'--:--'}</div><div><b>{city(race.track.city)} {t.dot} {race.race_number}. {t.races}</b><small>{race.distance_meters}m {t.dot} {clean(race.surface)} {t.dot} {race.entries.length} {t.horses}</small></div><div className="runner-preview">{race.entries.slice(0,2).map((entry,index)=><span key={entryKey(entry,index)}>{entry.program_number}. {clean(entry.horse_name)}</span>)}</div><em>{intelligence?`Chaos ${intelligence.chaos_index}`:t.review} {t.arrow}</em></a>})}</div>:<div className="empty">{t.empty}</div>}</section><aside className="model-side" id="model"><article className="panel model-card"><p className="eyebrow">{t.modelStatus}</p><h2>{health.deployed_model??t.waiting}</h2><div className="model-score">%{Math.round((health.candidate_top1_accuracy??0)*100)}</div><p>{t.test}</p><dl><div><dt>{t.result}</dt><dd>{clean(health.decision)||t.waiting}</dd></div><div><dt>{t.benchmark}</dt><dd>%{Math.round((health.handicap_benchmark_top1_accuracy??0)*100)}</dd></div></dl></article><article className="panel guide-card"><p className="eyebrow">{t.guide}</p><ul><li><b>Chaos:</b> {clean('Yar\u0131\u015f ne kadar belirsiz?')}</li><li><b>Value:</b> {clean('Model ve AGF nerede ayr\u0131\u015f\u0131yor?')}</li><li><b>{t.races}:</b> {clean('Adaylar\u0131 ve gerek\u00e7eleri birlikte incele.')}</li></ul></article></aside></section>
 </main>
}