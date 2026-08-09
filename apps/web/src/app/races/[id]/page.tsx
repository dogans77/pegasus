type Track={name?:string|null};
type Race={id:number;race_number?:number|null;scheduled_time?:string|null;start_time?:string|null;distance_meters?:number|null;surface?:string|null;track?:Track|null};
type Entry={id:number;program_number?:number|string|null;horse_id?:number|string|null;horse_name?:string|null;jockey_name?:string|null;trainer_name?:string|null;weight_kg?:number|string|null;handicap_rating?:number|string|null;agf_percent?:number|string|null};

export const dynamic='force-dynamic';
const api=process.env.PEGASUS_API_URL||process.env.NEXT_PUBLIC_API_URL||'http://127.0.0.1:8042/api/v1';
const t={back:'\u2190 Program',tag:'KO\u015eU DETAYI',card:'Ko\u015fu kart\u0131',program:'G\u00fcncel programa d\u00f6n',missingTitle:'Bu ko\u015fu kart\u0131 art\u0131k etkin de\u011fil',missing:'A\u00e7t\u0131\u011f\u0131n kart, g\u00fcncel veri alan\u0131nda bulunamad\u0131. G\u00fcncel resmi programdan ba\u015fka bir kart se\u00e7ebilirsin.',no:'No',horse:'At',hp:'HP',agf:'AGF',weight:'Kilo',jockey:'Jokey',trainer:'Antren\u00f6r',profile:'At profili',runners:'at',source:'Resmi program aktar\u0131m\u0131',notice:'Bu sayfa veriyi tek kez al\u0131r; bulunmayan kart i\u00e7in yeniden deneme yapmaz.'};
function text(value:unknown){return value===null||value===undefined||value===''?'--':String(value)}
function pct(value:unknown){const n=Number(value);return Number.isFinite(n)?`%${n.toFixed(1)}`:'--'}
async function request<T>(path:string):Promise<T|null>{try{const response=await fetch(`${api}${path}`,{cache:'no-store'});return response.ok?await response.json() as T:null}catch{return null}}
function list<T>(value:unknown):T[]{if(Array.isArray(value))return value as T[];const item=value as {items?:T[];entries?:T[]};return item.items||item.entries||[]}

export default async function RaceDetail({params}:{params:Promise<{id:string}>}){
 const {id}=await params;
 const raceId=Number(id);
 const race=Number.isInteger(raceId)&&raceId>0?await request<Race>(`/races/${raceId}`):null;
 if(!race)return <main className="detail-shell"><header className="detail-nav"><a className="brand" href="/"><span>PEGASUS</span><small>RACE INTELLIGENCE</small></a><a href="/command-center">{t.program}</a></header><section className="detail-missing"><p className="eyebrow">{t.tag}</p><h1>{t.missingTitle}</h1><p>{t.missing}</p><a href="/command-center">{t.program} \u2192</a><small>{t.notice}</small></section></main>;
 const entries=list<Entry>(await request<unknown>(`/races/${race.id}/entries`)).sort((a,b)=>Number(a.program_number??999)-Number(b.program_number??999));
 const name=text(race.track?.name);
 const time=text(race.scheduled_time??race.start_time);
 return <main className="detail-shell"><header className="detail-nav"><a className="brand" href="/"><span>PEGASUS</span><small>RACE INTELLIGENCE</small></a><a href="/command-center">{t.back}</a></header><section className="detail-intro"><p className="eyebrow">{t.tag}</p><h1>{name} {race.race_number}. {t.card}</h1><p>{time} \u00b7 {race.distance_meters??'--'}m \u00b7 {text(race.surface)} \u00b7 {entries.length} {t.runners}</p></section><section className="detail-panel"><div className="detail-heading"><div><p className="eyebrow">{t.card.toUpperCase()}</p><h2>{entries.length} {t.runners}</h2></div><small>{t.source}</small></div><div className="detail-table"><table><thead><tr><th>{t.no}</th><th>{t.horse}</th><th>{t.hp}</th><th>{t.agf}</th><th>{t.weight}</th><th>{t.jockey}</th><th>{t.trainer}</th></tr></thead><tbody>{entries.map(entry=><tr key={entry.id}><td>{text(entry.program_number)}</td><td><b>{text(entry.horse_name)}</b>{entry.horse_id?<a href={`/horses/${entry.horse_id}`}>{t.profile} \u2192</a>:null}</td><td>{text(entry.handicap_rating)}</td><td>{pct(entry.agf_percent)}</td><td>{text(entry.weight_kg)}</td><td>{text(entry.jockey_name)}</td><td>{text(entry.trainer_name)}</td></tr>)}</tbody></table></div></section></main>;
}