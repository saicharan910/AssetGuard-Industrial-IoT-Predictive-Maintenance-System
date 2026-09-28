import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import './App.css';

const ASSET_DESCRIPTIONS = {
  "MTR-001": "Primary mechanical drive motor unit",
  "PUMP-101": "Fluid transfer coolant pump system",
  "FAN-042": "Exhaust airflow cooling blower unit"
};

function App() {
  const [history, setHistory] = useState([]);
  const [current, setCurrent] = useState(null);
  const [selectedAsset, setSelectedAsset] = useState("MTR-001");
  const [hoveredAsset, setHoveredAsset] = useState(null);
  const [reportStatus, setReportStatus] = useState("");
  const wsRef = useRef(null);

  const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
  const WS_BASE_URL = API_BASE_URL.replace(/^http/, 'ws');

  useEffect(() => {
    // 1. Load initial history for chosen asset
    axios.get(`${API_BASE_URL}/api/history/${selectedAsset}`)
      .then(({ data }) => {
        const chartData = data.map(row => ({
          ...row,
          time: new Date(row.timestamp).toLocaleTimeString(),
        }));
        setHistory(chartData);
      })
      .catch(err => console.error("Initial load error:", err));

    // 2. Open persistent WebSocket stream
    if (wsRef.current) {
      wsRef.current.close();
    }

    const socket = new WebSocket(`${WS_BASE_URL}/ws/telemetry/${selectedAsset}`);
    wsRef.current = socket;

    socket.onmessage = (event) => {
      const liveData = JSON.parse(event.data);
      setCurrent(liveData);
      setHistory(prev => {
        const updated = [...prev, {
          ...liveData,
          time: new Date(liveData.timestamp).toLocaleTimeString()
        }];
        return updated.slice(-30);
      });
    };

    return () => {
      socket.close();
    };
  }, [selectedAsset, API_BASE_URL, WS_BASE_URL]);

  // 3. Direct Browser CSV Download
  const handleGenerateReport = async () => {
    try {
      setReportStatus("Downloading CSV...");
      const response = await axios.get(`${API_BASE_URL}/api/report`, {
        responseType: 'blob',
      });

      const blob = new Blob([response.data], { type: 'text/csv' });
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.setAttribute('download', 'assetguard_ml_report.csv');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);

      setReportStatus("Report downloaded successfully.");
    } catch (err) {
      console.error("Export error:", err);
      setReportStatus("Export failed.");
    }
  };

  return (
    <div className="dashboard-container">
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1>AssetGuard IIoT Monitor</h1>

        {/* Dropdown Container with Hover Tooltip */}
        <div
          className="select-wrapper"
          onMouseEnter={() => setHoveredAsset(selectedAsset)}
          onMouseLeave={() => setHoveredAsset(null)}
        >
          <select
            value={selectedAsset}
            onChange={(e) => {
              setSelectedAsset(e.target.value);
              setHoveredAsset(e.target.value);
            }}
            className="btn-primary"
            style={{ padding: '0.5rem 1rem', fontSize: '0.95rem', cursor: 'pointer' }}
          >
            <option value="MTR-001">Motor (MTR-001)</option>
            <option value="PUMP-101">Pump (PUMP-101)</option>
            <option value="FAN-042">Fan (FAN-042)</option>
          </select>

          {hoveredAsset && (
            <div className="asset-tooltip">
              {ASSET_DESCRIPTIONS[hoveredAsset]}
            </div>
          )}
        </div>
      </header>

      <main className="dashboard-grid">
        {current && (
          <section className="card status-card">
            <h2>ID: {current.equipment_id}</h2>
            <div className="metrics">
              <p>Temp: {Number(current.temperature_celsius).toFixed(2)} °C</p>
              <p>Vib: {Number(current.vibration_mm_s).toFixed(2)} mm/s</p>
              <p className={`status ${current.health_status.includes('Warning') ? 'danger' : 'safe'}`}>
                {current.health_status}
              </p>
            </div>
          </section>
        )}

        <section className="card actions-card">
          <h2>ML Analytics Engine</h2>
          <button onClick={handleGenerateReport} className="btn-primary">
            Export Pandas CSV
          </button>
          {reportStatus && <p className="status-msg">{reportStatus}</p>}
        </section>
      </main>

      <section className="chart-section">
        <ResponsiveContainer width="100%" height={350}>
          <LineChart data={history}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
            <XAxis dataKey="time" />
            <YAxis yAxisId="left" domain={['dataMin - 5', 'dataMax + 5']} />
            <YAxis yAxisId="right" orientation="right" domain={[0, 7]} />
            <Tooltip />
            <Legend />
            <Line yAxisId="left" type="monotone" dataKey="temperature_celsius" stroke="#2563eb" name="Temp (°C)" dot={false} strokeWidth={2} isAnimationActive={false} />
            <Line yAxisId="right" type="monotone" dataKey="vibration_mm_s" stroke="#dc2626" name="Vibration" dot={false} strokeWidth={2} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </section>
    </div>
  );
}

export default App;