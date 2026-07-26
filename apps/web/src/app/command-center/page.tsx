type Track={name?:string|null};
type Race={id:number;race_number?:number|null;scheduled_time?:string|null;start_time?:string|null;distance_meters?:number|null;surface?:string|null;track?:Track|null;entry_count?:number|null};
type Safety={state?:string;can_publish_actionable_scenarios?:boolean;verified_race_dates?:number;minimum_race_dates?:number;reason?:string};
type Performance={evaluated_races?:number;top1_accuracy?:number|null;top3_coverage?:number|null};
type Candidate={race_id?:number|string|null;horse_name?:string|null;program_number?:number|string|null;win_probability?:number|string|null};
type DailyRecommendation={race_id?:number|string|null;primary?:Candidate|null;top_entry?:Candidate|null;ranked_entries?:Candidate[];candidates?:Candidate[]};

export const dynamic='force-dynamic';
const api=process.env.PEGASUS_API_URL||process.env.NEXT_PUBLIC_API_URL||'http://127.0.0.1:8042/api/v1';
const t={
 title:'Yar\u0131\u015f g\u00fcn\u00fc merkezi',lead:'Resmi program, veri g\u00fcncelli\u011fi ve performans takibi tek yerde.',today:'BUG\u00dcN',program:'Program',performance:'Performans',bulletin:'B\u00fclten',details:'Yar\u0131\u015f kart\u0131',races:'Ko\u015fu',runners:'At giri\u015fi',tracks:'Hipodrom',model:'Model durumu',ready:'\u0130nceleme haz\u0131r',review:'Model inceleme modunda',waiting:'Resmi program bekleniyor',official:'Resmi veri aktar\u0131m\u0131',updated:'Son g\u00fcncelleme',top1:'Birinci aday isabeti',top3:'\u0130lk \u00fc\u00e7 kapsama',evaluated:'De\u011ferlendirilen ko\u015fu',source:'Model, do\u011frulanm\u0131\u015f sonu\u00e7 e\u015fi\u011fi tamamlanmadan eyleme d\u00f6n\u00fc\u015fmez.',open:'Kart\u0131 a\u00e7',noRaces:'Bug\u00fcn i\u00e7in aktar\u0131lm\u0131\u015f ko\u015fu bulunamad\u0131.',now:'CANLI G\u00dcNL\u00dcK G\u00d6R\u00dcN\u00dcM',all:'T\u00fcm hipodromlar',candidates:'Model s\u0131ralamas\u0131',unavailable:'Veri bekleniyor'
};
async function getJson<T>(path:string,fallback:T):Promise<T>{try{const response=await fetch(`${api}${path}`,{cache:'no-store'});return response.ok?await response.json() as T:fallback}catch{return fallback}}
function list<T>(value:unknown):T[]{if(Array.isArray(value))return value as T[];const object=value as {items?:T[];races?:T[];recommendations?:T[]};return object.items||object.races||object.recommendations||[]}
function text(value:unknown){return value===null||value===undefined||value===''?'--':String(value)}
function pct(value:unknown){const n=Number(value);return Number.isFinite(n)&&n>0?`%${n<=1?(n*100).toFixed(1):n.toFixed(1)}`:'--'}
function track(race:Race){return text(race.track?.name).trim()}
function time(race:Race){return text(race.scheduled_time??race.start_time)}
function cityCount(races:Race[]){return Array.from(new Set(races.map(track).filter(item=>item!=='--'))).length}

export default async function CommandCenter(){
 const today=new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Istanbul'}).format(new Date());
 const [rawBoard,safety,performance,rawRecommendations]=await Promise.all([
  getJson<{races?:Race[]}>(`/analytics/current-day-board?race_date=${today}`,{races:[]}),
  getJson<Safety>('/analytics/model-safety?refresh=true',{state:'review',can_publish_actionable_scenarios:false,verified_race_dates:0,minimum_race_dates:20}),
  getJson<Performance>('/results/performance',{evaluated_races:0,top1_accuracy:null,top3_coverage:null}),
  getJson<unknown>(`/recommendations/daily?race_date=${today}`,[])
 ]);
 const races=list<Race>(rawBoard.races).sort((a,b)=>`${time(a)}`.localeCompare(`${time(b)}`)||Number(a.race_number??999)-Number(b.race_number??999));
 const recommendations=list<DailyRecommendation>(rawRecommendations);
 const runners=races.reduce((sum,race)=>sum+Number(race.entry_count??0),0);
 const safetyReady=Boolean(safety.can_publish_actionable_scenarios);
 const featured=(race:Race)=>{const record=recommendations.find(item=>Number(item.race_id)===race.id);return record?.primary||record?.top_entry||record?.ranked_entries?.[0]||record?.candidates?.[0]||null};
 return <main className="cc-shell">
  <header className="cc-nav"><a className="cc-brand" href="/"><span className="cc-mark">P</span><span>PEGASUS<small>RACE INTELLIGENCE</small></span></a><nav><a href="/command-center">{t.program}</a><a href="/performance">{t.performance}</a><a href="/bulletin">{t.bulletin}</a></nav><a className="cc-status" href="/data-health"><i></i>{t.official}</a></header>
  <section className="cc-hero"><div><p className="eyebrow">{t.now}</p><h1>{t.title}</h1><p>{t.lead}</p><div className="cc-actions"><a className="cc-primary" href="#program">{t.program}</a><a className="cc-secondary" href="/performance">{t.performance}</a></div></div><aside className="cc-trust"><p className="eyebrow">{t.model.toUpperCase()}</p><h2>{safetyReady?t.ready:t.review}</h2><strong>{safety.verified_race_dates??0}/{safety.minimum_race_dates??20}</strong><p>{safetyReady?t.candidates:safety.reason||t.source}</p></aside></section>
  <section className="cc-metrics"><article><span>{t.races}</span><strong>{races.length}</strong><small>{today}</small></article><article><span>{t.runners}</span><strong>{runners||'--'}</strong><small>{t.official}</small></article><article><span>{t.tracks}</span><strong>{cityCount(races)}</strong><small>{t.all}</small></article><article><span>{t.top1}</span><strong>{pct(performance.top1_accuracy)}</strong><small>{performance.evaluated_races??0} {t.evaluated}</small></article></section>
  <section id="program" className="cc-program"><div className="cc-heading"><div><p className="eyebrow">{t.today}</p><h2>{t.program}</h2></div><a href="/bulletin">{t.bulletin} \u2192</a></div>{races.length?<div className="cc-race-list">{races.map(race=>{const top=featured(race);return <article key={race.id} className="cc-race-card"><div className="cc-race-number">{race.race_number??'--'}</div><div className="cc-race-main"><b>{track(race)}</b><span>{time(race)} \u00b7 {race.distance_meters??'--'}m \u00b7 {text(race.surface)}</span></div><div className="cc-race-signal">{safetyReady&&top?<><small>{t.candidates}</small><b>{text(top.program_number)}. {text(top.horse_name)}</b><span>{pct(top.win_probability)}</span></>:<><small>{t.model}</small><b>{t.review}</b><span>{t.unavailable}</span></>}</div><a className="cc-open" href={`/races/${race.id}`}>{t.open} \u2192</a></article>})}</div>:<div className="cc-empty"><h3>{t.noRaces}</h3><p>{t.updated}: {today}</p></div>}</section>
  <section className="cc-footnote"><span className="cc-horse" aria-hidden="true">\u265E</span><p>{t.source}</p><a href="/data-health">{t.updated} \u2192</a></section>
 </main>
}