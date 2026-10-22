import React, {useEffect, useRef, useState} from 'react';
import {createRoot} from 'react-dom/client';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import './style.css';

type Status = 'NEW'|'VERIFIED'|'ASSIGNED'|'RESOLVED';
type Incident = {message_id:string; incident_id:string; version:number; effective_priority:number; status:Status; assigned_team:string|null; received_at_ms:number;
  body:{text:string;priority:number;latitude:number|null;longitude:number|null;accuracy_m:number|null;location_captured_at_ms:number|null;location_text:string;created_at_ms:number;expires_at_ms:number;people_count:number;needs:string[]};
  ai:{model_version:string;suggested_priority:number;reasons:string[];confidence?:number|null;low_confidence?:boolean}};
const statuses:Record<Status,string>={NEW:'Chờ xác minh',VERIFIED:'Đã xác minh',ASSIGNED:'Đã phân công',RESOLVED:'Đã hoàn tất'};
const needNames:Record<string,string>={medical:'Y tế',evacuation:'Sơ tán',food:'Thực phẩm',water:'Nước uống',other:'Khác'};
const date=(ms:number)=>new Date(ms).toLocaleString('vi-VN');

function MapPanel({items,onSelect}:{items:Incident[];onSelect:(id:string)=>void}){
  const container=useRef<HTMLDivElement>(null);
  const map=useRef<maplibregl.Map|null>(null);
  const markers=useRef<maplibregl.Marker[]>([]);
  const [heat,setHeat]=useState(false);
  const [tiles,setTiles]=useState(false);
  const [mapError,setMapError]=useState('');
  useEffect(()=>{
    if(!container.current)return;
    try {
      const m=new maplibregl.Map({container:container.current,center:[108.2,16.07],zoom:10,
        style:{version:8,sources:{},layers:[{id:'background',type:'background',paint:{'background-color':'#e2ebe7'}}]}});
      m.on('load',()=>{m.addSource('sos-heat',{type:'geojson',data:{type:'FeatureCollection',features:[]}});m.addLayer({id:'sos-heat',type:'heatmap',source:'sos-heat',layout:{visibility:'none'},paint:{'heatmap-weight':['get','weight'],'heatmap-radius':35,'heatmap-opacity':.65}});});
      m.addControl(new maplibregl.NavigationControl(),'top-right');
      m.on('error',()=>setMapError('Không tải được một phần bản đồ. Danh sách SOS vẫn hoạt động.'));
      map.current=m;
    }catch{setMapError('Thiết bị không hỗ trợ WebGL. Xem tọa độ trong chi tiết SOS.');}
    return ()=>{map.current?.remove();map.current=null;};
  },[]);
  useEffect(()=>{
    if(!map.current)return;
    markers.current.forEach(m=>m.remove());
    markers.current=[];
    items.filter(i=>i.body.latitude!==null&&i.body.longitude!==null).forEach(i=>{
      const el=document.createElement('button');
      el.className=`map-pin p${i.effective_priority}`;
      el.textContent=`P${i.effective_priority}`;el.title=i.body.location_text;
      el.onclick=()=>onSelect(i.message_id);
      markers.current.push(new maplibregl.Marker({element:el}).setLngLat([i.body.longitude!,i.body.latitude!]).addTo(map.current!));
    });
  },[items,onSelect]);
  useEffect(()=>{if(heat&&map.current?.getSource('sos-heat')){const source=map.current.getSource('sos-heat') as maplibregl.GeoJSONSource;source.setData({type:'FeatureCollection',features:items.filter(i=>i.status!=='RESOLVED'&&i.body.latitude!==null&&i.body.longitude!==null).map(i=>({type:'Feature',properties:{weight:4-i.effective_priority},geometry:{type:'Point',coordinates:[i.body.longitude!,i.body.latitude!]}}))});}},[items,heat]);
  function toggleHeat(){
    const m=map.current;if(!m?.getSource('sos-heat'))return;
    const source=m.getSource('sos-heat') as maplibregl.GeoJSONSource;
    source.setData({type:'FeatureCollection',features:items.filter(i=>i.status!=='RESOLVED'&&i.body.longitude!==null&&i.body.latitude!==null).map(i=>({type:'Feature',properties:{weight:4-i.effective_priority},geometry:{type:'Point',coordinates:[i.body.longitude!,i.body.latitude!]}}))});
    m.setLayoutProperty('sos-heat','visibility',heat?'none':'visible');setHeat(!heat);
  }
  function enableTiles(){
    const m=map.current;if(!m)return;
    if(!m.isStyleLoaded()){setMapError('Bản đồ đang khởi tạo, thử lại sau một giây.');return;}
    if(!m.getSource('osm')){
      m.addSource('osm',{type:'raster',tiles:['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],tileSize:256,attribution:'© OpenStreetMap contributors'});
      m.addLayer({id:'osm',type:'raster',source:'osm'},'sos-heat');
    }
    setTiles(true);
  }
  function fit(){
    const located=items.filter(i=>i.body.latitude!==null&&i.body.longitude!==null);
    if(!located.length||!map.current)return;
    const bounds=new maplibregl.LngLatBounds();
    located.forEach(i=>bounds.extend([i.body.longitude!,i.body.latitude!]));
    map.current.fitBounds(bounds,{padding:80,maxZoom:14});
  }
  return <section className="map-panel"><div ref={container} className="map"/><div className="map-tools">
    {!tiles&&<button onClick={enableTiles}>Bật nền OSM trực tuyến</button>}<button onClick={fit}>Xem tất cả điểm</button><button onClick={toggleHeat}>{heat?'Ẩn heatmap':'Xem heatmap'}</button>
  </div><div className="map-caption">{mapError||'Bản đồ tọa độ • Nền OSM tùy chọn cần Internet; nhà cung cấp tile nhận vùng bản đồ đang xem.'}</div></section>;
}

function App(){
  const [token,setToken]=useState(()=>sessionStorage.getItem('rescuelink_token')||'');
  const [inputToken,setInputToken]=useState('');
  const [items,setItems]=useState<Incident[]>([]);
  const [total,setTotal]=useState(0);
  const [offset,setOffset]=useState(0);
  const [selected,setSelected]=useState<string|null>(null);
  const [error,setError]=useState('');
  const [lastRefresh,setLastRefresh]=useState<number|null>(null);
  const [search,setSearch]=useState('');
  const [filter,setFilter]=useState('ALL');
  const [team,setTeam]=useState('');
  const [saving,setSaving]=useState(false);
  const [priority,setPriority]=useState(2);
  const [reason,setReason]=useState('');
  const [previewText,setPreviewText]=useState('');
  const [preview,setPreview]=useState<Incident['ai']|null>(null);
  const [stats,setStats]=useState<{total:number;statuses:Record<string,number>;open_priorities:Record<string,number>}|null>(null);
  const [timeline,setTimeline]=useState<{event:string;at_ms:number}[]>([]);
  async function api(path:string,init:RequestInit={}){
    const r=await fetch('/api'+path,{...init,headers:{'Authorization':`Bearer ${token}`,'Content-Type':'application/json',...init.headers}});
    if(!r.ok){let message=`HTTP ${r.status}`;try{const j=await r.json();message=typeof j.detail==='string'?j.detail:message;}catch{}throw new Error(message);}
    return r.json();
  }
  async function refresh(){
    try{const [j,st]=await Promise.all([api(`/v1/sos?limit=100&offset=${offset}`),api('/v1/stats')]);setStats(st);setItems(j.items);setTotal(j.total);setLastRefresh(Date.now());setError('');}
    catch(e){setError((e as Error).message);}
  }
  useEffect(()=>{if(!token)return;void refresh();const timer=setInterval(refresh,5000);return()=>clearInterval(timer);},[token,offset]);
  const current=items.find(i=>i.message_id===selected);
  useEffect(()=>{setTeam(current?.assigned_team||'');setPriority(current?.effective_priority||2);setReason('');setTimeline([]);if(selected&&token)void api(`/v1/sos/${selected}/events`).then(setTimeline).catch(()=>{});},[selected,current?.version,token]);
  const filtered=items.filter(i=>(filter==='ALL'||i.status===filter)&&`${i.body.text} ${i.body.location_text}`.toLowerCase().includes(search.toLowerCase()));
  async function advance(){
    if(!current)return;
    const next:Partial<Record<Status,Status>>={NEW:'VERIFIED',VERIFIED:'ASSIGNED',ASSIGNED:'RESOLVED'};
    setSaving(true);
    try{await api(`/v1/sos/${current.message_id}`,{method:'PATCH',body:JSON.stringify({version:current.version,status:next[current.status],assigned_team:team.trim()||null})});await refresh();}
    catch(e){setError((e as Error).message);}finally{setSaving(false);}
  }
  async function adjustPriority(){
    if(!current)return;setSaving(true);
    try{await api(`/v1/sos/${current.message_id}/priority`,{method:'PATCH',body:JSON.stringify({version:current.version,priority,reason})});await refresh();}catch(e){setError((e as Error).message);}finally{setSaving(false);}
  }
  async function exportCsv(){
    try{const response=await fetch('/api/v1/export.csv',{headers:{Authorization:`Bearer ${token}`}});if(!response.ok)throw new Error(`HTTP ${response.status}`);const url=URL.createObjectURL(await response.blob());const a=document.createElement('a');a.href=url;a.download='rescuelink-sos.csv';a.click();URL.revokeObjectURL(url);}catch(e){setError((e as Error).message);}
  }
  async function tryAI(){try{setPreview(await api('/v1/triage/preview',{method:'POST',body:JSON.stringify({text:previewText,priority:3,needs:[]})}));}catch(e){setError((e as Error).message);}}
  if(!token)return <main className="login"><div className="login-art"><span className="eyebrow">KẾT NỐI KHI CẦN NHAU NHẤT</span><h1>Một lời cầu cứu.<br/>Thêm một cơ hội<br/><em>được lắng nghe.</em></h1><p>RescueLink / P2P · Store-and-Forward</p><div className="orbit one"/><div className="orbit two"/></div><form onSubmit={e=>{e.preventDefault();sessionStorage.setItem('rescuelink_token',inputToken.trim());setToken(inputToken.trim());}} className="login-form"><div className="brand">✳ RescueLink</div><span className="drill">MÔI TRƯỜNG DIỄN TẬP</span><h2>Trung tâm điều phối</h2><p>Nhập ADMIN_TOKEN trong file .env trên máy chủ. Bản này chỉ dùng dữ liệu giả lập.</p><label>Mã truy cập<input type="password" value={inputToken} onChange={e=>setInputToken(e.target.value)} required minLength={24} autoComplete="off"/></label><button className="primary">Vào bảng điều phối →</button><small>v0.2 · Prototype nghiên cứu · Chưa dùng trong cứu hộ thực tế</small></form></main>;
  return <div className="app"><aside className="rail"><div className="symbol">✳</div><span>RL</span><div className="rail-line"/><span className="active-icon">⌖</span><span className="vertical-label">RESCUELINK / ĐIỀU PHỐI</span></aside><main className="workspace">
    <header><div><span className="eyebrow">TRUNG TÂM HỖ TRỢ THIÊN TAI</span><h1>Tổng quan cứu trợ</h1></div><div className="header-actions"><span className="drill">DIỄN TẬP</span><button onClick={()=>{sessionStorage.removeItem('rescuelink_token');setToken('');setItems([]);}}>Đăng xuất</button></div></header>
    <section className="metrics">{[['Tổng SOS',stats?.total||0],['Cần xác minh',stats?.statuses.NEW||0],['P1 đang mở',stats?.open_priorities['1']||0],['Đã phân công',stats?.statuses.ASSIGNED||0]].map(([label,value])=><div className="metric" key={label}><span>{label}</span><strong>{value}</strong></div>)}</section>
    <div className="sync-line"><span className={error?'dot bad':'dot'}/>{error?`Mất đồng bộ: ${error}`:lastRefresh?`Cập nhật ${date(lastRefresh)} · kiểm tra mỗi 5 giây`:'Đang kết nối…'}<b> Trang {Math.floor(offset/100)+1} · {items.length}/{total} SOS; tìm kiếm/lọc trong trang này.</b><button disabled={offset===0} onClick={()=>{setSelected(null);setOffset(Math.max(0,offset-100));}}>Trang trước</button><button disabled={offset+100>=total} onClick={()=>{setSelected(null);setOffset(offset+100);}}>Trang sau</button><button onClick={refresh}>Tải lại</button><button onClick={exportCsv}>Xuất CSV (tối đa 10.000)</button></div>
    <section className="operations"><section className="inbox"><div className="panel-heading"><h2>Yêu cầu hỗ trợ</h2><span>{filtered.length}</span></div><input placeholder="Tìm nội dung, địa điểm…" value={search} onChange={e=>setSearch(e.target.value)} aria-label="Tìm SOS"/><select value={filter} onChange={e=>setFilter(e.target.value)} aria-label="Lọc trạng thái"><option value="ALL">Tất cả trạng thái</option>{Object.entries(statuses).map(([k,v])=><option value={k} key={k}>{v}</option>)}</select><div className="cards">{filtered.map(i=><button key={i.message_id} className={`sos-card ${selected===i.message_id?'selected':''}`} onClick={()=>setSelected(i.message_id)}><div className="card-top"><span className={`badge p${i.effective_priority}`}>P{i.effective_priority}</span><span>{statuses[i.status]}</span></div><h3>{i.body.location_text}</h3><p>{i.body.text}</p><footer><span>{i.body.people_count} người</span><span>{new Date(i.received_at_ms).toLocaleTimeString('vi-VN')}</span></footer></button>)}{!filtered.length&&<div className="empty"><span>⌁</span><h3>Chưa có yêu cầu</h3><p>Tạo SOS trên app hoặc chạy script seed_demo.py để kiểm tra luồng dữ liệu.</p></div>}</div></section>
    <MapPanel items={filtered} onSelect={setSelected}/>
    <section className="detail">{!current?<div className="empty"><span>↖</span><h3>Chọn một SOS</h3><p>Xem thông tin, xác minh và phân công đội hỗ trợ.</p></div>:<><div className="panel-heading"><h2>Chi tiết yêu cầu</h2><span className={`badge p${current.effective_priority}`}>P{current.effective_priority}</span></div><span className="state">{statuses[current.status]}</span><h3>{current.body.location_text}</h3><p className="message">{current.body.text}</p><div className="tags">{current.body.needs.map(n=><span key={n}>{needNames[n]||n}</span>)}</div><dl><dt>Số người</dt><dd>{current.body.people_count}</dd><dt>Tạo trên điện thoại</dt><dd>{date(current.body.created_at_ms)}</dd><dt>Trung tâm tiếp nhận</dt><dd>{date(current.received_at_ms)}</dd><dt>Tọa độ</dt><dd>{current.body.latitude===null?'Chưa có GPS':`${current.body.latitude}, ${current.body.longitude}`}</dd><dt>Sai số vị trí</dt><dd>{current.body.accuracy_m===null?'Chưa xác định':`${current.body.accuracy_m} m`}</dd>{current.body.location_captured_at_ms&&<><dt>Vị trí ghi nhận lúc</dt><dd>{date(current.body.location_captured_at_ms)}</dd></>}</dl><div className="ai-note"><b>Gợi ý AI/baseline: P{current.ai.suggested_priority}</b><p>{current.ai.reasons.join(' ')}</p><small>{current.ai.model_version} · Điểm mô hình: {current.ai.confidence==null?'không có':current.ai.confidence.toFixed(3)} · Cần người xác minh.</small></div>{current.status!=='RESOLVED'&&<div className="priority-editor"><label>Mức điều phối (nguồn gửi: P{current.body.priority})<select value={priority} onChange={e=>setPriority(Number(e.target.value))}><option value={1}>P1 — Khẩn cấp</option><option value={2}>P2 — Hỗ trợ sớm</option><option value={3}>P3 — Thông tin</option></select></label><input placeholder="Lý do điều chỉnh (bắt buộc)" value={reason} onChange={e=>setReason(e.target.value)} maxLength={250}/><button disabled={saving||reason.trim().length<3} onClick={adjustPriority}>Lưu mức điều phối</button></div>}{current.status==='VERIFIED'&&<label>Đội nhận nhiệm vụ<input value={team} onChange={e=>setTeam(e.target.value)} placeholder="Ví dụ: Đội diễn tập 01" maxLength={100}/></label>}{current.assigned_team&&<p>Đội: <b>{current.assigned_team}</b></p>}{current.status!=='RESOLVED'&&<button className="primary" onClick={advance} disabled={saving||(current.status==='VERIFIED'&&!team.trim())}>{saving?'Đang lưu…':current.status==='NEW'?'Xác nhận đã kiểm tra':current.status==='VERIFIED'?'Phân công đội':'Xác nhận đã hoàn tất'}</button>}<h4>Lịch sử xử lý</h4><ul className="timeline">{timeline.map((e,idx)=><li key={idx}>{statuses[e.event as Status]||(e.event==='PRIORITY_CHANGED'?'Điều chỉnh mức điều phối':'Trung tâm nhận SOS')}<small>{date(e.at_ms)}</small></li>)}</ul><small className="technical-id">ID: {current.message_id.slice(0,16)}…</small></>}</section></section>
    <section className="research-panel"><h2>Thử phân loại nội dung</h2><p>Mô hình học từ dữ liệu tổng hợp. Gợi ý ở đây không tạo SOS và không thay đổi mức điều phối.</p><textarea value={previewText} onChange={e=>{setPreviewText(e.target.value);setPreview(null);}} maxLength={1000} placeholder="Nhập nội dung diễn tập…"/><button onClick={tryAI} disabled={previewText.trim().length<3}>Phân loại thử</button>{preview&&<p>P{preview.suggested_priority} · {preview.model_version} · Điểm: {preview.confidence?.toFixed(3)||'không có'} · {preview.reasons.join(' ')}</p>}</section><footer className="page-footer">Dữ liệu diễn tập · Vị trí có thể đã cũ · Giao nhận tin không đồng nghĩa cứu hộ đã đến.</footer>
  </main></div>;
}
createRoot(document.getElementById('root')!).render(<App/>);
