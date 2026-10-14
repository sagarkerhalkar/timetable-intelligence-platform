"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { ChangeEvent, MouseEvent } from "react";
import { QrProductNav } from "../../../components/qr-product-nav";

const PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/backend";

type QrRow = {
  id:string; name:string; slug:string; qr_type:string; tracking_mode:string; identity_mode:string;
  target_url:string; source_url:string; public_url:string; active:boolean; created_at:string; updated_at:string;
  template_id:string|null; template_name:string|null; total_scans:number; legacy_scans:number;
  unique_visitors:number; unique_emails:number; country_count:number;
};
type PageResponse = { items:QrRow[]; total:number; limit:number; next_cursor:string|null; has_more:boolean };
type StatusFilter = "all"|"active"|"inactive";
type SortMode = "recent"|"oldest"|"name"|"scans";
type ViewMode = "table"|"cards";
type Channel = {value:string;label:string};

const CHANNELS:Channel[] = [
  {value:"web",label:"Web / Website"},{value:"whatsapp",label:"WhatsApp"},{value:"telegram",label:"Telegram"},
  {value:"instagram",label:"Instagram"},{value:"google-chat",label:"Google Chat"},{value:"facebook",label:"Facebook"},
  {value:"messenger",label:"Messenger"},{value:"linkedin",label:"LinkedIn"},{value:"email",label:"Email"},
  {value:"teams",label:"Microsoft Teams"},{value:"slack",label:"Slack"},{value:"discord",label:"Discord"}
];

function formatNumber(value:number){return value.toLocaleString("en-IN")}
function formatDate(value:string){const d=new Date(value);return Number.isNaN(d.valueOf())?value:new Intl.DateTimeFormat("en-IN",{day:"2-digit",month:"short",year:"numeric"}).format(d)}
function absoluteUrl(value:string){if(!value)return "";try{return new URL(value,window.location.origin).toString()}catch{return value}}
function imageUrl(code:QrRow,format:"png"|"svg"|"pdf",source?:string,download=false){const p=new URLSearchParams({format});if(source)p.set("source",source);if(download)p.set("download","true");return `${PUBLIC_API_URL}/api/v1/qr-codes/${encodeURIComponent(code.id)}/image?${p.toString()}`}
function download(url:string){const a=document.createElement("a");a.href=url;a.rel="noopener";document.body.appendChild(a);a.click();a.remove()}
async function copyText(value:string){if(navigator.clipboard?.writeText){try{await navigator.clipboard.writeText(value);return}catch{}}const area=document.createElement("textarea");area.value=value;area.readOnly=true;area.style.position="fixed";area.style.opacity="0";document.body.appendChild(area);area.select();document.execCommand("copy");area.remove()}

