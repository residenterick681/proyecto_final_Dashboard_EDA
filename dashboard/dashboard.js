'use strict';
const DATA=JSON.parse(document.getElementById('payload').textContent);
const $=id=>document.getElementById(id), fmt=(v,d=0)=>v===null||!Number.isFinite(v)?'—':v.toLocaleString('es-EC',{maximumFractionDigits:d,minimumFractionDigits:d});
const valid=v=>typeof v==='number'&&Number.isFinite(v), sum=a=>a.reduce((s,v)=>s+(valid(v)?v:0),0), mean=a=>a.length?sum(a)/a.length:null;
const median=a=>{a=a.filter(valid).sort((a,b)=>a-b);return a.length?(a[Math.floor(a.length/2)]+a[Math.floor((a.length-1)/2)])/2:null};
const escapeHTML=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const allMonths=[...new Set(DATA.rows.map(r=>r.fecha.slice(0,7)))].sort();
const monthLabel=s=>new Date(s+'-15T12:00:00').toLocaleDateString('es-EC',{month:'short',year:'numeric'});
const names=Object.fromEntries(DATA.rows.map(r=>[r.activo,r.nombre_activo]));
for(const id of ['start','end']) $(id).innerHTML=allMonths.map(m=>`<option value="${m}">${monthLabel(m)}</option>`).join('');
for(const a of Object.keys(names).sort()) $('asset').add(new Option(`${a} · ${names[a]}`,a));
function defaults(){ $('start').value='2026-01';$('end').value='2026-08';$('asset').value='all';$('metric').value='crudo';$('balanced').checked=false; }
defaults();
const baseLayout={font:{family:'Segoe UI, Arial',size:11,color:'#38514a'},paper_bgcolor:'transparent',plot_bgcolor:'transparent',margin:{l:65,r:20,t:14,b:48},showlegend:false,xaxis:{gridcolor:'#eef1eb',zeroline:false},yaxis:{gridcolor:'#e7eee7',zeroline:false},colorway:['#1c7b63','#c99a47','#719aae','#355449']};
function plot(id,traces,layout={}){Plotly.react(id,traces,structuredClone({...baseLayout,...layout}),{responsive:true,displayModeBar:false,locale:'es'});}
let selectedRows=[];
function pearson(xs,ys){const xm=mean(xs),ym=mean(ys),dx=xs.map(v=>v-xm),dy=ys.map(v=>v-ym);const den=Math.sqrt(sum(dx.map(x=>x*x))*sum(dy.map(y=>y*y)));return den?sum(dx.map((x,i)=>x*dy[i]))/den:null;}
function render(){
 const start=$('start').value,end=$('end').value,asset=$('asset').value,key=$('metric').value,unit=key==='crudo'?'barriles':'MPC',dailyUnit=key==='crudo'?'barriles/día':'MPC/día';
 const months=allMonths.filter(m=>m>=start&&m<=end);
 let rows=DATA.rows.filter(r=>r.fecha.slice(0,7)>=start&&r.fecha.slice(0,7)<=end&&(asset==='all'||r.activo===asset));
 const before=[...new Set(rows.map(r=>r.activo))];
 if($('balanced').checked){const complete=before.filter(a=>rows.filter(r=>r.activo===a&&valid(r[key])).length===months.length);rows=rows.filter(r=>complete.includes(r.activo));}
 selectedRows=rows;
 const assets=[...new Set(rows.map(r=>r.activo))].sort(), good=rows.filter(r=>valid(r[key]));
 const days=months.reduce((s,m)=>{const [y,mo]=m.split('-').map(Number);return s+new Date(y,mo,0).getDate()},0);
 const priceRows=DATA.prices.filter(r=>r.fecha.slice(0,7)>=start&&r.fecha.slice(0,7)<=end&&valid(r.precio_usd_barril));
 const groups=assets.map(a=>{const g=rows.filter(r=>r.activo===a),v=g.filter(r=>valid(r[key]));return{a,n:v.length,rows:g.length,total:v.length?sum(v.map(r=>r[key])):null,med:median(v.map(r=>r[key+'_diario'])),out:g.filter(r=>r['atipico_'+key+'_diario']).length}}).sort((a,b)=>(b.total??-1)-(a.total??-1));
 const total=good.length?sum(good.map(r=>r[key])):null;
 $('selection').textContent=`${monthLabel(start)} — ${monthLabel(end)} · ${asset==='all'?'Todos los activos':names[asset]}`;
 $('scope').textContent=`${rows.length} registros · ${assets.length} activos · ${months.length} meses calendario`;
 const alerts=[];
 if(start>end) alerts.push('El inicio es posterior al fin. Corrige el rango de fechas.');
 if(!rows.length) alerts.push('No hay registros para esta selección. Ajusta el período, el activo o el filtro de cobertura.');
 const small=groups.filter(g=>g.n<12);if(small.length)alerts.push(`${small.length} grupo(s) con n < 12 meses válidos. Cobertura inferior a un ciclo anual; interpreta sus comparaciones con cautela.`);
 const missing=rows.length-good.length, absent=assets.length*months.length-rows.length;
 if(missing||absent)alerts.push(`${missing} valor(es) de ${key} sin resolver y ${absent} combinación(es) activo-mes sin registro. Los totales son sumas observadas y pueden ser parciales.`);
 if(priceRows.length<months.length)alerts.push(`Precio disponible en ${priceRows.length}/${months.length} meses. No se imputan los meses faltantes.`);
 if(rows.some(r=>r.catalogo_faltante))alerts.push('AB16 no tiene nombre en el catálogo entregado. Se conserva separado de los demás activos.');
 $('alerts').innerHTML=alerts.map(t=>`<div class="notice">${escapeHTML(t)}</div>`).join('');
 const top3=groups.slice(0,3).reduce((s,g)=>s+(g.total??0),0);
 $('kpis').innerHTML=[['Volumen observado',total===null?'—':fmt(total/1e6,2)+' M',`${unit} · n = ${good.length} activo-mes`],['Tasa diaria del período',total===null?'—':fmt(total/days),`${dailyUnit} · ${days} días calendario`],['Precio mensual medio',fmt(mean(priceRows.map(r=>r.precio_usd_barril)),2),`USD/barril · n = ${priceRows.length} meses · sin ponderar`],['Concentración: top 3',total?fmt(100*top3/total,1)+' %':'—',groups.slice(0,3).map(g=>g.a).join(' · ')||'Sin activos']].map(([l,v,s])=>`<article class="kpi"><div class="label">${l}</div><strong>${v}</strong><small>${s}</small></article>`).join('');
 const series=months.map(m=>{const g=rows.filter(r=>r.fecha.startsWith(m)),v=g.filter(r=>valid(r[key]));return{m,value:v.length?sum(v.map(r=>r[key])):null,n:v.length,price:DATA.prices.find(p=>p.fecha.startsWith(m))?.precio_usd_barril??null}});
 $('trendTitle').textContent=`${key==='crudo'?'Crudo':'Gas'} por mes`;
 $('trendSub').textContent=`Suma de ${unit} observados. El detalle muestra cuántos activos aportan cada mes.`;
 plot('trend',[{x:series.map(s=>s.m),y:series.map(s=>s.value===null?null:s.value/1e6),type:'scatter',mode:'lines+markers',connectgaps:false,line:{color:'#1c7b63',width:3},marker:{size:6},customdata:series.map(s=>s.n),hovertemplate:'%{x}<br>%{y:.3f} millones<br>n = %{customdata} activos<extra></extra>'}],{yaxis:{...baseLayout.yaxis,title:{text:`Millones de ${unit}`}},xaxis:{...baseLayout.xaxis,type:'date'}});
 const ordered=[...groups].reverse();
 plot('ranking',[{x:ordered.map(g=>g.total===null?null:g.total/1e6),y:ordered.map(g=>`${g.a} · n=${g.n}`),type:'bar',orientation:'h',marker:{color:'#40846d'},hovertemplate:'%{y}<br>%{x:.3f} millones<extra></extra>'}],{xaxis:{...baseLayout.xaxis,title:{text:`Millones de ${unit}`}},margin:{l:90,r:15,t:10,b:45}});
 plot('distribution',assets.map(a=>({type:'box',name:a,y:rows.filter(r=>r.activo===a&&valid(r[key+'_diario'])).map(r=>r[key+'_diario']),boxpoints:'outliers',marker:{color:'#3b866f',size:4},line:{width:1.3}})),{yaxis:{...baseLayout.yaxis,title:{text:dailyUnit}},xaxis:{...baseLayout.xaxis,tickangle:-30}});
 // Cohorte estable en TODO el intervalo; los meses no se multiplican por los activos.
 const stable=assets.filter(a=>rows.filter(r=>r.activo===a&&valid(r[key])).length===months.length);
 const pairs=months.map(m=>{const g=rows.filter(r=>r.fecha.startsWith(m)&&stable.includes(r.activo)),p=DATA.prices.find(r=>r.fecha.startsWith(m));return{m,x:p?.precio_usd_barril,y:g.length?sum(g.map(r=>r[key]))/g[0].dias_mes:null}}).filter(p=>valid(p.x)&&valid(p.y));
 const r=pairs.length>=12?pearson(pairs.map(p=>p.x),pairs.map(p=>p.y)):null;
 $('scatterSub').textContent=`${stable.length} activos con cobertura constante · n = ${pairs.length} meses pareados. ${pairs.length<12?'Menos de 12 meses: se omite r.':`Pearson descriptivo r = ${fmt(r,3)}; no es causal.`}`;
 plot('scatter',[{x:pairs.map(p=>p.x),y:pairs.map(p=>p.y),text:pairs.map(p=>p.m),type:'scatter',mode:'markers',marker:{size:9,color:'#bc8940',opacity:.8},hovertemplate:'%{text}<br>Precio: %{x:.2f} USD/barril<br>Tasa: %{y:,.0f}<extra></extra>'}],{xaxis:{...baseLayout.xaxis,title:{text:'Precio mensual · USD/barril'}},yaxis:{...baseLayout.yaxis,title:{text:dailyUnit}}});
 $('groups').innerHTML='<thead><tr><th>Activo</th><th>n válido / meses del período</th><th>Total observado</th><th>Mediana diaria</th><th>Atípicos IQR</th><th>Cobertura</th></tr></thead><tbody>'+groups.map(g=>`<tr><td>${escapeHTML(names[g.a])} (${g.a})</td><td class="num">${g.n} / ${months.length}</td><td class="num">${fmt(g.total,2)}</td><td class="num">${fmt(g.med,2)}</td><td class="num">${g.out}</td><td>${g.n<12?'<span class="tag">n &lt; 12</span>':'12+ meses'}${g.n<months.length?' · parcial':''}</td></tr>`).join('')+'</tbody>';
 const coverageAssets=asset==='all'?Object.keys(names).sort():[asset];
 plot('coverage',[{type:'heatmap',x:months,y:coverageAssets,z:coverageAssets.map(a=>months.map(m=>{const r=rows.find(r=>r.activo===a&&r.fecha.startsWith(m));return !r?0:valid(r[key])?2:1})),zmin:0,zmax:2,colorscale:[[0,'#e4e7e1'],[.25,'#e4e7e1'],[.25,'#edc06a'],[.75,'#edc06a'],[.75,'#40846d'],[1,'#40846d']],showscale:false,xgap:2,ygap:2,hovertemplate:'%{y} · %{x}<br>Estado: %{z} (0 ausente, 1 conflicto, 2 válido)<extra></extra>'}],{margin:{l:65,r:15,t:10,b:45},xaxis:{type:'category',tickangle:-35},yaxis:{type:'category'}});
}
for(const id of ['start','end','asset','metric','balanced'])$(id).addEventListener('change',render);
$('reset').addEventListener('click',()=>{defaults();render()});
document.querySelectorAll('[data-panel]').forEach(btn=>btn.addEventListener('click',()=>{document.querySelectorAll('[data-panel]').forEach(b=>b.setAttribute('aria-selected',String(b===btn)));document.querySelectorAll('[role=tabpanel]').forEach(p=>p.hidden=p.id!==btn.dataset.panel);setTimeout(()=>document.querySelectorAll('.js-plotly-plot').forEach(p=>Plotly.Plots.resize(p)),30)}));
$('download').addEventListener('click',()=>{const keys=['fecha','activo','nombre_activo','crudo','gas','precio_usd_barril','conflicto_crudo','conflicto_gas','filas_origen'];const quote=v=>'"'+String(v??'').replace(/"/g,'""')+'"';const csv='\ufeff'+[keys.join(','),...selectedRows.map(r=>keys.map(k=>quote(r[k])).join(','))].join('\r\n');const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));a.download='seleccion_eda.csv';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)});
const au=DATA.audit;
$('audit').innerHTML='<table>'+[['Filas originales',au.filas_produccion_original],['Claves activo-mes finales',au.filas_limpias],['Copias exactas extra',au.duplicados_exactos_extra],['Celdas contradictorias',au.celdas_conflictivas],['Huecos dentro de cobertura observada',au.huecos_interiores],['Registros sin nombre de catálogo',au.filas_sin_catalogo],['Registros sin precio',au.filas_sin_precio],['Ceros de gas conservados',au.ceros_gas_conservados]].map(([k,v])=>`<tr><td>${k}</td><td class="num">${v}</td></tr>`).join('')+'</table>';
$('decisionContent').innerHTML=DATA.decisions.map(d=>`<article class="decision"><h3>${escapeHTML(d.titulo)}</h3><p>${escapeHTML(d.evidencia)}</p><p><b>Acción:</b> ${escapeHTML(d.accion)}</p><p><b>Responsable:</b> ${escapeHTML(d.responsable)} · <b>Indicador:</b> ${escapeHTML(d.indicador)}</p><p><b>Límite:</b> ${escapeHTML(d.limite)}</p></article>`).join('');
const cor=DATA.summary.correlacion;
$('correlationMethod').textContent=`En la cohorte histórica fija de ${cor.cohorte.length} activos se analizan ${cor.n} cambios mensuales pareados (febrero de 2022 a julio de 2026). Pearson de cambios = ${fmt(cor.r,3)}; IC exploratorio por bloques de 3 meses, 2.000 réplicas y semilla 2026: [${fmt(cor.ic95[0],3)}, ${fmt(cor.ic95[1],3)}]. Sensibilidad con bloques de 6 meses en el informe. El intervalo depende del supuesto de estabilidad local y no demuestra ausencia de relación ni sirve como pronóstico.`;
render();
if(document.modelContext?.registerTool){
 const lifecycle=new AbortController();
 const registration=document.modelContext.registerTool({name:'configurar_filtros_eda',title:'Configurar filtros del dashboard',description:'Actualiza el período, el activo y la medida de la vista visible. No cambia los archivos fuente.',inputSchema:{type:'object',properties:{desde:{type:'string',enum:allMonths},hasta:{type:'string',enum:allMonths},activo:{type:'string',enum:['all',...Object.keys(names)]},medida:{type:'string',enum:['crudo','gas']}},required:['desde','hasta','activo','medida'],additionalProperties:false},annotations:{readOnlyHint:false,untrustedContentHint:false},execute(input){if(!input||!allMonths.includes(input.desde)||!allMonths.includes(input.hasta)||input.desde>input.hasta||!['all',...Object.keys(names)].includes(input.activo)||!['crudo','gas'].includes(input.medida))throw new Error('Filtros inválidos');$('start').value=input.desde;$('end').value=input.hasta;$('asset').value=input.activo;$('metric').value=input.medida;$('balanced').checked=false;render();return{registros:selectedRows.length,desde:input.desde,hasta:input.hasta,activo:input.activo,medida:input.medida}}},{signal:lifecycle.signal});
 Promise.resolve(registration).catch(()=>{});window.addEventListener('pagehide',()=>lifecycle.abort(),{once:true});
}
