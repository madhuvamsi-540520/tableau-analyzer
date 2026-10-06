# Tableau Analysis Tool

Enterprise BI metadata analyzer for Tableau workbooks (`.twb` / `.twbx`). A
multi-module, tabbed web application; the **Data Source Details (Inventory)**
module is under active development.

> The earlier Tableau → Power BI **PBIP converter** lives untouched under
> `../parked/tableau-to-pbip-app/` and is reserved for the future *Migration
> Assessment* module.

## Stack
- **Backend:** Python / FastAPI (port 8000)
- **Frontend:** React + Vite + Ant Design (port 5173, proxies `/api` to the backend)

## Run (development)
Backend:
```
cd backend
py -m pip install -r requirements.txt
py -m uvicorn app.main:app --reload --port 8000
```
Frontend:
```
cd frontend
npm install
npm run dev
```
Open http://localhost:5173.

## Tests
```
cd backend
py -m pytest
```

## Status — Data Source Details (Inventory) module: COMPLETE
- 5-tab shell (Data Source Details active; other four tabs are "Coming soon").
- Dark / light theme toggle; responsive (desktop / tablet).
- Upload one or more `.twb` / `.twbx` (content validation, hardened `.twbx`
  unzip, session-scoped TTL job store).
- **Parser**: all data sources, connections (typed), tables, columns
  (role/aggregation/nullable), relationships & joins, unions, data-source
  filters, custom SQL (with sqlglot analysis), calculated-field & parameter counts.
- **Classification**: Star / Snowflake / Galaxy / Flat / Hybrid with reasoning;
  complexity metrics.
- **Schema diagram** (React Flow, auto-layout) beside a **data lineage summary**.
- **Technical Assessment**: deterministic technical debt, trade-offs, modeling
  risks, data-quality risks, governance (incl. PII), scalability, performance,
  optimization + an enterprise best-practice review and a 0–100 maturity score.
- **Exports**: Excel, CSV, JSON, PDF; copy-to-clipboard for SQL and metadata.

Backend: `py -m pytest` → 54 tests. The other four modules are future work.
