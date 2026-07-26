type Race = { id:number; race_number?:number|null; scheduled_time?:string|null; start_time?:string|null; distance_meters?:number|null; surface?:string|null; track?:{name?:string|null}|null };
type Entry = { id:number; program_number?:number|null; horse_id?:number|null; horse_name?:string|null; jockey_name?:string|null; trainer_name?:string|null; weight_kg?:number|string|null; handicap_rating?:number|string|null; agf_percent?:number|string|null };
type Candidate = { program_number?:number|null; horse_name?:string|null; win_probability?:number|string|null };
type Daily = { race_id?:number|string|null; ranked_entries?:Candidate[]; candidates?:Candidate[]; alternatives?:Candidate[]; primary?:Candidate|null; top_entry?:Candidate|null };
type Safety = { can_publish_actionable_scenarios?:boolean; state?:string; verified_race_dates?:number; minimum_race_dates?:number; reason?:string };

export const dynamic = 'force-dynamic';
const api = process.env.PEGASUS_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8042/api/v1';
const t = {
  title:'\u00d6zenli g\u00fcnl\u00fck b\u00fclten', intro:'Resmi program, ko\u015fu kart\u0131 ve veri durumu tek ekranda.', today:'Bug\u00fcn', city:'Hipodrom', race:'Ko\u015fu', runners:'at',
  no:'No', horse:'At', model:'Model', hp:'HP', agf:'AGF', weight:'Kilo', jockey:'Jokey', trainer:'Antren\u00f6r', card:'Ko\u015fu kart\u0131', details:'Detayl\u0131 incele',
  source:'Kaynak: resmi program aktar\u0131m\u0131', back:'Programa d\u00f6n', unavailable:'Bug\u00fcn i\u00e7in aktar\u0131lm\u0131\u015f resmi program bulunamad\u0131.', waiting:'G\u00fcncel program aktar\u0131ld\u0131\u011f\u0131nda b\u00fclten burada g\u00f6r\u00fcnecek.',
  review:'Model inceleme modunda', safety:'Do\u011frulanm\u0131\u015f sonu\u00e7 ve kalibrasyon e\u015fi\u011fi tamamlanmadan aday, kupon ve aksiyon i\u00e7eri\u011fi g\u00f6sterilmez.', profile:'At profili', unavailableMarket:'AGF verisi hen\u00fcz aktar\u0131lmad\u0131', caution:'Bu ekran bilgi ve olas\u0131l\u0131k tabanl\u0131 karar deste\u011fidir; kesin sonu\u00e7 iddias\u0131 ta\u015f\u0131maz.'
};
async function getJson<T>(path:string, fallback:T):Promise<T>{try{const response=await fetch(`${api}${path}`,{cache:'no-store'});return response.ok?await response.json() as T:fallback}catch{return fallback}}
function list<T>(value:unknown):T[]{if(Array.isArray(value)) return value as T[];const object=value as {items?:T[];races?:T[];recommendations?:T[]};return object.items||object.races||object.recommendations||[]}
function text(value:unknown){return value===null||value===undefined||value===''?'--':String(value)}
function num(value:unknown){const parsed=Number(value);return Number.isFinite(parsed)?parsed:null}
function percent(value:unknown){const parsed=num(value);return parsed===null||parsed<=0?'--':`%${parsed.toFixed(1)}`}
function city(race:Race){return text(race.track?.name).replace(/\s+/g,' ').trim()}
function raceTime(race:Race){return text(race.scheduled_time??race.start_time)}

