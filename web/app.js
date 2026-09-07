import {$,$$,E,get,post,icon,button,badge,stats,pageHead,empty,listen,toast,modal,showJSON,
        runJob,download,artifactsHTML,bindArtifacts,pickPath,bytes,when,fileIcon,dropZone,bindDrop,jobsHTML,bindJobs,mount} from './common.js';
const info=await get('info');
let state,selectedId=null,tab='workbench',hexOffset=0;
const statusText={valid:'Checks passed',review:'Review notes',repairable:'Repair available',damaged:'Damaged',unrecoverable:'No recoverable bytes'};
const statusKind=s=>s==='valid'?'good':s==='damaged'||s==='unrecoverable'?'bad':'warn';
const guide=`<p>RecoveryLab creates copies. It never repairs a source file in place.</p><ol class="list-note"><li>Drop a file or select Use sample files.</li><li>Read the checks and coverage notes.</li><li>Run an available recovery method.</li><li>Compare the report and open the recovered copy in its normal application.</li></ol><p class="muted small">The app cannot recreate bytes that no longer exist. A checksum check is not proof that a document renders correctly.</p>`;
async function refresh(){state=await get('state');}
async function inspectPaths(paths){const result=await runJob('inspect',{paths});selectedId=result.inspections[0]?.id;await refresh();if(tab!=='workbench'){location.hash='workbench';}else await renderWorkbench();toast('Inspection complete. Read the checks before creating a copy.');}
async function loadDemo(){const sample=await get('examples');await inspectPaths(sample.files);}
function metrics(){return stats([['Files inspected',state.stats.inspected,'Recent inspection records','search'],['Available copy methods',state.stats.repairable,'Conservative, format-specific operations','tools'],['Recovered copies',state.stats.copies,'Each copy has an audit report','file']]);}
async function renderWorkbench(){
  if(!state.entries.some(e=>e.id===selectedId))selectedId=state.entries[0]?.id||null;
  $('#view').innerHTML=pageHead('FILE INSPECTION & RECOVERY','Inspect first. Recover a copy.','Read file signatures, validate supported structures, and recover the bytes that still exist.',`${button('choose-source','Choose local file','folder')}${button('use-samples','Use sample files','play','primary')}`)+metrics()+dropZone('recovery-drop')
  +`<div class="split wide-detail"><section class="panel"><div class="panel-head"><h2>Inspected files</h2>${button('recover-batch','Recover supported','tools','ghost',state.entries.some(e=>e.repair_available)?'':'disabled')}</div><div>${state.entries.length?state.entries.map(e=>`<button class="file-row ${e.id===selectedId?'selected':''}" data-inspection="${E(e.id)}">${fileIcon(e.name)}<div class="file-main"><strong>${E(e.name)}</strong><small>${bytes(e.size)} · ${E(e.detected.kind.toUpperCase())} · ${E(when(e.created))}</small></div>${badge(e.output?'Copy created':statusText[e.status]||e.status,e.output?'good':statusKind(e.status))}</button>`).join(''):empty('No files inspected','Drop a file above or open the sample cases.','tools')}</div></section><aside class="panel" id="inspection-panel"></aside></div><div class="notice info">${icon('shield')}<span>Inspection does not execute document macros or programs. Recoveries go to a new output folder. Unsupported repairs are not guessed.</span></div>`;
  listen('#use-samples','click',loadDemo);
  listen('#choose-source','click',async()=>{const path=await pickPath(info.example_path,true);if(path)await inspectPaths([path]);});
  bindDrop('recovery-drop',files=>inspectPaths(files.map(f=>f.path)));
  listen('[data-inspection]','click',async(_,node)=>{selectedId=node.dataset.inspection;$$('[data-inspection]').forEach(n=>n.classList.toggle('selected',n===node));await renderInspection();});
  listen('#recover-batch','click',async()=>{const files=state.entries.filter(e=>e.repair_available&&!e.output);if(!files.length){toast('All supported files in this list already have a recovered copy.');return;}for(const entry of files)await runJob('repair',{id:entry.id});await refresh();await renderWorkbench();toast(`${files.length} new recovered copies created.`);});
  await renderInspection();
}
async function renderInspection(){
  const panel=$('#inspection-panel');if(!panel)return;
  if(!selectedId){panel.innerHTML=empty('Inspection details','Select a file to inspect its structure and available recovery method.','search');return;}
  const row=await get('inspection',{id:selectedId}),report=row.report;
  const passed=report.checks.filter(c=>c.status==='pass').length;
  panel.innerHTML=`<div class="panel-head"><div><h2 style="overflow-wrap:anywhere">${E(report.name)}</h2><p>${E(report.detected.basis)}</p></div>${badge(statusText[report.status]||report.status,statusKind(report.status))}</div><div class="panel-body"><div class="key-values"><span>Detected format</span><strong>${E(report.detected.kind.toUpperCase())}</strong><span>Input size</span><strong>${bytes(report.size)}</strong><span>Checks passed</span><strong>${passed} of ${report.checks.length}</strong><span>Byte entropy</span><strong>${report.entropy.toFixed(3)} bits per byte <span class="muted tiny">(sample, not a health score)</span></strong></div><h3>Structure checks</h3>${report.checks.map(c=>`<div class="check-row ${E(c.status)}">${icon(c.status==='pass'?'check':'alert')}<div><strong>${E(c.label)}</strong><p>${E(c.detail)}</p></div></div>`).join('')}<div class="divider"></div><div class="section-actions">${button('recover-file',report.repair_available?report.repair_label:'No supported repair','tools','primary',report.repair_available?'':'disabled')}${button('view-hex','Hex view','grid','ghost')}${button('export-inspection','Report','download','ghost')}</div><p class="hash-line" style="margin-top:16px">Source SHA-256<br>${E(report.sha256)}</p>${Object.keys(report.details).length?button('format-details','View format details','file','ghost'):''}<div id="recovery-output"></div></div>`;
  listen('#recover-file','click',async()=>{await runJob('repair',{id:selectedId,escape_formulas:true});await refresh();if(tab==='workbench')await renderWorkbench();toast('Recovered copy created. The original remains unchanged.');});
  listen('#export-inspection','click',async()=>download(await post('export',{id:selectedId})));
  listen('#format-details','click',()=>showJSON('Format details',report.details));
  listen('#view-hex','click',async()=>{hexOffset=0;await renderHex();});
  if(row.output){
    const result=row.output;const out=$('#recovery-output');
    out.innerHTML=`<div class="divider"></div><div class="notice good">${icon('check')}<span>New copy created. Original hash ${result.original_unchanged?'still matches':'does not match; inspect the source again'}.</span></div><h3>Recovery notes</h3>${result.notes.map(n=>`<p class="small muted">${E(n)}</p>`).join('')}<div class="inline-meta">${badge('Before: '+(statusText[result.before_status]||result.before_status),'warn')}${badge('After: '+(statusText[result.after_status]||result.after_status),'good')}</div>${artifactsHTML([result.output,result.report])}`;
    bindArtifacts([result.output,result.report],out);
  }
}
async function renderHex(){
  const result=await get('hex',{id:selectedId,offset:hexOffset});
  modal('Read-only hex view',`<p class="small muted">Hex offsets identify positions in the original file. This view cannot edit bytes.</p><pre class="code-block" style="font-size:10px;white-space:pre">OFFSET    HEX BYTES                                          TEXT\n${result.rows.map(r=>`${r.offset}  ${r.hex.padEnd(47,' ')}  ${r.text}`).map(E).join('\n')}</pre><div class="input-row"><label class="small">Offset <input id="hex-offset" type="number" min="0" max="${result.size}" value="${hexOffset}" style="width:120px"></label>${button('hex-go','Go','arrow')}${button('hex-previous','Previous 256 bytes','','ghost')}${button('hex-next','Next 256 bytes','','ghost')}</div>`);
  listen('#hex-go','click',async()=>{hexOffset=Number($('#hex-offset').value);await renderHex();});
  listen('#hex-previous','click',async()=>{hexOffset=Math.max(0,hexOffset-256);await renderHex();});
  listen('#hex-next','click',async()=>{hexOffset=Math.min(Math.max(0,result.size-1),hexOffset+256);await renderHex();});
}
async function route(next){tab=next;await refresh();
  if(tab==='workbench')return renderWorkbench();
  if(tab==='history'){
    $('#view').innerHTML=pageHead('RECOVERY HISTORY','Keep the repair evidence.','Each recovered copy records its input hash, output hash, and exact transformation notes.')+metrics()+`<div class="panel">${jobsHTML(state.jobs)}</div>`;bindJobs();return;
  }
  const methods=[['JSON','Parse syntax and locate errors','Remove trailing commas outside strings. Reformat valid JSON.','Other syntax errors remain unsupported.'],['CSV / TSV','Detect delimiter, encoding, and row widths','Convert to UTF-8 CSV. Pad short rows. Preserve extra cells.','Broken quoting is not guessed. Formula-like values are escaped by default.'],['ZIP','Check entry headers, sizes, and CRC values','Rebuild readable entries. Recover valid local entries without a central directory.','Encrypted, unsafe, incomplete, and unsupported entries are omitted.'],['DOCX / XLSX / PPTX','Inspect the underlying ZIP package','Rebuild valid Office packages. Export incomplete parts as ZIP.','The app does not certify that the Office document renders correctly.'],['PNG','Check signature, chunk boundaries, and CRC values','Copy verified chunks through the end marker.','JPEG and GIF sources can be decoded into a new PNG. Incomplete pixel data is not guessed.'],['Text','Check supported text encoding','Write a new UTF-8 text copy.','Unsupported binary data is not treated as text.'],['PDF / JPEG / GIF / SQLite','Identify supported signatures; PDF end-marker check','Rebuild PDF pages, decode images, or recover readable SQLite data.','Open outputs to verify content. Local FFmpeg remuxes supported video streams.']];
  $('#view').innerHTML=pageHead('FORMAT COVERAGE','Repair only what can be checked.','Recovery methods are deliberately narrow. Missing content is never invented.')+`<div class="panel"><div class="panel-body">${guide}</div></div><div class="panel"><table><thead><tr><th>Format</th><th>Inspection</th><th>Recovery method</th><th>Limit</th></tr></thead><tbody>${methods.map(r=>`<tr>${r.map(c=>`<td>${E(c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div><div class="notice">${icon('alert')}<span>This version does not recover deleted disk sectors, recreate missing packets, break passwords, or assign recovery probabilities.</span></div>`;
}
mount(info,[['workbench','Recovery workbench','tools'],['history','Job history','clock'],['formats','Format coverage','file']],route,guide);
