import React, {useEffect, useRef, useState} from 'react';
import {Activity, Ambulance, BarChart3, Camera, CarFront, CircleAlert, Clock3, FileImage, Gauge, LayoutDashboard, MapPin, Play, Radio, ShieldCheck, Siren, Upload, Video, Wifi, Zap} from 'lucide-react';

const API = 'http://127.0.0.1:8000';
const demo = {vehicle_count:24, counts:{car:13,motorcycle:7,bus:2,truck:2},density:'High',detections:[]};
function Stat({icon:Icon,label,value,sub}) {return <div className="stat"><div className="stat-top"><span>{label}</span><Icon size={18}/></div><strong>{value}</strong><small>{sub}</small></div>}
export default function App(){
 const [page,setPage]=useState('Overview'),[result,setResult]=useState(null),[busy,setBusy]=useState(false),[message,setMessage]=useState('Ready to analyze footage.'),[source,setSource]=useState('upload'),[emergency,setEmergency]=useState(false),[vehicle,setVehicle]=useState('Ambulance'),[origin,setOrigin]=useState('North'),[destination,setDestination]=useState('Hospital – South'),[live,setLive]=useState(false);
 const videoRef=useRef(null),streamRef=useRef(null),fileRef=useRef(null);
 const [traffic, setTraffic] = useState({
  north: 30,
  south: 20,
  east: 8,
  west: 5
});
const [signalResult, setSignalResult] = useState(null);
const [signalBusy, setSignalBusy] = useState(false);
const [signalError, setSignalError] = useState('');
const [emergencyResult, setEmergencyResult] = useState(null);
 useEffect(()=>()=>stopCamera(),[]);
 function stopCamera(){if(streamRef.current){streamRef.current.getTracks().forEach(t=>t.stop());streamRef.current=null;}setLive(false);}
 async function startCamera(){try{const s=await navigator.mediaDevices.getUserMedia({video:true,audio:false});streamRef.current=s;videoRef.current.srcObject=s;await videoRef.current.play();setLive(true);setMessage('Live camera connected.');}catch(e){setMessage('Camera unavailable: '+e.message);}}
 async function sendFrame(){if(!videoRef.current || !live)return;const c=document.createElement('canvas');c.width=videoRef.current.videoWidth;c.height=videoRef.current.videoHeight;c.getContext('2d').drawImage(videoRef.current,0,0);const blob=await new Promise(r=>c.toBlob(r,'image/jpeg',.85));const f=new FormData();f.append('file',blob,'webcam.jpg');await analyze('/api/analyze-frame',f);}

function activateEmergency() {
  if (origin === destination.replace('Hospital – ', '')) {
    setEmergencyResult({
      error: 'Starting direction and destination cannot be the same.'
    });
    return;
  }

  const route = {
    North: ['North', 'South', 'East', 'West'],
    South: ['South', 'North', 'West', 'East'],
    East: ['East', 'West', 'North', 'South'],
    West: ['West', 'East', 'South', 'North']
  };

  const destinationDirection = destination.replace('Hospital – ', '');
  const startIndex = route[origin].indexOf(destinationDirection);

  const orderedRoute = route[origin].slice(0, startIndex + 1);

  const vehicleCount = Object.values(traffic)
    .reduce((sum, value) => sum + Number(value), 0);

  setEmergencyResult({
    vehicle,
    origin,
    destination: destinationDirection,
    route: orderedRoute,
    vehiclesBeforePriority: vehicleCount,
    priorityStatus: 'ACTIVE',
    message: 'Emergency priority route generated successfully.'
  });

  setEmergency(true);
}
 async function calculateSignals() {
  setSignalBusy(true);
  setSignalError('');

  try {
    const response = await fetch(API + '/api/adaptive-signal', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        north: Number(traffic.north),
        south: Number(traffic.south),
        east: Number(traffic.east),
        west: Number(traffic.west)
      })
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Signal calculation failed');

    setSignalResult(data);
  } catch (error) {
    setSignalError(error.message);
  } finally {
    setSignalBusy(false);
  }
}
 