export default async function Bulletin({searchParams}:{searchParams:Promise<{city?:string;race?:string}>}){
  const query=await searchParams;
  const today=new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Istanbul'}).format(new Date());
  const board=await getJson<{races?:Race[]}>(`/analytics/current-day-board?race_date=${today}`,{races:[]});
  const races=list<Race>(board.races).sort((a,b)=>(a.race_number??999)-(b.race_number??999));
  const cities=Array.from(new Set(races.map(city).filter((item)=>item!=='--'))).sort((a,b)=>a.localeCompare(b,'tr'));
  const selectedCity=cities.includes(query.city??'')?String(query.city):cities[0]??'';
  const cityRaces=races.filter((item)=>city(item)===selectedCity);
  const selected=cityRaces.find((item)=>item.id===Number(query.race))??cityRaces[0]??null;
  const [rawEntries,rawDaily,safety]=selected?await Promise.all([getJson<unknown>(`/races/${selected.id}/entries`,[]),getJson<unknown>(`/recommendations/daily?race_date=${today}`,[]),getJson<Safety>('/analytics/model-safety',{can_publish_actionable_scenarios:false,state:'review'})]):[[],[],{can_publish_actionable_scenarios:false,state:'review'}];
  const entries=list<Entry>(rawEntries).sort((a,b)=>(a.program_number??999)-(b.program_number??999));
  const daily=list<Daily>(rawDaily).find((item)=>Number(item.race_id)===selected?.id);
  const candidates=(daily?.ranked_entries?.length?daily.ranked_entries:[...(daily?.candidates??[]),...(daily?.alternatives??[]),daily?.primary,daily?.top_entry].filter(Boolean) as Candidate[]).sort((a,b)=>(num(b.win_probability)??-1)-(num(a.win_probability)??-1));
  const candidateFor=(entry:Entry)=>candidates.find((candidate)=>candidate.program_number===entry.program_number)||null;
  const href=(name:string,id?:number)=>`/bulletin?city=${encodeURIComponent(name)}${id?`&race=${id}`:''}`;
  const verified=safety.verified_race_dates??0;
  const minimum=safety.minimum_race_dates??20;
  return <main className="bulletin-shell">
    <header className="bulletin-top"><div><a href="/">PEGASUS</a><span>{t.title}</span></div><a href="/program">{t.back}</a></header>
    <section className="bulletin-hero"><div><p className="eyebrow">{t.today.toUpperCase()}</p><h1>{t.title}</h1><p>{t.intro}</p></div><div className="bulletin-source"><b>{today}</b><span>{t.source}</span></div></section>
    {!selected?<section className="bulletin-empty"><h2>{t.unavailable}</h2><p>{t.waiting}</p></section>:<>
      <nav className="bulletin-city-tabs" aria-label={t.city}>{cities.map((name)=><a key={name} className={name===selectedCity?'active':''} href={href(name)}>{name}</a>)}</nav>
      <nav className="bulletin-race-tabs" aria-label={t.race}>{cityRaces.map((item)=><a key={item.id} className={item.id===selected.id?'active':''} href={href(selectedCity,item.id)}><b>{item.race_number}. {t.race}</b><span>{raceTime(item)}</span></a>)}</nav>
      <section className="bulletin-race-meta"><div className="bulletin-track-mark" aria-hidden="true">\u265E</div><div><p className="eyebrow">{selectedCity} / {selected.race_number}. {t.race}</p><h2>{t.card}</h2><p>{raceTime(selected)} \u00b7 {selected.distance_meters??'--'}m \u00b7 {text(selected.surface)} \u00b7 {entries.length} {t.runners}</p></div><a className="bulletin-detail-link" href={`/races/${selected.id}`}>{t.details} \u2192</a></section>
      {!safety.can_publish_actionable_scenarios?<section className="bulletin-gate"><b>{t.review}</b><p>{t.safety}</p><small>{t.source} \u00b7 {verified}/{minimum} {t.today.toLowerCase()}</small></section>:null}
      <section className="bulletin-grid"><div className="bulletin-table-card"><div className="panel-heading"><div><p className="eyebrow">{t.card.toUpperCase()}</p><h2>{entries.length} {t.runners}</h2></div><small>{t.caution}</small></div><div className="bulletin-table-wrap"><table className="bulletin-table"><thead><tr><th>{t.no}</th><th>{t.horse}</th><th>{t.model}</th><th>{t.hp}</th><th>{t.agf}</th><th>{t.weight}</th><th>{t.jockey}</th><th>{t.trainer}</th></tr></thead><tbody>{entries.map((entry)=>{const candidate=candidateFor(entry);return <tr key={entry.id}><td>{text(entry.program_number)}</td><td><b>{text(entry.horse_name)}</b>{entry.horse_id?<a href={`/horses/${entry.horse_id}`}>{t.profile} \u2192</a>:null}</td><td>{safety.can_publish_actionable_scenarios?percent(candidate?.win_probability):'--'}</td><td>{text(entry.handicap_rating)}</td><td>{num(entry.agf_percent)===null?t.unavailableMarket:percent(entry.agf_percent)}</td><td>{text(entry.weight_kg)}</td><td>{text(entry.jockey_name)}</td><td>{text(entry.trainer_name)}</td></tr>})}</tbody></table></div></div><aside className="bulletin-insights"><section><p className="eyebrow">{t.review.toUpperCase()}</p><h2>{safety.can_publish_actionable_scenarios?'Haz\u0131r':t.review}</h2><strong>{verified}/{minimum}</strong><p>{t.safety}</p></section><section><p className="eyebrow">VER\u0130 DURUMU</p><h2>{entries.length} {t.runners}</h2><p>{t.source}</p></section></aside></section>
    </>}
  </main>
}