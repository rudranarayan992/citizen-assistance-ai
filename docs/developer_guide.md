# Developer Guide — Citizen Assistance AI

## Purpose
This guide explains how to boot the prototype, where the datasets live, and how the components connect.

## Folder map
- `data/core/` — knowledge datasets (laws, helplines, police stations, schemes, templates)
- `data/compliance/` — legal disclaimers & emergency rules
- `api/` — backend endpoints (to be implemented)
- `backend/` — prototype scripts (incident detector, law retriever)
- `docs/` — design and policy docs
- `templates/` — complaint templates

## Quickstart (dev)
1. Clone repo.
2. Create virtualenv: `python -m venv venv && . venv/bin/activate` (Windows: `venv\Scripts\activate`)
3. Install minimal libs: `pip install flask pandas sentence-transformers faiss-cpu openai`
4. Load datasets: check `data/core/*.csv` and `incident_types.json`.
5. Run the prototype server (example): `python api/app.py` (server skeleton provided by devs).

## APIs (skeleton)
- `POST /detect` — body: `{ "message": "..." }` → returns `{ "incident":"cyber_fraud" }`
- `POST /report-incident` — body: case JSON → stores and returns a `case_id`
- `GET /nearest-police?lat=&lng=` — returns nearest police station

## Where to add new data
Add rows to CSV files in `data/core/`. Keep `latitude,longitude` for location rows.

## Contact / Maintainers
Project owner: repository /docs contacts.