async function analyze(endpoint, form) {
  setBusy(true);
  setMessage('Analyzing footage with computer vision…');

  try {
    const r = await fetch(API + endpoint, {
      method: 'POST',
      body: form
    });

    const d = await r.json();

    if (!r.ok) {
      throw new Error(d.detail || 'Analysis failed');
    }

    setResult(d);
    setMessage('Analysis completed successfully.');

    return d;

  } catch (e) {
    setMessage(e.message + ' — start the backend and ensure the YOLO model is available.');
    throw e;

  } finally {
    setBusy(false);
  }
} 


async function handleFile(file) {
  if (!file) return;

  // Clear previous analysis and signal results
  setResult(null);
  setSignalResult(null);
  setSignalError('');
  setTraffic({
    north: 0,
    south: 0,
    east: 0,
    west: 0
  });

  const form = new FormData();
  form.append('file', file);

  const isVideo = file.type.startsWith('video/');

  try {
    const data = await analyze(
      isVideo ? '/api/analyze-video' : '/api/analyze-image',
      form
    );

    // Automatic signal calculation for images
    if (!isVideo) {
      if (!data.direction_counts) {
        throw new Error('Directional vehicle counts are missing.');
      }

      const directions = {
        north: Number(data.direction_counts.north),
        south: Number(data.direction_counts.south),
        east: Number(data.direction_counts.east),
        west: Number(data.direction_counts.west)
      };

      setTraffic(directions);
      setSignalBusy(true);

      const response = await fetch(
        API + '/api/adaptive-signal',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(directions)
        }
      );

      const signalData = await response.json();

      if (!response.ok) {
        throw new Error(
          signalData.detail || 'Signal calculation failed'
        );
      }

      setSignalResult(signalData);
      setMessage('Latest image analyzed and signal timings updated!');
    }

  } catch (error) {
    setSignalError(error.message);
    setMessage(error.message);

  } finally {
    setSignalBusy(false);
  }
}
 async function upload(e){handleFile(e.target.files?.[0]);e.target.value='';}
 const count=result?.vehicle_count ?? result?.average_vehicles_per_frame ?? demo.vehicle_count;
 const counts=result?.counts ?? demo.counts;
 const density=result?.density ?? demo.density;
 const isVideoResult=Boolean(result?.sampled_frames);
 return <div className="app">
  <aside className="sidebar"><div className="brand"><div className="brand-icon"><Activity/></div><div><b>SmartTraffic <em>AI</em></b><small>URBAN MOBILITY INTELLIGENCE</small></div></div>
   <div className="nav-label">WORKSPACE</div>{[['Overview',LayoutDashboard],['Traffic Monitoring',Video],['AI Detection',Gauge],['Signal Management',Activity],['Emergency Corridor',Ambulance],['Analytics',BarChart3]].map(([n,I])=><button key={n} className={'nav '+(page===n?'active':'')} onClick={()=>setPage(n)}><I size={18}/>{n}</button>)}
   <div className="sidebar-bottom"><div className="system"><span className="pulse"/> SYSTEM STATUS <b>LOCAL DEMO</b></div><small>Smart city traffic intelligence<br/>Prototype v0.1</small></div>
  </aside>
  <main className="main">
   <header className="topbar"><div><div className="eyebrow">SMART CITY / TRAFFIC OPERATIONS</div><h1>{page}</h1></div><div className="top-right"><span className="live-pill"><i/> Prototype workspace</span><div className="avatar">ST</div></div></header>
   {page==='Overview' && <>
    <section className="welcome"><div><div className="eyebrow light">INTELLIGENT TRANSPORTATION SYSTEM</div><h2>See traffic. Understand congestion.<br/><span>Coordinate smarter movement.</span></h2><p>Analyze road footage and generate adaptive traffic recommendations with AI.</p><button className="primary" onClick={()=>setPage('Traffic Monitoring')}><Play size={16}/> Start traffic analysis</button></div><div className="welcome-art"><div className="radar"><div className="radar-core"><Activity size={32}/></div><span className="radar-dot d1"/><span className="radar-dot d2"/><span className="radar-dot d3"/></div></div></section>
    <div className="section-heading"><div><h3>Traffic overview</h3><p>Latest analysis or sample dashboard values</p></div><span className="muted-tag">DEMO DATA UNTIL ANALYZED</span></div>
    <section className="stats"><Stat icon={CarFront} label="Vehicles detected" value={count} sub="Current analyzed sample"/><Stat icon={CircleAlert} label="Traffic density" value={density} sub="Based on detected vehicles"/><Stat icon={Camera} label="Input sources" value={live?'1 live':'Upload / webcam'} sub="Camera connection status"/><Stat icon={Clock3} label="Emergency status" value={emergency?'Priority active':'Standby'} sub="Operator-controlled demo"/> </section>
    <section className="grid-two"><div className="panel"><div className="panel-head"><div><h3>Start monitoring</h3><p>Choose how to provide traffic footage</p></div><Video/></div><div className="mode-cards"><button onClick={()=>{setPage('Traffic Monitoring');setSource('upload')}}><FileImage/><b>Upload media</b><small>Analyze image or video</small></button><button onClick={()=>{setPage('Traffic Monitoring');setSource('live')}}><Radio/><b>Live camera</b><small>Use webcam stream</small></button></div></div>
    <div className="panel"><div className="panel-head"><div><h3>Emergency corridor</h3><p>Priority coordination workflow</p></div><Ambulance/></div><div className="emergency-mini"><div className="emergency-icon"><Siren/></div><div><b>{emergency?'Emergency priority activated':'No active emergency'}</b><small>Activate a route-priority demonstration</small></div><button className="outline" onClick={()=>setPage('Emergency Corridor')}>Open</button></div></div></section>
   </>}
   {page==='Traffic Monitoring' && <section className="panel monitor"><div className="panel-head"><div><h3>Traffic footage input</h3><p>Upload a road image/video or connect a webcam</p></div><Wifi/></div><div className="tabs"><button className={source==='upload'?'selected':''} onClick={()=>setSource('upload')}> <Upload size={16}/> Upload media</button><button className={source==='live'?'selected':''} onClick={()=>setSource('live')}><Camera size={16}/> Live webcam</button></div>
    {source==='upload'?<div className="dropzone" onClick={()=>fileRef.current?.click()}><input ref={fileRef} type="file" accept="image/*,video/mp4,video/avi,video/quicktime" onChange={upload} hidden/><div className="upload-icon"><Upload/></div><b>Choose traffic image or video</b><p>Click to browse · JPG, PNG, MP4, AVI</p><small>Images up to 15 MB · Videos up to 100 MB</small></div>:<div className="camera-box"><video ref={videoRef} muted playsInline/><div className="camera-actions"><button className="primary" onClick={startCamera} disabled={live}><Camera size={16}/> Connect webcam</button><button className="outline" onClick={stopCamera} disabled={!live}>Stop camera</button><button className="outline" onClick={sendFrame} disabled={!live||busy}><Zap size={16}/> Analyze frame</button></div></div>}
    <div className="status-line"><span className={busy?'spinner':''}/>{message}</div>
    {result&&<div className="result-box"><div className="panel-head"><div><h3>AI analysis result</h3><p>{isVideoResult?`Sampled ${result.sampled_frames} frames from ${result.duration_seconds}s video`:'Image/frame analysis'}</p></div><span className="density-tag">{density} density</span></div><div className="result-stats"><div><small>Vehicle count / average</small><b>{count}</b></div>{Object.entries(counts||{}).map(([k,v])=><div key={k}><small>{k}</small><b>{v}</b></div>)}</div></div>}
   </section>}
   {page==='AI Detection'&&<section className="panel"><h3>AI detection module</h3><p className="muted">The backend uses YOLO to detect common road vehicles in uploaded images, sampled video frames and webcam snapshots.</p><div className="detection-grid">{Object.entries(counts||demo.counts).map(([k,v])=><div className="detect-card" key={k}><CarFront/><small>{k}</small><b>{v}</b></div>)}</div><div className="notice"><ShieldCheck/> <span><b>Detection limitation:</b> The standard model detects cars, motorcycles, buses and trucks. Ambulance/fire-engine recognition needs a dedicated trained model or operator confirmation.</span></div><button className="primary" onClick={()=>setPage('Traffic Monitoring')}>Analyze footage</button></section>}
   {page==='Signal Management' && <section className="panel">
  <div className="panel-head">
    <div>
      <h3>Adaptive Traffic Signal Management</h3>
      <p>Enter vehicle counts for each road direction</p>
    </div>
    <Activity/>
  </div>

  <div className="form-grid">
    {['north','south','east','west'].map(direction => (
      <label key={direction}>
        {direction.toUpperCase()} vehicles
        <input
          type="number"
          min="0"
          max="200"
          value={traffic[direction]}
          onChange={e => setTraffic({
            ...traffic,
            [direction]: e.target.value
          })}
        />
      </label>
    ))}
  </div>

  <button className="primary" onClick={calculateSignals} disabled={signalBusy}>
    <Activity size={17}/>
    {signalBusy ? 'Calculating...' : 'Calculate Adaptive Signals'}
  </button>

  {signalError && <div className="notice">{signalError}</div>}

  {signalResult && (
    <div className="result-box">
      <h3>Signal Calculation Results</h3>
      <div className="result-stats">
        <div><small>Total vehicles</small><b>{signalResult.demand.total}</b></div>
        <div><small>Congestion</small><b>{signalResult.congestion_level}</b></div>
        <div><small>North–South green</small><b>{signalResult.signal_recommendations.north_south.green_seconds}s</b></div>
        <div><small>East–West green</small><b>{signalResult.signal_recommendations.east_west.green_seconds}s</b></div>
      </div>
      <div className="notice">
        <b>AI Decision explanation:</b>
        <p>{signalResult.explanation}</p>
      </div>
      <p>Total green time: {signalResult.cycle_green_seconds} seconds</p>
      <small>Yellow time: {signalResult.yellow_seconds} seconds per transition.</small>
    </div>
  )}

  <div className="notice">
    These are simulated traffic signal recommendations.
    They do not control real traffic lights.
  </div>
</section>}
  
