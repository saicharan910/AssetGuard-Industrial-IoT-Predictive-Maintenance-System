import { useState, useEffect } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import './App.css';

function App() {
  const [history, setHistory] = useState([]);
  const [current, setCurrent] = useState(null);
  const [reportStatus, setReportStatus] = useState("");

  const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

  const fetchTelemetry = async () => {
    try {
      const { data: liveData } = await axios.get(`${API_BASE_URL}/api/telemetry`);
      setCurrent(liveData);

      const { data: historyData } = await axios.get(`${API_BASE_URL}/api/history`);
      const chartData = historyData.map(row => ({
        ...row,
        time: new Date(row.timestamp).toLocaleTimeString(),
      }));
      setHistory(chartData);
    } catch (err) {
      console.error("Dashboard error:", err);
    }
  };


  const handleGenerateReport = async () => {
    try {
      setReportStatus("Generating report...");
      const response = await axios.get(`${API_BASE_URL}/api/report`, {
        responseType: 'blob',
      });

      // Create a temporary downloadable link for the blob
      const blob = new Blob([response.data], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'assetguard_equipment_report.csv');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      setReportStatus("Report downloaded successfully.");
    } catch (err) {
      console.error("Report download error:", err);
      setReportStatus("Report generation failed.");
    }
  };

  useEffect(() => {
    fetchTelemetry();
    const intervalId = setInterval(fetchTelemetry, 2000);
    return () => clearInterval(intervalId);
  }, []);

  return (
    <div className="dashboard-container">
      <header>
        <h1>AssetGuard IIoT Monitor</h1>
      </header>

      <main className="dashboard-grid">
        {current && (
          <section className="card status-card">
            <h2>ID: {current.equipment_id}</h2>
            <div className="metrics">
              <p>Temp: {current.temperature_celsius} °C</p>
              <p>Vib: {current.vibration_mm_s} mm/s</p>
              <p className={`status ${current.health_status.includes('Warning') ? 'danger' : 'safe'}`}>
                {current.health_status}
              </p>
            </div>
          </section>
        )}

        <section className="card actions-card">
          <h2>Analytics Engine</h2>
          <button onClick={handleGenerateReport} className="btn-primary">
            Export Pandas CSV
          </button>
          {reportStatus && <p className="status-msg">{reportStatus}</p>}
        </section>
      </main>

      <section className="chart-section">
        <ResponsiveContainer height={350} width="100%">
          <LineChart data={history}>
            <CartesianGrid opacity={0.3} strokeDasharray="3 3" />
            <XAxis dataKey="time" />
            <YAxis yAxisId="left" domain={['dataMin - 5', 'dataMax + 5']} />
            <YAxis yAxisId="right" orientation="right" domain={[0, 7]} />
            <Tooltip />
            <Legend />
            <Line yAxisId="left" type="monotone" dataKey="temperature_celsius" stroke="#2563eb" name="Temp (°C)" dot={false} strokeWidth={2} />
            <Line yAxisId="right" type="monotone" dataKey="vibration_mm_s" stroke="#dc2626" name="Vibration" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </section>
    </div>
  );
}

export default App;