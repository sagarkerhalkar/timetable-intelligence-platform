"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { ChangeEvent } from "react";
import { QrProductNav } from "../../../components/qr-product-nav";

const PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/backend";

type Period = "7d"|"30d"|"90d"|"365d"|"all";
type Analytics = {
  period:Period; qr_id:string|null; total_qr_codes:number; active_qr_codes:number; verified_scans:number;
  unique_devices:number; unique_emails:number; identified_scans:number; anonymous_scans:number;
  trend:Array<{day:string;scans:number}>; countries:Record<string,number>; devices:Record<string,number>;
  browsers:Record<string,number>; operating_systems:Record<string,number>; platforms:Record<string,number>;
  confidence:Record<string,number>; top_qr_codes:Array<{id:string;name:string;slug:string;target_url:string;scans:number}>;
};
type RecentScan = {id:number;qr_id:string;qr_name:string;scanned_at:string;country:string;device_type:string;browser:string;operating_system:string;platform:string;source_confidence:string;scanner_email:string;device_id:string};
type RecentResponse={items:RecentScan[];next_cursor:number|null;has_more:boolean};
type QrLookup={id:string;name:string;slug:string;source_url:string;public_url:string;total_scans:number};
type QrResponse={items:QrLookup[];total:number};

const EMPTY:Analytics={period:"30d",qr_id:null,total_qr_codes:0,active_qr_codes:0,verified_scans:0,unique_devices:0,unique_emails:0,identified_scans:0,anonymous_scans:0,trend:[],countries:{},devices:{},browsers:{},operating_systems:{},platforms:{},confidence:{},top_qr_codes:[]};
function n(v:number){return v.toLocaleString("en-IN")}
function countryName(code:string){if(!code||code==="Unknown")return "Unknown";try{return new Intl.DisplayNames(["en"],{type:"region"}).of(code)||code}catch{return code}}
function indiaTime(value:string){const d=new Date(value);return Number.isNaN(d.valueOf())?value:new Intl.DateTimeFormat("en-IN",{timeZone:"Asia/Kolkata",dateStyle:"medium",timeStyle:"short"}).format(d)}
function rangeRows(data:Record<string,number>,country=false){return Object.entries(data).sort((a,b)=>b[1]-a[1]).slice(0,8).map(([label,value])=>({label:country?countryName(label):label,value}))}

function Bars({title,data,country=false}:{title:string;data:Record<string,number>;country?:boolean}){const rows=rangeRows(data,country);const max=Math.max(1,...rows.map(x=>x.value));return <article className="qav2-panel"><header><h3>{title}</h3><span>{rows.length} groups</span></header><div className="qav2-bars">{rows.map(row=><div key={row.label}><div><strong>{row.label}</strong><span>{n(row.value)}</span></div><i><b style={{width:`${Math.max(2,(row.value/max)*100)}%`}}/></i></div>)}{!rows.length?<p className="qrfy-no-data">No verified scan data in this period.</p>:null}</div></article>}

function Trend({rows}:{rows:Array<{day:string;scans:number}>}){const max=Math.max(1,...rows.map(x=>x.scans));return <div className="qav2-trend">{rows.map(row=><div key={row.day} title={`${row.day}: ${row.scans}`}><i style={{height:`${Math.max(3,(row.scans/max)*100)}%`}}/><span>{row.day.slice(5)}</span></div>)}{!rows.length?<p>No verified scan activity in this period.</p>:null}</div>}