{page === 'Emergency Corridor' && (
  <section className="panel">
    <div className="panel-head">
      <div>
        <h3>Emergency Green Corridor</h3>
        <p>Configure an emergency vehicle priority scenario</p>
      </div>
      <Ambulance />
    </div>

    <div className="form-grid">
      <label>
        Vehicle type
        <select value={vehicle} onChange={e => setVehicle(e.target.value)}>
          <option>Ambulance</option>
          <option>Fire engine</option>
        </select>
      </label>

      <label>
        Starting direction
        <select value={origin} onChange={e => setOrigin(e.target.value)}>
          {['North', 'South', 'East', 'West'].map(x => (
            <option key={x}>{x}</option>
          ))}
        </select>
      </label>

      <label>
        Destination
        <select value={destination} onChange={e => setDestination(e.target.value)}>
          {[
            'Hospital – North',
            'Hospital – South',
            'Hospital – East',
            'Hospital – West'
          ].map(x => (
            <option key={x}>{x}</option>
          ))}
        </select>
      </label>
    </div>

    <button className="danger" onClick={activateEmergency}>
      <Siren size={17} />
      Activate emergency scenario
    </button>

    <button
      className="outline"
      onClick={() => {
        setEmergency(false);
        setEmergencyResult(null);
      }}
    >
      Deactivate emergency priority
    </button>

    {emergencyResult && (
      <div className="emergency-result">
        {emergencyResult.error ? (
          <p>{emergencyResult.error}</p>
        ) : (
          <>
            <b>Priority scenario active</b>
            <p>Vehicle: {emergencyResult.vehicle}</p>
            <p>Origin: {emergencyResult.origin}</p>
            <p>Destination: {emergencyResult.destination}</p>
            <p>
              Vehicles in latest analysis:
              {' '}{emergencyResult.vehiclesBeforePriority}
            </p>
            <p>Proposed priority route:</p>
            <b>{emergencyResult.route.join(' → ')}</b>
            <p>{emergencyResult.message}</p>
          </>
        )}
      </div>
    )}

    <div className="notice">
      This is a simulated emergency-priority workflow.
      It does not control real traffic signals or guarantee
      an emergency vehicle's passage.
    </div>
  </section>
)}
   {page==='Analytics'&&<section className="panel"><div className="panel-head"><div><h3>Traffic analytics</h3><p>Vehicle class counts from the latest analysis</p></div><BarChart3/></div><div className="bars">{Object.entries(counts||demo.counts).map(([k,v])=><div className="bar-row" key={k}><span>{k}</span><div><i style={{width:Math.min(100,(v/Math.max(1,...Object.values(counts||demo.counts)))*100)+'%'}}/></div><b>{v}</b></div>)}</div><div className="notice">Run an image, video or webcam analysis to replace the sample values with detected counts.</div></section>}
   <footer>SMARTTRAFFIC AI · HACKATHON SOFTWARE PROTOTYPE <span>Not connected to real traffic infrastructure</span></footer>
  </main>
 </div>
}
