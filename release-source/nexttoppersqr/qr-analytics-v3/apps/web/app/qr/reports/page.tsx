"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "/backend";

type Place = { country:string; state:string; district:string; city:string; scans:number; unique_browsers:number };
type Device = { device_token:string; device_type:string; operating_system:string; browser:string; device_model:string; scans:number; qr_campaigns:number; last_seen:string };
type Qr = { qr_id:string; qr_name:string; scans:number; unique_browsers:number };
type Report = { verified_scans:number; unique_browsers:number; locations:Place[]; devices:Device[]; qr_codes:Qr[]; location_quality:string; device_quality:string; limited_to_top_groups:number };
type Official = { store:string; app_id:string; kind:string; count:number; latest_date:string };
type Store = { status:string; verified_store_downloads:Official[]; note:string };
type Code = {id:string; name:string};

function number(value: number | undefined) { return Number(value || 0).toLocaleString("en-IN"); }
function query(id: string) { return id ? "?qr_id=" + encodeURIComponent(id) : ""; }

export default function QrGeoAndStoreReports() {
  const [selected,setSelected] = useState("");
  const [codes,setCodes] = useState<Code[]>([]);
  const [report,setReport] = useState<Report | null>(null);
  const [stores,setStores] = useState<Store | null>(null);
  const [error,setError] = useState("");
  const [loading,setLoading] = useState(true);
  const [tab,setTab] = useState<"location" | "device" | "stores">("location");
  const [search,setSearch] = useState("");

  useEffect(() => {
    let active = true;
    fetch(API + "/api/v1/qr-codes", {credentials:"same-origin"})
      .then(r=>r.ok?r.json():Promise.reject(Error("Could not read QR codes")))
      .then((v:Code[])=>{if(active)setCodes(Array.isArray(v)?v:[]);})
      .catch(()=>{});
    return ()=>{active=false};
  },[]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    const json = (url:string) => fetch(url,{credentials:"same-origin"})
      .then(async r=>{if(!r.ok)throw Error("Request failed: "+r.status);return r.json();});
    Promise.all([
      json(API + "/api/v1/qr-reports/summary" + query(selected)),
      json(API + "/api/v1/qr-reports/stores")
    ]).then(([a,b]:[Report,Store])=>{
      if(active){setReport(a);setStores(b);}
    }).catch(e=>{if(active)setError(String(e?.message||e));})
      .finally(()=>{if(active)setLoading(false);});
    return ()=>{active=false;};
  },[selected]);

  const filter = search.trim().toLowerCase();
  const places = (report?.locations || []).filter(v=>!filter ||
    [v.country,v.state,v.district,v.city].some(s=>s.toLowerCase().includes(filter)));
  const devices = (report?.devices || []).filter(v=>!filter ||
    [v.device_token,v.device_type,v.operating_system,v.browser,v.device_model].some(s=>s.toLowerCase().includes(filter)));
  const totals = stores?.verified_store_downloads || [];
  const apple = totals.filter(r=>r.store==="apple");
  const play = totals.filter(r=>r.store==="play");

  return <main style={{maxWidth:1250,margin:"auto",padding:"26px 20px",fontFamily:"system-ui,sans-serif"}}>
    <nav style={{display:"flex",gap:18,marginBottom:24}}>
      <Link href="/qr/stats">← QR Statistics</Link><Link href="/qr/codes">My QR Codes</Link>
    </nav>
    <header>
      <h1 style={{fontSize:30,fontWeight:800}}>QR Geography, Devices & App Downloads</h1>
      <p>Per-QR scan intelligence, official store totals and downloadable PDF/CSV reports.</p>
    </header>
    <section style={{display:"flex",gap:12,alignItems:"end",flexWrap:"wrap",margin:"24px 0"}}>
      <label style={{display:"grid",gap:5,minWidth:290}}>QR campaign
        <select value={selected} onChange={e=>setSelected(e.target.value)} style={{padding:12}}>
          <option value="">All QR campaigns</option>
          {codes.map(v=><option key={v.id} value={v.id}>{v.name}</option>)}
        </select>
      </label>
      <a href={API+"/api/v1/qr-reports/scans.csv"+query(selected)} download style={{padding:12,border:"1px solid",borderRadius:6}}>Download CSV</a>
      <a href={API+"/api/v1/qr-reports/summary.pdf"+query(selected)} download style={{padding:12,border:"1px solid",borderRadius:6}}>Download PDF</a>
    </section>
    {loading?<p>Loading report…</p>:null}
    {error?<p role="alert" style={{color:"crimson"}}>{error}. Install the reporting backend module before using this screen.</p>:null}
    {report?<section style={{display:"flex",gap:20,flexWrap:"wrap",marginBottom:24}}>
      <article><strong style={{fontSize:26}}>{number(report.verified_scans)}</strong><div>Verified QR scans</div></article>
      <article><strong style={{fontSize:26}}>{number(report.unique_browsers)}</strong><div>Unique browsers (estimated)</div></article>
      <article><strong style={{fontSize:26}}>{number(report.qr_codes.length)}</strong><div>QR campaigns in top results</div></article>
    </section>:null}
    <div style={{display:"flex",gap:10,marginBottom:18,flexWrap:"wrap"}}>
      <button onClick={()=>setTab("location")} aria-pressed={tab==="location"}>Country / State / District / City</button>
      <button onClick={()=>setTab("device")} aria-pressed={tab==="device"}>Device scan counts</button>
      <button onClick={()=>setTab("stores")} aria-pressed={tab==="stores"}>Play Store / App Store</button>
    </div>
    {tab!=="stores"?<input placeholder="Filter country, state, city or device..." value={search} onChange={e=>setSearch(e.target.value)}
      style={{padding:11,width:"min(100%,480px)",marginBottom:16}} aria-label="Filter report"/>:null}
    {tab==="location"?<>
      <p style={{fontSize:13}}>{report?.location_quality}. City is not automatically a district; missing information is shown as Unknown.</p>
      <div style={{overflowX:"auto"}}><table style={{width:"100%",textAlign:"left",borderCollapse:"collapse"}}>
        <thead><tr>{["Country","State / Region","District","City","Scans","Unique browsers"].map(v=><th key={v} style={{padding:10,borderBottom:"1px solid #aaa"}}>{v}</th>)}</tr></thead>
        <tbody>{places.map((v,i)=><tr key={i}><td>{v.country}</td><td>{v.state}</td><td>{v.district}</td><td>{v.city}</td><td>{number(v.scans)}</td><td>{number(v.unique_browsers)}</td></tr>)}</tbody>
      </table></div>
    </>:null}
    {tab==="device"?<>
      <p style={{fontSize:13}}>{report?.device_quality}. Private browsing or clearing storage may change a device token.</p>
      <div style={{overflowX:"auto"}}><table style={{width:"100%",textAlign:"left",borderCollapse:"collapse"}}>
        <thead><tr>{["Device token","Type","OS","Browser","Model (if supplied)","QRs","Scans","Last scan UTC"].map(v=><th key={v} style={{padding:10,borderBottom:"1px solid #aaa"}}>{v}</th>)}</tr></thead>
        <tbody>{devices.map((v,i)=><tr key={i}><td>{v.device_token||"Unknown"}</td><td>{v.device_type}</td><td>{v.operating_system}</td><td>{v.browser}</td><td>{v.device_model}</td><td>{number(v.qr_campaigns)}</td><td>{number(v.scans)}</td><td>{v.last_seen}</td></tr>)}</tbody>
      </table></div>
    </>:null}
    {tab==="stores"?<>
      <p>Only confirmed aggregated data imported from official store reports is shown here. A QR scan is not proof of an install, and these totals are not automatically attributed to individual QR codes.</p>
      <h2>Google Play</h2>
      {play.length?play.map((v,i)=><p key={i}>{v.app_id} · {v.kind}: <strong>{number(v.count)}</strong> (latest {v.latest_date})</p>):<p>No official Play Console report imported.</p>}
      <h2>Apple App Store</h2>
      {apple.length?apple.map((v,i)=><p key={i}>{v.app_id} · {v.kind}: <strong>{number(v.count)}</strong> (latest {v.latest_date})</p>):<p>No official App Store Connect report imported.</p>}
      <p style={{fontSize:13}}>Campaign-specific install attribution needs Play Install Referrer in the Android app and App Store campaign links/analytics for Apple. Historical QR scans alone cannot establish that relationship.</p>
    </>:null}
    <footer style={{marginTop:32,fontSize:13}}>
      Report shows the top {report?.limited_to_top_groups || 1000} grouped locations/devices/QR campaigns. CSV streams all verified scan rows.
      Original QR images, redirect URLs and Cloudflare KV are unchanged.
    </footer>
  </main>;
}
