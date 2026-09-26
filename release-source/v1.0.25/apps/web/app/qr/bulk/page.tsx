"use client";

import Link from "next/link";
import { ChangeEvent, useCallback, useEffect, useMemo, useState } from "react";
import { PaginationControls } from "../../../components/pagination-controls";
import { QrProductNav } from "../../../components/qr-product-nav";
import { parseBulkQrRows } from "../../../lib/qr-bulk";
import { paginateItems } from "../../../lib/pagination";

const API = process.env.NEXT_PUBLIC_API_URL ?? "/backend";
type Template={id:string;name:string;description:string;tracking_mode:string;identity_mode:string;is_default:boolean;qr_count:number;design:{foreground_color:string;background_color:string;logo_asset_id:string|null};experience:{mode:string;asset_id:string|null;accent_color:string;background_color:string}};
type Row={name:string;url:string};
type Created={id:string;name:string;slug:string;target_url:string;template_name:string|null;total_scans:number;unique_visitors:number};

function validUrl(value:string){try{const u=new URL(value.trim());return u.protocol==="http:"||u.protocol==="https:"}catch{return false}}
async function copyText(value:string){if(navigator.clipboard?.writeText){try{await navigator.clipboard.writeText(value);return}catch{/* fallback */}}const area=document.createElement("textarea");area.value=value;area.setAttribute("readonly","");area.style.position="fixed";area.style.opacity="0";document.body.appendChild(area);area.select();document.execCommand("copy");area.remove()}

