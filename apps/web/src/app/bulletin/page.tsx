type Race = { id:number; race_number?:number|null; scheduled_time?:string|null; start_time?:string|null; distance_meters?:number|null; surface?:string|null; track?:{name?:string|null}|null; race_date?:string|null };
type Entry = { id:number; program_number?:number|null; horse_id?:number|null; horse_name?:string|null; jockey_name?:string|null; trainer_name?:string|null; weight_kg?:number|string|null; handicap_rating?:number|string|null; agf_percent?:number|string|null };
type Candidate = { program_number?:number|null; horse_name?:string|null; win_probability?:number|string|null; strengths?:string[]; risks?:string[] };
type Explanation = { primary?:Candidate|null; alternatives?:Candidate[];ranked_entries?:Candidate[]; chaos_index?:number|string|null };
type ValueItem = { program_number?:number|null; horse_name?:string|null; edge_percentage_points?:number|string|null };
type Value = { chaos_index?:number|string|null; value_candidates?:ValueItem[] };
type DailyRecommendation = { race_id?:number|string|null; primary?:Candidate|null; top_entry?:Candidate|null; candidates?:Candidate[]; alternatives?:Candidate[]; ranked_entries?:Candidate[] };

export const dynamic = 'force-dynamic';
const api = process.env.PEGASUS_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8042/api/v1';
const t = {
  title:'G\u00fcnl\u00fck b\u00fclten', intro:'Resmi program, model sinyali ve ko\u015fu kart\u0131 tek ekranda.', today:'Bug\u00fcn',
  city:'Hipodrom', race:'Ko\u015fu', runners:'at', no:'No', horse:'At', model:'Model', hp:'HP', agf:'AGF', weight:'Kilo', jockey:'Jokey', trainer:'Antren\u00f6r',
  card:'Ko\u015fu kart\u0131', details:'Detayl\u0131 incele', featured:'\u00d6ne \u00e7\u0131kan aday', analysis:'Analiz notu', chaos:'S\u00fcrpriz riski', value:'De\u011fer sinyali',
  unavailable:'Bug\u00fcn i\u00e7in aktar\u0131lm\u0131\u015f resmi program bulunamad\u0131.', waiting:'G\u00fcncel program aktar\u0131ld\u0131\u011f\u0131nda b\u00fclten burada g\u00f6r\u00fcnecek.',
  profile:'At profili', source:'Kaynak: resmi program aktar\u0131m\u0131', caution:'Bu ekran olas\u0131l\u0131k tabanl\u0131 karar deste\u011fidir; kesin sonu\u00e7 iddias\u0131 ta\u015f\u0131maz.',
  noModel:'Model \u00e7\u0131kt\u0131s\u0131 haz\u0131rlan\u0131yor', noMarket:'AGF verisi hen\u00fcz aktar\u0131lmad\u0131', back:'Programa d\u00f6n'
};
async function getJson<T>(path:string, fallback:T):Promise<T>{try{const response=await fetch(`${api}${path}`,{cache:'no-store'});return response.ok?await response.json() as T:fallback}catch{return fallback}}
function items<T>(value:unknown):T[]{if(Array.isArray(value))return value as T[];const object=value as {items?:T[];recommendations?:T[];races?:T[]};return Array.isArray(object?.items)?object.items:Array.isArray(object?.recommendations)?object.recommendations:Array.isArray(object?.races)?object.races:[]}
function valueText(value:unknown):string{return value===null||value===undefined||value===''?'--':String(value)}
function numeric(value:unknown):number|null{const parsed=Number(value);return Number.isFinite(parsed)?parsed:null}
function probability(value:unknown):string{const parsed=numeric(value);return parsed===null||parsed<=0?'--':`%${parsed.toFixed(1)}`}
function cityOf(race:Race):string{return valueText(race.track?.name).replace(/\s+/g,' ').trim()}
function timeOf(race:Race):string{return valueText(race.scheduled_time??race.start_time)}