export default function QrCodesScalePage(){
  const [data,setData]=useState<PageResponse>({items:[],total:0,limit:25,next_cursor:null,has_more:false});
  const [loading,setLoading]=useState(true);const [error,setError]=useState("");const [message,setMessage]=useState("");
  const [searchDraft,setSearchDraft]=useState("");const [search,setSearch]=useState("");
  const [status,setStatus]=useState<StatusFilter>("all");const [type,setType]=useState("all");const [sort,setSort]=useState<SortMode>("recent");const [limit,setLimit]=useState(25);
  const [cursor,setCursor]=useState<string|null>(null);const [history,setHistory]=useState<Array<string|null>>([]);
  const [selected,setSelected]=useState<Set<string>>(new Set());const [view,setView]=useState<ViewMode>("table");
  const [preview,setPreview]=useState<QrRow|null>(null);const [channelCode,setChannelCode]=useState<QrRow|null>(null);const [channel,setChannel]=useState("whatsapp");const [channelFormat,setChannelFormat]=useState<"png"|"svg"|"pdf">("png");

  useEffect(()=>{const timer=window.setTimeout(()=>setSearch(searchDraft.trim()),260);return()=>window.clearTimeout(timer)},[searchDraft]);
  useEffect(()=>{setCursor(null);setHistory([])},[search,status,type,sort,limit]);

  const load=useCallback(async()=>{setLoading(true);setError("");try{const p=new URLSearchParams({limit:String(limit),active:status,qr_type:type,sort});if(search)p.set("q",search);if(cursor)p.set("cursor",cursor);const r=await fetch(`${PUBLIC_API_URL}/api/v1/qr-scale/codes?${p.toString()}`,{cache:"no-store"});if(!r.ok)throw new Error("Could not load QR library.");const next=await r.json() as PageResponse;setData(next)}catch(e){setError(e instanceof Error?e.message:"Could not load QR library.")}finally{setLoading(false)}},[cursor,limit,search,sort,status,type]);
  useEffect(()=>{void load()},[load]);

  const selectedVisible=useMemo(()=>data.items.filter(x=>selected.has(x.id)).length,[data.items,selected]);
  const pageNumber=history.length+1;
  function nextPage(){if(!data.next_cursor)return;setHistory(current=>[...current,cursor]);setCursor(data.next_cursor);window.scrollTo({top:0,behavior:"smooth"})}
  function previousPage(){if(!history.length)return;const copy=[...history];const prior=copy.pop()??null;setHistory(copy);setCursor(prior);window.scrollTo({top:0,behavior:"smooth"})}
  function toggle(id:string){setSelected(current=>{const next=new Set(current);next.has(id)?next.delete(id):next.add(id);return next})}
  function selectVisible(){setSelected(current=>{const next=new Set(current);data.items.forEach(x=>next.add(x.id));return next})}
  function clearSelection(){setSelected(new Set())}
  async function copySource(code:QrRow){await copyText(code.source_url||code.target_url);setMessage(`Source link copied: ${code.name}`)}
  async function copyQr(code:QrRow){await copyText(absoluteUrl(code.public_url));setMessage(`QR link copied: ${code.name}`)}
  async function setActive(code:QrRow){const r=await fetch(`${PUBLIC_API_URL}/api/v1/qr-codes/${encodeURIComponent(code.id)}/active?active=${!code.active}`,{method:"POST"});if(!r.ok){setError("Could not change QR status.");return}setMessage(`${code.name} is now ${code.active?"Inactive":"Active"}.`);await load()}
  async function clearScans(code:QrRow){if(!window.confirm(`Clear scan history for “${code.name}”? The QR stays saved.`))return;const r=await fetch(`${PUBLIC_API_URL}/api/v1/qr-codes/${encodeURIComponent(code.id)}/scans`,{method:"DELETE"});if(!r.ok){setError("Could not clear scan history.");return}setMessage(`Scan history cleared for ${code.name}.`);await load()}
  async function deleteCode(code:QrRow){if(!window.confirm(`Permanently delete “${code.name}”? Existing printed copies will stop working.`))return;const r=await fetch(`${PUBLIC_API_URL}/api/v1/qr-codes/${encodeURIComponent(code.id)}`,{method:"DELETE"});if(!r.ok){setError("Could not delete QR.");return}setSelected(current=>{const next=new Set(current);next.delete(code.id);return next});setMessage(`${code.name} deleted.`);await load()}
  async function deleteSelected(){const ids=[...selected];if(!ids.length)return;if(!window.confirm(`Permanently delete ${ids.length} selected QR code${ids.length===1?"":"s"}?`))return;let deleted=0;for(let start=0;start<ids.length;start+=5){const batch=ids.slice(start,start+5);const results=await Promise.all(batch.map(id=>fetch(`${PUBLIC_API_URL}/api/v1/qr-codes/${encodeURIComponent(id)}`,{method:"DELETE"})));deleted+=results.filter(r=>r.ok).length}setMessage(`${deleted} QR code${deleted===1?"":"s"} deleted.`);clearSelection();await load()}

  function QuickActions({code}:{code:QrRow}){return <div className="qsv2-actions">
    <button type="button" onClick={()=>void copySource(code)}>Copy Source</button>
    <button type="button" onClick={()=>setPreview(code)}>Open QR</button>
    <button type="button" onClick={()=>void copyQr(code)}>Copy QR Link</button>
    <Link href={`/qr/stats?qr_id=${encodeURIComponent(code.id)}`}>Analytics</Link>
    <details><summary>•••</summary><div className="qsv2-action-menu">
      <Link href={`/qr?edit=${encodeURIComponent(code.id)}`}>Edit QR</Link>
      <button onClick={()=>void setActive(code)}>{code.active?"Deactivate":"Activate"}</button>
      <button onClick={()=>download(imageUrl(code,"png",undefined,true))}>Download PNG</button>
      <button onClick={()=>download(imageUrl(code,"svg",undefined,true))}>Download SVG</button>
      <button onClick={()=>download(imageUrl(code,"pdf",undefined,true))}>Download PDF</button>
      <button onClick={()=>setChannelCode(code)}>Channel QR…</button>
      <button onClick={()=>void clearScans(code)}>Clear scan data</button>
      <button className="danger" onClick={()=>void deleteCode(code)}>Delete permanently</button>
    </div></details>
  </div>}

  return <main className="qrfy-page qsv2-page">
    <QrProductNav/>
    <header className="qsv2-hero"><div><p className="qrfy-kicker">Scale-ready QR operations</p><h1>My QR Codes</h1><p>Compact, server-side QR management designed for lakhs of campaigns. Open a QR, copy its source, or drill into analytics without loading the whole library.</p></div><div><span className="qsv2-scale-badge">{formatNumber(data.total)} QR codes</span><Link className="qrfy-button primary" href="/qr">＋ Create QR</Link></div></header>

    <section className="qsv2-toolbar">
      <label className="qsv2-search"><span>Search</span><input value={searchDraft} onChange={(e:ChangeEvent<HTMLInputElement>)=>setSearchDraft(e.target.value)} placeholder="Name, slug or source URL…"/></label>
      <label><span>Status</span><select value={status} onChange={(e:ChangeEvent<HTMLSelectElement>)=>setStatus(e.target.value as StatusFilter)}><option value="all">All</option><option value="active">Active</option><option value="inactive">Inactive</option></select></label>
      <label><span>Type</span><select value={type} onChange={(e:ChangeEvent<HTMLSelectElement>)=>setType(e.target.value)}><option value="all">All types</option><option value="url">URL</option><option value="wifi">Wi-Fi</option><option value="calendar">Calendar</option><option value="contact">Contact</option><option value="email">Email</option><option value="geo">Location</option><option value="phone">Phone</option></select></label>
      <label><span>Sort</span><select value={sort} onChange={(e:ChangeEvent<HTMLSelectElement>)=>setSort(e.target.value as SortMode)}><option value="recent">Newest</option><option value="oldest">Oldest</option><option value="name">Name</option><option value="scans">Most scans</option></select></label>
      <label><span>Rows</span><select value={limit} onChange={(e:ChangeEvent<HTMLSelectElement>)=>setLimit(Number(e.target.value))}><option value={25}>25</option><option value={50}>50</option><option value={100}>100</option></select></label>
      <div className="qsv2-view-toggle"><button className={view==="table"?"active":""} onClick={()=>setView("table")}>Table</button><button className={view==="cards"?"active":""} onClick={()=>setView("cards")}>Cards</button></div>
    </section>

    <section className="qsv2-selection"><div><strong>{formatNumber(data.total)} results</strong><span> · page {pageNumber}</span>{loading?<em> · refreshing…</em>:null}</div><div><button onClick={selectVisible}>Select visible</button><button onClick={clearSelection} disabled={!selected.size}>Clear ({selected.size})</button><button className="danger" onClick={()=>void deleteSelected()} disabled={!selected.size}>Delete selected ({selected.size})</button></div></section>
    {message?<div className="qrfy-toast success">{message}</div>:null}{error?<div className="qrfy-toast error">{error}</div>:null}

    {view==="table"?<section className="qsv2-table-wrap"><table className="qsv2-table"><thead><tr><th className="check"></th><th>QR</th><th>Source / link</th><th>Status</th><th>Verified</th><th>Devices</th><th>Countries</th><th>Created</th><th>Quick actions</th></tr></thead><tbody>
      {data.items.map(code=><tr key={code.id} className={selected.has(code.id)?"selected":""}><td><input type="checkbox" checked={selected.has(code.id)} onChange={()=>toggle(code.id)} aria-label={`Select ${code.name}`}/></td><td><div className="qsv2-qr-cell"><img loading="lazy" src={imageUrl(code,"png")} alt=""/><div><strong>{code.name}</strong><small>{code.qr_type.toUpperCase()} · {code.tracking_mode}</small><code>{code.slug}</code></div></div></td><td><div className="qsv2-source"><strong title={code.source_url}>{code.source_url||code.target_url||"Native QR action"}</strong><small title="Public tracked QR">NextToppers QR</small></div></td><td><span className={`qsv2-status ${code.active?"active":"inactive"}`}>{code.active?"Active":"Inactive"}</span></td><td><strong>{formatNumber(code.total_scans)}</strong></td><td>{formatNumber(code.unique_visitors)}</td><td>{formatNumber(code.country_count)}</td><td>{formatDate(code.created_at)}</td><td><QuickActions code={code}/></td></tr>)}
      {!loading&&!data.items.length?<tr><td colSpan={9}><div className="qrfy-no-data">No QR codes match these filters.</div></td></tr>:null}
    </tbody></table></section>:<section className="qsv2-card-grid">{data.items.map(code=><article key={code.id} className={selected.has(code.id)?"selected":""}><header><input type="checkbox" checked={selected.has(code.id)} onChange={()=>toggle(code.id)}/><img loading="lazy" src={imageUrl(code,"png")} alt=""/><div><strong>{code.name}</strong><small>{code.qr_type.toUpperCase()} · {code.active?"Active":"Inactive"}</small></div></header><div className="qsv2-card-source"><span>Source</span><strong>{code.source_url||code.target_url||"Native QR action"}</strong></div><dl><div><dt>Verified</dt><dd>{formatNumber(code.total_scans)}</dd></div><div><dt>Devices</dt><dd>{formatNumber(code.unique_visitors)}</dd></div><div><dt>Countries</dt><dd>{formatNumber(code.country_count)}</dd></div></dl><QuickActions code={code}/></article>)}{!loading&&!data.items.length?<div className="qrfy-no-data">No QR codes match these filters.</div>:null}</section>}

    <nav className="qsv2-cursor-nav" aria-label="QR library pages"><button onClick={previousPage} disabled={!history.length}>← Previous</button><span>Page {pageNumber} · showing {data.items.length} of {formatNumber(data.total)}</span><button onClick={nextPage} disabled={!data.has_more||!data.next_cursor}>Next →</button></nav>

    {preview?<div className="qsv2-modal-backdrop" role="dialog" aria-modal="true" onMouseDown={(e:MouseEvent<HTMLDivElement>)=>{if(e.target===e.currentTarget)setPreview(null)}}><section className="qsv2-modal"><button className="close" onClick={()=>setPreview(null)}>×</button><p className="qrfy-kicker">Open QR anytime</p><h2>{preview.name}</h2><img src={imageUrl(preview,"png")} alt={`QR code for ${preview.name}`}/><div className="qsv2-modal-links"><button onClick={()=>void copySource(preview)}>Copy Source Link</button><button onClick={()=>void copyQr(preview)}>Copy QR Link</button>{preview.public_url?<a href={absoluteUrl(preview.public_url)} target="_blank" rel="noreferrer">Open public QR link ↗</a>:null}</div><div className="qsv2-downloads"><button onClick={()=>download(imageUrl(preview,"png",undefined,true))}>PNG</button><button onClick={()=>download(imageUrl(preview,"svg",undefined,true))}>SVG</button><button onClick={()=>download(imageUrl(preview,"pdf",undefined,true))}>PDF</button></div></section></div>:null}

    {channelCode?<div className="qsv2-modal-backdrop" role="dialog" aria-modal="true" onMouseDown={(e:MouseEvent<HTMLDivElement>)=>{if(e.target===e.currentTarget)setChannelCode(null)}}><section className="qsv2-modal small"><button className="close" onClick={()=>setChannelCode(null)}>×</button><p className="qrfy-kicker">Exact source attribution</p><h2>Channel QR</h2><label><span>Channel</span><select value={channel} onChange={(e:ChangeEvent<HTMLSelectElement>)=>setChannel(e.target.value)}>{CHANNELS.map(x=><option value={x.value} key={x.value}>{x.label}</option>)}</select></label><label><span>Format</span><select value={channelFormat} onChange={(e:ChangeEvent<HTMLSelectElement>)=>setChannelFormat(e.target.value as "png"|"svg"|"pdf")}><option value="png">PNG</option><option value="svg">SVG</option><option value="pdf">PDF</option></select></label><img src={imageUrl(channelCode,"png",channel)} alt="Channel QR preview"/><button className="qrfy-button primary" onClick={()=>download(imageUrl(channelCode,channelFormat,channel,true))}>Download channel QR</button></section></div>:null}
  </main>
}