export default function QrAnalyticsScalePage(){
  const [period,setPeriod]=useState<Period>("30d");const [qrId,setQrId]=useState("");const [analytics,setAnalytics]=useState<Analytics>(EMPTY);
  const [recent,setRecent]=useState<RecentResponse>({items:[],next_cursor:null,has_more:false});const [recentHistory,setRecentHistory]=useState<Array<number|null>>([]);const [recentCursor,setRecentCursor]=useState<number|null>(null);
  const [qrSearch,setQrSearch]=useState("");const [qrResults,setQrResults]=useState<QrLookup[]>([]);const [selectedName,setSelectedName]=useState("");
  const [loading,setLoading]=useState(true);const [error,setError]=useState("");

  useEffect(()=>{const params=new URLSearchParams(window.location.search);const id=params.get("qr_id")||"";setQrId(id)},[]);
  useEffect(()=>{setRecentCursor(null);setRecentHistory([])},[period,qrId]);

  const load=useCallback(async()=>{setLoading(true);setError("");try{const p=new URLSearchParams({period});if(qrId)p.set("qr_id",qrId);const rp=new URLSearchParams({limit:"25"});if(qrId)rp.set("qr_id",qrId);if(recentCursor)rp.set("cursor",String(recentCursor));const [a,r]=await Promise.all([fetch(`${PUBLIC_API_URL}/api/v1/qr-scale/analytics?${p.toString()}`,{cache:"no-store"}),fetch(`${PUBLIC_API_URL}/api/v1/qr-scale/recent-scans?${rp.toString()}`,{cache:"no-store"})]);if(!a.ok||!r.ok)throw new Error("Could not load scalable QR analytics.");setAnalytics(await a.json() as Analytics);setRecent(await r.json() as RecentResponse)}catch(e){setError(e instanceof Error?e.message:"Could not load scalable QR analytics.")}finally{setLoading(false)}},[period,qrId,recentCursor]);
  useEffect(()=>{void load()},[load]);

  useEffect(()=>{if(!qrSearch.trim()){setQrResults([]);return}const timer=window.setTimeout(async()=>{try{const p=new URLSearchParams({limit:"10",q:qrSearch.trim(),active:"all",qr_type:"all",sort:"recent"});const r=await fetch(`${PUBLIC_API_URL}/api/v1/qr-scale/codes?${p.toString()}`,{cache:"no-store"});if(r.ok){const body=await r.json() as QrResponse;setQrResults(body.items)}}catch{}},250);return()=>window.clearTimeout(timer)},[qrSearch]);

  const uniqueRate=analytics.verified_scans?Math.round((analytics.unique_devices/analytics.verified_scans)*100):0;
  const identifiedRate=analytics.verified_scans?Math.round((analytics.identified_scans/analytics.verified_scans)*100):0;
  function selectQr(row:QrLookup){setQrId(row.id);setSelectedName(row.name);setQrSearch("");setQrResults([]);window.history.replaceState(null,"",`/qr/stats?qr_id=${encodeURIComponent(row.id)}`)}
  function clearQr(){setQrId("");setSelectedName("");window.history.replaceState(null,"","/qr/stats")}
  function recentNext(){if(!recent.next_cursor)return;setRecentHistory(h=>[...h,recentCursor]);setRecentCursor(recent.next_cursor)}
  function recentPrev(){if(!recentHistory.length)return;const h=[...recentHistory];const prior=h.pop()??null;setRecentHistory(h);setRecentCursor(prior)}

  return <main className="qrfy-page qav2-page"><QrProductNav/>
    <header className="qav2-hero"><div><p className="qrfy-kicker">Aggregate-backed intelligence</p><h1>QR Analytics</h1><p>Large-scale verified scan analytics designed to stay useful when campaigns and scan history grow into lakhs and millions. Raw scan rows are never loaded all at once.</p></div><div className="qav2-hero-actions"><span>Scale mode</span><Link className="qrfy-button" href="/qr/reports">Geo, Device & Store Reports</Link><Link className="qrfy-button primary" href="/qr/codes">Manage QR Codes</Link></div></header>

    <section className="qav2-controls"><div className="qav2-periods">{(["7d","30d","90d","365d","all"] as Period[]).map(x=><button key={x} className={period===x?"active":""} onClick={()=>setPeriod(x)}>{x==="all"?"All time":x.toUpperCase()}</button>)}</div><div className="qav2-qr-filter"><input value={qrSearch} onChange={(e:ChangeEvent<HTMLInputElement>)=>setQrSearch(e.target.value)} placeholder={qrId?(selectedName||"Specific QR selected"):"Search QR for drill-down…"}/>{qrId?<button onClick={clearQr}>Back to global</button>:null}{qrResults.length?<div className="qav2-search-results">{qrResults.map(row=><button key={row.id} onClick={()=>selectQr(row)}><strong>{row.name}</strong><small>{row.slug} · {n(row.total_scans)} verified</small></button>)}</div>:null}</div></section>
    {error?<div className="qrfy-toast error">{error}</div>:null}

    <section className="qav2-kpis">
      <article><span>Verified scans</span><strong>{n(analytics.verified_scans)}</strong><small>{period==="all"?"All time":period.toUpperCase()}</small></article>
      <article><span>Unique browsers/devices</span><strong>{n(analytics.unique_devices)}</strong><small>{uniqueRate}% of scan volume · not unique humans</small></article>
      <article><span>Identified scans</span><strong>{n(analytics.identified_scans)}</strong><small>{identifiedRate}% submitted email identity</small></article>
      <article><span>Anonymous scans</span><strong>{n(analytics.anonymous_scans)}</strong><small>No email required</small></article>
      <article><span>Identified emails</span><strong>{n(analytics.unique_emails)}</strong><small>Deliberately submitted identities</small></article>
      <article><span>Active QR</span><strong>{n(analytics.active_qr_codes)}</strong><small>of {n(analytics.total_qr_codes)} in scope</small></article>
    </section>

    <section className="qav2-grid"><article className="qav2-panel wide"><header><div><span>VERIFIED ACTIVITY</span><h2>Scan trend</h2></div><b>{n(analytics.verified_scans)}</b></header><Trend rows={analytics.trend}/></article><Bars title="Countries" data={analytics.countries} country/><Bars title="Devices" data={analytics.devices}/><Bars title="Browsers" data={analytics.browsers}/><Bars title="Operating systems" data={analytics.operating_systems}/><Bars title="Source platforms" data={analytics.platforms}/><Bars title="Attribution confidence" data={analytics.confidence}/></section>

    {!qrId?<section className="qav2-panel qav2-top"><header><div><span>PORTFOLIO</span><h2>Top QR codes</h2></div><small>Click any QR for drill-down</small></header><div className="qav2-top-list">{analytics.top_qr_codes.map((row,index)=><button key={row.id} onClick={()=>{setQrId(row.id);setSelectedName(row.name);window.history.replaceState(null,"",`/qr/stats?qr_id=${encodeURIComponent(row.id)}`)}}><span>#{index+1}</span><div><strong>{row.name}</strong><small>{row.target_url||row.slug}</small></div><b>{n(row.scans)}<em>verified</em></b></button>)}{!analytics.top_qr_codes.length?<p className="qrfy-no-data">No verified scans in this period.</p>:null}</div></section>:null}

    <section className="qav2-panel qav2-recent"><header><div><span>CURSOR-PAGED RAW HISTORY</span><h2>Recent verified scans</h2></div><small>25 records at a time · newest first</small></header><div className="qav2-table-wrap"><table><thead><tr><th>QR</th><th>Time</th><th>Country</th><th>Device</th><th>Browser / OS</th><th>Identity</th><th>Source</th><th>Confidence</th></tr></thead><tbody>{recent.items.map(scan=><tr key={scan.id}><td><strong>{scan.qr_name}</strong></td><td>{indiaTime(scan.scanned_at)}</td><td>{countryName(scan.country)}</td><td>{scan.device_type}<small>{scan.device_id}</small><details className="qr-device-details-v23"><summary><span>Technical details</span><b>View</b></summary><div className="qr-device-detail-groups"><section><h4>Browser & platform</h4><dl><div><dt>Browser</dt><dd>{scan.browser||"Unavailable"}</dd></div><div><dt>OS</dt><dd>{scan.operating_system||"Unavailable"}</dd></div><div><dt>Source platform</dt><dd>{scan.platform||"Unknown"}</dd></div></dl></section><section><h4>Device & identity</h4><dl><div><dt>Device ID</dt><dd>{scan.device_id||"Unavailable"}</dd></div><div><dt>Device type</dt><dd>{scan.device_type||"Unavailable"}</dd></div><div><dt>Identity</dt><dd>{scan.scanner_email||"Anonymous"}</dd></div><div><dt>Country</dt><dd>{countryName(scan.country)}</dd></div></dl></section></div></details></td><td>{scan.browser}<small>{scan.operating_system}</small></td><td>{scan.scanner_email||"Anonymous"}</td><td>{scan.platform}</td><td><span className={`qav2-confidence ${scan.source_confidence}`}>{scan.source_confidence==="tagged"?"Exact":scan.source_confidence==="detected"?"Detected":"Unknown"}</span></td></tr>)}{!recent.items.length?<tr><td colSpan={8}><div className="qrfy-no-data">No verified scans in this scope.</div></td></tr>:null}</tbody></table></div><nav className="qsv2-cursor-nav"><button onClick={recentPrev} disabled={!recentHistory.length}>← Previous</button><span>Raw history page {recentHistory.length+1}</span><button onClick={recentNext} disabled={!recent.has_more||!recent.next_cursor}>Next →</button></nav></section>

    <section className="qav2-scale-note"><strong>Scale behavior</strong><p>QR library operations are server-side and cursor-paged. Analytics reads compact daily/dimension aggregates instead of scanning every raw event for every dashboard card. Verified scans keep bot filtering, and “unique devices” remains a browser/device identifier—not a claim of unique human people.</p></section>
    {loading?<div className="qrfy-loading-float">Refreshing scale analytics…</div>:null}
  </main>
}