export default async function Bulletin({searchParams}:{searchParams:Promise<{city?:string;race?:string}>}){
  const query=await searchParams;
  const allRaces=items<Race>(await getJson<unknown>('/races/',[]));
  const today=new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Istanbul'}).format(new Date());
  const todayRaces=allRaces.filter((race)=>String(race.race_date??'').slice(0,10)===today);
  const cities=Array.from(new Set(todayRaces.map(cityOf).filter((city)=>city!=='--'))).sort((a,b)=>a.localeCompare(b,'tr'));
  const selectedCity=cities.includes(query.city??'')?String(query.city):cities[0]??'';
  const cityRaces=todayRaces.filter((race)=>cityOf(race)===selectedCity).sort((a,b)=>(a.race_number??999)-(b.race_number??999));
  const selectedRace=cityRaces.find((race)=>race.id===Number(query.race))??cityRaces[0]??null;
  const [rawEntries,explanation,value,rawDaily]=selectedRace?await Promise.all([
    getJson<unknown>(`/races/${selectedRace.id}/entries`,[]),
    getJson<Explanation|null>(`/explanations/races/${selectedRace.id}`,null),
    getJson<Value|null>(`/value/races/${selectedRace.id}`,null),
    getJson<unknown>(`/recommendations/daily?race_date=${today}`,[]),
  ]):[[],null,null,[]];
  const entries=items<Entry>(rawEntries).sort((a,b)=>(a.program_number??999)-(b.program_number??999));
  const daily=items<DailyRecommendation>(rawDaily).find((item)=>Number(item.race_id)===selectedRace?.id)??null;
  const fallbackCandidates=[explanation?.primary,...(explanation?.alternatives??[]),daily?.primary,daily?.top_entry,...(daily?.candidates??[]),...(daily?.alternatives??[])].filter(Boolean) as Candidate[];
  const candidates=((daily?.ranked_entries?.length?daily.ranked_entries:fallbackCandidates)??[]).filter(Boolean).sort((a,b)=>(numeric(b.win_probability)??-1)-(numeric(a.win_probability)??-1));
  const candidateFor=(entry:Entry)=>candidates.find((candidate)=>candidate.program_number===entry.program_number)||candidates.find((candidate)=>String(candidate.horse_name??'').trim().toUpperCase()===String(entry.horse_name??'').trim().toUpperCase())||null;
  const lead=candidates[0]??explanation?.primary??daily?.primary??daily?.top_entry??null;
  const valueLead=value?.value_candidates?.[0]??null;
  const linkFor=(city:string,race?:number)=>`/bulletin?city=${encodeURIComponent(city)}${race?`&race=${race}`:''}`;
  return <main className="bulletin-shell">
    <header className="bulletin-top"><div><a href="/">PEGASUS</a><span>{t.title}</span></div><a href="/program">{t.back}</a></header>
    <section className="bulletin-hero"><div><p className="eyebrow">{t.today.toUpperCase()}</p><h1>{t.title}</h1><p>{t.intro}</p></div><div className="bulletin-source"><b>{today}</b><span>{t.source}</span></div></section>
    {!selectedRace?<section className="bulletin-empty"><h2>{t.unavailable}</h2><p>{t.waiting}</p></section>:<>
      <section className="bulletin-city-tabs" aria-label={t.city}>{cities.map((city)=><a key={city} className={city===selectedCity?'active':''} href={linkFor(city)}>{city}</a>)}</section>
      <section className="bulletin-race-tabs" aria-label={t.race}>{cityRaces.map((race)=><a key={race.id} className={race.id===selectedRace.id?'active':''} href={linkFor(selectedCity,race.id)}><b>{race.race_number}. {t.race}</b><span>{timeOf(race)}</span></a>)}</section>
      <section className="bulletin-race-meta"><div><p className="eyebrow">{selectedCity} / {selectedRace.race_number}. {t.race}</p><h2>{t.card}</h2><p>{timeOf(selectedRace)} {'\u00b7'} {selectedRace.distance_meters??'--'}m {'\u00b7'} {valueText(selectedRace.surface)} {'\u00b7'} {entries.length} {t.runners}</p></div><a className="bulletin-detail-link" href={`/races/${selectedRace.id}`}>{t.details} {'\u2192'}</a></section>
      <section className="bulletin-grid"><div className="bulletin-table-card"><div className="panel-heading"><div><p className="eyebrow">{t.card.toUpperCase()}</p><h2>{entries.length} {t.runners}</h2></div><small>{t.caution}</small></div><div className="bulletin-table-wrap"><table className="bulletin-table"><thead><tr><th>{t.no}</th><th>{t.horse}</th><th>{t.model}</th><th>{t.hp}</th><th>{t.agf}</th><th>{t.weight}</th><th>{t.jockey}</th><th>{t.trainer}</th></tr></thead><tbody>{entries.map((entry)=>{const candidate=candidateFor(entry);const market=probability(entry.agf_percent);return <tr key={entry.id}><td>{valueText(entry.program_number)}</td><td><b>{valueText(entry.horse_name)}</b>{entry.horse_id?<a href={`/horses/${entry.horse_id}`}>{t.profile} {'\u2192'}</a>:null}</td><td>{probability(candidate?.win_probability)}</td><td>{valueText(entry.handicap_rating)}</td><td>{market==='--'?t.noMarket:market}</td><td>{valueText(entry.weight_kg)}</td><td>{valueText(entry.jockey_name)}</td><td>{valueText(entry.trainer_name)}</td></tr>})}</tbody></table></div></div>
      <aside className="bulletin-insights"><section><p className="eyebrow">{t.featured.toUpperCase()}</p><h2>{lead?`${lead.program_number}. ${valueText(lead.horse_name)}`:t.noModel}</h2><strong>{probability(lead?.win_probability)}</strong><p>{lead?.strengths?.slice(0,3).join(' \u00b7 ')||t.noModel}</p></section><section><p className="eyebrow">{t.chaos.toUpperCase()}</p><h2>{numeric(value?.chaos_index??explanation?.chaos_index)?.toFixed(1)??'--'}/100</h2><p>{t.caution}</p></section><section><p className="eyebrow">{t.value.toUpperCase()}</p><h2>{valueLead?`${valueLead.program_number}. ${valueText(valueLead.horse_name)}`:t.noMarket}</h2><p>{valueLead?`${probability(valueLead.edge_percentage_points)} model-AGF fark\u0131`:t.noMarket}</p></section></aside></section>
    </>}
  </main>
}