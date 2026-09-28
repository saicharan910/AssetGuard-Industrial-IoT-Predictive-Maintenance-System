# AssetGuard: Industrial IoT Predictive Maintenance System

A full-stack, real-time industrial condition monitoring and predictive maintenance platform. AssetGuard streams multivariate sensor telemetry across persistent WebSockets, evaluates equipment health using an unsupervised machine learning model, provides interactive multi-asset diagnostics, and exports compliance audit reports.

---

## Live Deployments
* **Interactive Frontend Dashboard:** [AssetGuard Monitor on Vercel](https://asset-guard-industrial-io-t-predict.vercel.app/)
* **Backend API & ML Engine:** [AssetGuard Service on Render](https://assetguard-industrial-iot-predictive-9j6a.onrender.com/)
* **API Documentation:** [Swagger UI Endpoint](https://assetguard-industrial-iot-predictive-9j6a.onrender.com/docs)

---

## Core Capabilities
* **Sub-Second WebSocket Streaming:** Pushes real-time temperature (°C) and vibration velocity (mm/s) readings to the client interface using bidirectional WebSockets (`/ws/telemetry/{equipment_id}`).
* **Unsupervised Anomaly Detection:** Employs an in-memory Scikit-Learn **Isolation Forest** model to detect multivariate operational anomalies against equipment baselines rather than relying solely on rigid, hardcoded limits.
* **Multi-Asset Fleet Switching:** Provides isolated monitoring profiles and historical trends across rotating machinery classes:
  * **Electric Motor (`MTR-001`):** Primary mechanical drive baseline (~75 °C, ~2.0 mm/s).
  * **Coolant Pump (`PUMP-101`):** Fluid transfer unit baseline (~60 °C, ~1.5 mm/s).
  * **Exhaust Fan (`FAN-042`):** Airflow blower baseline (~45 °C, ~1.0 mm/s).
* **Interactive Time-Series Visualization:** Renders dual-axis synchronized trends via Recharts to decouple thermal dissipation from mechanical vibration.
* **In-Memory Pandas Audit Export:** Generates and directly streams downloadable CSV audit reports (`assetguard_ml_report.csv`) from relational database records for ISO/safety compliance.

---

## Architecture & Tech Stack

```text
   [ React + Vite Client ]
             │  ▲
  REST / WS  │  │  Telemetry & Alerts
             ▼  │
     [ FastAPI Engine ]
      ├── Scikit-Learn (Isolation Forest Outlier Classifier)
      ├── SQLAlchemy ORM (SQLite / PostgreSQL Support)
      └── Pandas Data Analytics (CSV Generation & In-Memory Streaming)
