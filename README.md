# 🔭 Project FORESIGHT - AI-Powered Demand & Inventory Intelligence

Project FORESIGHT is an enterprise-grade AI application built with Streamlit that predicts SKU-level demand from historical sales data, quantifies stockout and overstock risk exposure, and generates actionable inventory recommendations for supply chain planners.

---

## 🏛️ System Architecture & Workflow

```text
Raw Sales CSV/XLSX ➔ Data Cleaning & Pipeline ➔ Feature Engineering (Lags, Rolling Means)
  ➔ Champion ML Model Selection (Random Forest vs Seasonal Naive) ➔ 30-Day SKU Demand Forecast
  ➔ Risk Scoring Engine (Safety Stock & Reorder Points) ➔ Role-Based Dashboard & Action Telemetry
```

---

## 📁 Repository Structure

```text
├── app.py                     # Main application entrypoint (Auth, Navigation, Session State)
├── auth/                      # Authentication & RBAC System
│   ├── authentication.py      # Password verification & SHA-256 hashing
│   ├── session.py             # Session state initialization & top header
│   ├── styles.py              # Enterprise dark glassmorphism styling
│   ├── users.py               # Persistent user registry
│   └── users.json             # Encrypted user accounts store
├── pages/                     # Enterprise Multipage Views
│   ├── Dashboard.py           # Executive KPIs & Quick Actions
│   ├── Forecast.py            # Machine Learning predictions & WAPE backtesting
│   ├── Risk_Analysis.py       # Stockout / Overstock risk matrices & Rupee impact
│   ├── Inventory_Health.py    # SKU health status & turn velocity
│   ├── SKU_Explorer.py        # Individual SKU deep dives
│   ├── Reports.py             # Exportable purchase orders & executive briefs
│   └── Settings.py            # ERP policy parameters & immutable audit logs
├── src/                       # Machine Learning & Analytics Core
│   ├── forecast.py            # Random Forest ML model, WAPE & Bias metrics
│   ├── pipeline.py            # Sales data ingestion & time-series feature pipeline
│   └── risk.py                # Reorder point math, stockout & overstock scoring
├── data/                      # Raw & processed telemetry
├── tests/                     # Unit test suite
├── .streamlit/                # Streamlit configuration & secrets
├── requirements.txt           # Python dependencies
└── README.md                  # Documentation
```

---

## 🔐 Role-Based Access Control (RBAC)

Project FORESIGHT enforces strict role-based view separation:

| Role | Theme | Accessible Pages | Purpose | Default Credentials |
|---|---|---|---|---|
| **Administrator** | 🟣 Violet | All 7 Pages (`Dashboard`, `Forecast`, `Risk Analysis`, `Inventory Health`, `SKU Explorer`, `Reports`, `Settings`) | System configuration, model retraining, user management, audit logs | `admin@foresight.ai` / `admin123` |
| **Inventory Planner** | 🔵 Blue | 6 Pages (`Dashboard`, `Forecast`, `Risk Analysis`, `Inventory Health`, `SKU Explorer`, `Reports`) | Operational forecasting, purchase order approvals | `planner@foresight.ai` / `planner123` |
| **Viewer** | 🟢 Green | 3 Pages (`Dashboard`, `Forecast`, `Reports`) | Read-only executive summaries & reports | `viewer@foresight.ai` / `viewer123` |

---

## 🚀 Quickstart - Running Locally

### 1. Clone & Setup Virtual Environment
```bash
git clone https://github.com/your-username/Project_FORESIGHT.git
cd Project_FORESIGHT
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Launch Streamlit Application
```bash
streamlit run app.py
```

---

## 🌐 Deploying to Streamlit Community Cloud

### Step 1: Push Repository to GitHub
Ensure all code, `.gitignore`, and `requirements.txt` are committed to your GitHub repository.

### Step 2: Deploy on Streamlit Cloud
1. Sign in to [share.streamlit.io](https://share.streamlit.io/).
2. Click **New app**.
3. Select your GitHub repository, branch (`main`), and set **Main file path** to `app.py`.
4. Click **Deploy**.

---

## 📊 Dataset Ingestion Schema

To upload custom sales exports in the **Admin Quick Actions**, prepare a CSV or XLSX file containing:

| Column | Data Type | Required | Description |
|---|---|---|---|
| `date` | YYYY-MM-DD | Yes | Daily sales transaction timestamp |
| `sku` / `sku_id` | String | Yes | Unique Stock Keeping Unit Identifier |
| `product` | String | Yes | Product name |
| `quantity_sold` / `units_sold` | Numeric | Yes | Quantity sold on date |
| `current_stock` | Numeric | Yes | Current on-hand stock inventory |
| `unit_cost` | Numeric | Optional | Cost per unit (defaults to estimate if missing) |
| `price` | Numeric | Optional | Listing price per unit |

---

## 🧪 Running Unit Tests

```bash
python tests/test_logic.py
```

---

## 📄 License & Attribution

Developed for **Project FORESIGHT - AI Powered Demand Forecasting & Inventory Intelligence**.
© 2026 Project FORESIGHT. All Rights Reserved.
