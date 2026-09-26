"use client";

import Link from "next/link";
import { ChangeEvent, useCallback, useEffect, useMemo, useState } from "react";
import { PaginationControls } from "../../../components/pagination-controls";
import { QrProductNav } from "../../../components/qr-product-nav";
import { paginateItems } from "../../../lib/pagination";

const API = process.env.NEXT_PUBLIC_API_URL ?? "/backend";

type Design = { foreground_color:string; background_color:string; dot_style:string; marker_border_style:string; marker_center_style:string; frame_style:string; frame_text:string|null; logo_asset_id:string|null; logo_scale_percent:number };
type Experience = { mode:string; asset_id:string|null; title:string; message:string; accent_color:string; background_color:string; image_fit:string; image_scale_percent:number };
type Template = { id:string; name:string; description:string; tracking_mode:"tracked"|"direct"; identity_mode:"anonymous"|"email"; design:Design; experience:Experience; is_default:boolean; qr_count:number; created_at:string; updated_at:string };

function dateLabel(value:string){const d=new Date(value);return Number.isNaN(d.valueOf())?value:new Intl.DateTimeFormat("en-IN",{day:"2-digit",month:"short",year:"numeric"}).format(d)}

export default function QrTemplatesPage(){
  const [items,setItems]=useState<Template[]>([]);
  const [search,setSearch]=useState("");
  const [page,setPage]=useState(1);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  const [message,setMessage]=useState("");

  const load=useCallback(async()=>{setLoading(true);setError("");try{const r=await fetch(`${API}/api/v1/qr-templates`,{cache:"no-store"});if(!r.ok)throw new Error("Could not load QR templates.");setItems(await r.json() as Template[])}catch(e){setError(e instanceof Error?e.message:"Could not load QR templates.")}finally{setLoading(false)}},[]);
  useEffect(()=>{void load()},[load]);
  useEffect(()=>{setPage(1)},[search]);

  const filtered=useMemo(()=>{const needle=search.trim().toLowerCase();if(!needle)return items;return items.filter(item=>`${item.name} ${item.description} ${item.tracking_mode} ${item.identity_mode}`.toLowerCase().includes(needle))},[items,search]);
  const pageData=useMemo(()=>paginateItems(filtered,page,6),[filtered,page]);
  useEffect(()=>{if(page!==pageData.page)setPage(pageData.page)},[page,pageData.page]);

  async function patch(id:string,body:object){const r=await fetch(`${API}/api/v1/qr-templates/${id}`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});if(!r.ok)throw new Error("Template update failed.");await load()}
  async function makeDefault(item:Template){try{await patch(item.id,{is_default:true});setMessage(`${item.name} is now the default template.`)}catch(e){setError(e instanceof Error?e.message:"Could not set default.")}}
  async function duplicate(item:Template){setError("");const r=await fetch(`${API}/api/v1/qr-templates/${item.id}/duplicate`,{method:"POST"});if(!r.ok){setError("Could not duplicate this template.");return}const copy=await r.json() as Template;setMessage(`${copy.name} created.`);await load()}
  async function remove(item:Template){if(!window.confirm(`Delete template “${item.name}”?\n\nAlready-created QR codes remain independent and continue working.`))return;const r=await fetch(`${API}/api/v1/qr-templates/${item.id}`,{method:"DELETE"});if(!r.ok){setError("Could not delete template.");return}setMessage(`${item.name} deleted. Existing QR codes were not changed.`);await load()}

  return <main className="qrfy-page qr-route-enter"><QrProductNav/>
    <header className="qrfy-page-header"><div><p className="qrfy-kicker">Reusable design system</p><h1>QR Templates</h1><p>Create multiple reusable designs. Logo, full-screen image, colors, QR styling, scan experience and identity settings stay saved while Name + URL change.</p></div><Link className="qrfy-button primary" href="/qr">＋ Build a template</Link></header>
    {message?<div className="qrfy-toast success">{message}</div>:null}{error?<div className="qrfy-toast error">{error}</div>:null}
    <section className="qr-template-hero qrfy-panel"><div><span>HOW IT WORKS</span><h2>Design once. Generate many.</h2><p>Open New QR, perfect the logo/background/colors, then save the current design as a named template. Choose that template in Bulk Create and enter only QR Name + URL.</p></div><Link className="qrfy-button secondary" href="/qr/bulk">Open Bulk Create →</Link></section>

    <section className="qrfy-panel qr-template-toolbar-v125">
      <label className="qrfy-search"><span>⌕</span><input value={search} onChange={(event:ChangeEvent<HTMLInputElement>)=>setSearch(event.target.value)} placeholder="Search templates…"/></label>
      <div><strong>{filtered.length.toLocaleString("en-IN")}</strong><span> matching template{filtered.length===1?"":"s"}</span></div>
    </section>

    <section className="qr-template-grid">
      {pageData.items.map(item=><article key={item.id} className={`qrfy-panel qr-template-card ${item.is_default?"default":""}`}>
        <div className="qr-template-card-top"><div className="qr-template-swatch" style={{background:item.design.background_color,borderColor:item.design.foreground_color}}><i style={{background:item.design.foreground_color}}/><b style={{background:item.experience.accent_color}}/></div><div><small>{item.is_default?"DEFAULT TEMPLATE":"SAVED TEMPLATE"}</small><h2>{item.name}</h2><p>{item.description||"Reusable QR + scan-screen design"}</p></div></div>
        <div className="qr-template-facts"><span>{item.tracking_mode==="tracked"?"Tracked analytics":"Direct"}</span><span>{item.identity_mode==="email"?"Email identity":"Anonymous"}</span><span>{item.experience.mode==="page"?"Full-screen image":item.experience.mode==="logo"?"Opening logo":"Animated brand"}</span><span>{item.qr_count} QR codes</span></div>
        <div className="qr-template-meta"><span>Updated {dateLabel(item.updated_at)}</span><span>{item.design.logo_asset_id?"QR logo saved":"No QR logo"}</span></div>
        <div className="qr-template-actions"><Link className="qrfy-button primary" href={`/qr/bulk?template=${item.id}`}>Bulk Create</Link><Link className="qrfy-button ghost" href={`/qr?template=${item.id}`}>Use in Builder</Link><button className="qrfy-button ghost" onClick={()=>void duplicate(item)}>Duplicate</button>{!item.is_default?<button className="qrfy-button ghost" onClick={()=>void makeDefault(item)}>Set Default</button>:null}<button className="qr-template-delete" onClick={()=>void remove(item)}>Delete</button></div>
      </article>)}
      {!loading&&!pageData.total?<div className="qrfy-panel qrfy-no-data">No saved templates match this search. Create one from the QR Builder or clear the search.</div>:null}
    </section>
    <PaginationControls page={pageData.page} pages={pageData.pages} total={pageData.total} start={pageData.start} end={pageData.end} onPageChange={setPage} label="templates"/>
    {loading?<div className="qrfy-loading-float">Loading templates…</div>:null}
  </main>
}