export default function QrBulkPage(){
  const [templates,setTemplates]=useState<Template[]>([]);
  const [selected,setSelected]=useState("");
  const [templatePage,setTemplatePage]=useState(1);
  const [rows,setRows]=useState<Row[]>([{name:"",url:""},{name:"",url:""},{name:"",url:""}]);
  const [rowPage,setRowPage]=useState(1);
  const [paste,setPaste]=useState("");
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [message,setMessage]=useState("");
  const [created,setCreated]=useState<Created[]>([]);
  const [resultPage,setResultPage]=useState(1);

  const load=useCallback(async()=>{try{const r=await fetch(`${API}/api/v1/qr-templates`,{cache:"no-store"});if(!r.ok)throw new Error();const data=await r.json() as Template[];setTemplates(data);const query=new URLSearchParams(window.location.search).get("template");const initial=(query&&data.some(x=>x.id===query))?query:data.find(x=>x.is_default)?.id||data[0]?.id||"";setSelected(current=>current||initial);if(initial){const index=data.findIndex(x=>x.id===initial);if(index>=0)setTemplatePage(Math.floor(index/6)+1)}}catch{setError("Could not load templates.")}},[]);
  useEffect(()=>{void load()},[load]);

  const template=templates.find(x=>x.id===selected);
  const analyticsReady=template?.tracking_mode==="tracked";
  const validRows=useMemo(()=>rows.filter(row=>row.name.trim()&&validUrl(row.url)),[rows]);
  const invalidCount=rows.filter(row=>(row.name.trim()||row.url.trim())&&!(row.name.trim()&&validUrl(row.url))).length;
  const templateData=useMemo(()=>paginateItems(templates,templatePage,6),[templates,templatePage]);
  const rowData=useMemo(()=>paginateItems(rows,rowPage,10),[rows,rowPage]);
  const resultData=useMemo(()=>paginateItems(created,resultPage,10),[created,resultPage]);

  useEffect(()=>{if(templatePage!==templateData.page)setTemplatePage(templateData.page)},[templatePage,templateData.page]);
  useEffect(()=>{if(rowPage!==rowData.page)setRowPage(rowData.page)},[rowPage,rowData.page]);
  useEffect(()=>{if(resultPage!==resultData.page)setResultPage(resultData.page)},[resultPage,resultData.page]);

  function setRow(index:number,key:keyof Row,value:string){setRows(current=>current.map((row,i)=>i===index?{...row,[key]:value}:row))}
  function addRow(){setRows(current=>{const next=[...current,{name:"",url:""}];setRowPage(Math.ceil(next.length/10));return next})}
  function removeRow(index:number){setRows(current=>current.filter((_,i)=>i!==index))}
  function applyPaste(){const parsed=parseBulkQrRows(paste);if(!parsed.length){setError("Paste at least one Name + URL row.");return}setRows(parsed);setRowPage(1);setPaste("");setMessage(`${parsed.length} rows imported.`);setError("")}
  async function filePicked(event:ChangeEvent<HTMLInputElement>){const file=event.target.files?.[0];if(!file)return;const text=await file.text();const parsed=parseBulkQrRows(text);if(!parsed.length){setError("The CSV/TXT file did not contain Name + URL rows.");return}setRows(parsed);setRowPage(1);setMessage(`${parsed.length} rows loaded from ${file.name}.`)}
  async function generate(){if(!selected){setError("Choose a template first.");return}if(invalidCount||!validRows.length){setError("Every non-empty row needs a Name and valid http/https URL.");return}if(validRows.length>500){setError("Bulk creation is limited to 500 valid QR rows per request.");return}setBusy(true);setError("");setMessage("");try{const r=await fetch(`${API}/api/v1/qr-bulk`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({template_id:selected,items:validRows})});const body=await r.json().catch(()=>null) as {created?:Created[];detail?:string}|null;if(!r.ok)throw new Error(body?.detail||"Bulk creation failed.");const next=body?.created||[];setCreated(next);setResultPage(1);setMessage(`${next.length} QR codes created with ${template?.name||"the selected template"}. Each QR has its own analytics.`)}catch(e){setError(e instanceof Error?e.message:"Bulk creation failed.")}finally{setBusy(false)}}
  async function copyUrl(value:string,name:string){await copyText(value);setMessage(`URL copied for ${name}.`)}

  return <main className="qrfy-page qr-route-enter"><QrProductNav/>
    <header className="qrfy-page-header"><div><p className="qrfy-kicker">High-volume QR workflow</p><h1>Bulk QR Generator</h1><p>Choose one saved template, then enter only Name + URL. Every generated QR keeps independent tracking and per-QR analytics.</p></div><Link className="qrfy-button ghost" href="/qr/templates">Manage Templates</Link></header>
    {message?<div className="qrfy-toast success">{message}</div>:null}{error?<div className="qrfy-toast error">{error}</div>:null}
    <section className="qr-bulk-layout"><div className="qrfy-panel qr-bulk-main">
      <div className="qrfy-step-title"><span>1</span><div><h2>Choose template</h2><p>Logo, full-screen image, colors, design, scan screen, tracking and identity come from this template.</p></div></div>
      <div className="qr-bulk-template-list">{templateData.items.map(item=><button key={item.id} className={selected===item.id?"selected":""} onClick={()=>setSelected(item.id)}><i style={{background:item.design.foreground_color}}/><div><strong>{item.name}</strong><small>{item.tracking_mode} · {item.identity_mode} · {item.qr_count} existing QR</small></div>{item.is_default?<b>DEFAULT</b>:null}</button>)}</div>
      {!templates.length?<div className="qr-bulk-empty">No template exists yet. <Link href="/qr">Create a design and save it as a template →</Link></div>:null}
      <PaginationControls page={templateData.page} pages={templateData.pages} total={templateData.total} start={templateData.start} end={templateData.end} onPageChange={setTemplatePage} label="templates"/>

      <div className="qrfy-step-title qr-bulk-step"><span>2</span><div><h2>Add QR Name + URL</h2><p>Manual rows, spreadsheet paste, CSV or TXT. Up to 500 QR codes per bulk job. Input is paged at 10 rows.</p></div></div>
      <div className="qr-bulk-import"><textarea value={paste} onChange={(e:ChangeEvent<HTMLTextAreaElement>)=>setPaste(e.target.value)} placeholder={'Paste from Excel / Google Sheets:\nCommerce 11th\thttps://example.com/11\nCommerce 12th\thttps://example.com/12'} /><div><button className="qrfy-button secondary" onClick={applyPaste}>Paste / Import Rows</button><label className="qrfy-button ghost qr-file-button">Upload CSV/TXT<input type="file" accept=".csv,.txt,text/csv,text/plain" onChange={(e:ChangeEvent<HTMLInputElement>)=>void filePicked(e)}/></label></div></div>
      <div className="qr-bulk-table"><div className="qr-bulk-head"><span>#</span><span>QR Name</span><span>Destination URL</span><span/></div>{rowData.items.map((row,offset)=>{const index=rowData.start+offset;return <div className="qr-bulk-row" key={index}><span>{index+1}</span><input value={row.name} maxLength={120} onChange={(e:ChangeEvent<HTMLInputElement>)=>setRow(index,"name",e.target.value)} placeholder="Commerce 11th"/><input value={row.url} onChange={(e:ChangeEvent<HTMLInputElement>)=>setRow(index,"url",e.target.value)} placeholder="https://..."/><button title="Remove row" onClick={()=>removeRow(index)}>×</button></div>})}</div>
      <div className="qr-bulk-row-footer-v125"><button className="qrfy-button ghost" onClick={addRow}>＋ Add row</button><PaginationControls page={rowData.page} pages={rowData.pages} total={rowData.total} start={rowData.start} end={rowData.end} onPageChange={setRowPage} label="input rows"/></div>
      <div className="qr-bulk-generate"><div><strong>{validRows.length} ready</strong><span>{invalidCount?`${invalidCount} rows need correction`:`All non-empty rows valid`}</span></div><button className="qrfy-button primary" disabled={busy||!selected||!analyticsReady||!validRows.length||validRows.length>500||invalidCount>0} onClick={()=>void generate()}>{busy?"Generating…":`Generate ${validRows.length||"All"} QR Codes`}</button></div>
    </div>
    <aside className="qrfy-panel qr-bulk-summary"><span>SELECTED TEMPLATE</span>{template?<><h2>{template.name}</h2>{!analyticsReady?<div className="qrfy-toast error">This is a Direct template. Choose/save a Tracked template so every bulk QR has independent analytics.</div>:null}<div className="qr-bulk-preview" style={{background:template.design.background_color}}><i style={{background:template.design.foreground_color}}/><b style={{background:template.experience.accent_color}}/></div><dl><div><dt>Tracking</dt><dd>{template.tracking_mode}</dd></div><div><dt>Identity</dt><dd>{template.identity_mode}</dd></div><div><dt>QR logo</dt><dd>{template.design.logo_asset_id?"Saved":"None"}</dd></div><div><dt>Full-screen image</dt><dd>{template.experience.mode==="page"&&template.experience.asset_id?"Saved":template.experience.mode}</dd></div></dl></>:<p>Choose a template.</p>}</aside></section>

    {created.length?<section className="qrfy-panel qr-bulk-results"><div className="qrfy-card-title"><div><span>GENERATED SUCCESSFULLY</span><h2>{created.length} independent QR campaigns</h2><p>Same design. Separate URL, scan count, unique devices, source analytics and history for every QR.</p></div><Link className="qrfy-button secondary" href="/qr/codes">Open My QR Codes</Link></div><div className="qr-bulk-result-grid qr-bulk-result-grid-v125">{resultData.items.map(code=><article key={code.id}><img src={`${API}/api/v1/qr-codes/${code.id}/image?format=png`} alt={`QR for ${code.name}`}/><div><strong>{code.name}</strong><small title={code.target_url}>{code.target_url}</small></div><div><button onClick={()=>void copyUrl(code.target_url,code.name)}>Copy URL</button><a href={`${API}/api/v1/qr-codes/${code.id}/image?format=png&download=true`}>PNG</a><Link href={`/qr/stats?qr_id=${code.id}`}>Analytics</Link></div></article>)}</div><PaginationControls page={resultData.page} pages={resultData.pages} total={resultData.total} start={resultData.start} end={resultData.end} onPageChange={setResultPage} label="generated QR codes"/></section>:null}
  </main>
}
