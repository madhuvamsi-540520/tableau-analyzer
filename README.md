# PowerShift BI Migration Studio

Enterprise Tableau → Power BI migration assessment tool. Upload Tableau
workbooks (`.twb` / `.twbx`) and get metadata analysis, a Well-Architected
review, and a generated PBIP project.

## Stack
- **Backend:** Python / FastAPI (port 8000)
- **Frontend:** React + Vite + Ant Design (port 5173, proxies `/api` to the backend)

In production both ship as **one container**: the Vite bundle is built and
served by FastAPI alongside `/api`, so the browser sees a single origin.

## Modules
| Tab | What it does |
|---|---|
| **Tableau Analysis** | Workbook/worksheet inventory, calculated fields, groups/sets/bins, visualization summary |
| **Data Source Details** | Connections, tables, columns, joins, unions, custom SQL (sqlglot); Star/Snowflake/Galaxy/Flat/Hybrid classification; React Flow schema diagram + lineage; technical assessment with a 0–100 maturity score |
| **DAX & Formula** | Tableau calculation → DAX conversion, with optional AI-assisted suggestions |
| **Dashboards & Worksheets** | Rationalization: similarity analysis, consolidation, KPI dedup, viz best practices, AI review |
| **Well-Architected** | Pillar scorecard (security, performance, governance, Fabric/semantic readiness, technical debt, migration risk), quick wins, remediation roadmap |
| **Migration Assessment** | PBIP generation (TMDL, M queries, visuals) and effort estimation |

Exports: Excel, CSV, JSON, PDF.

## Run (development)
Backend:
```
cd backend
py -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
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
.venv/Scripts/python -m pytest
```
131 tests.

## Deployment
See [DEPLOY.md](DEPLOY.md). `./deploy.sh` builds from source and deploys to
Cloud Run behind IAP, restricted to the Mastech domain.

## Contributing
- Branch per change (`feat/…`, `fix/…`); do not commit to `main` directly.
- `.gitattributes` pins LF in the repository — do not override it locally.
- Run the backend suite before pushing.
- Never commit secrets. API keys are pasted at runtime in the UI, not stored.
