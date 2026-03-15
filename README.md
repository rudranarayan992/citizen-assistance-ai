# Citizen Assistance AI Platform

A prototype platform for citizens to report incidents, receive AI-guided assistance using government data, laws, and escalation contacts.

## Features

- Incident reporting with automatic type detection
- Nearest police station finder
- Victim guidance with step-by-step actions
- Escalation system
- Case tracking
- Legal disclaimers

## Backend

Built with FastAPI, uses CSV/JSON data sources.

### Endpoints

- `POST /report_incident` - Submit incident report
- `GET /nearest_station?lat={lat}&lon={lon}` - Find nearest police station
- `GET /escalation_contacts` - Get escalation contacts
- `GET /case_tracker/{case_id}` - Track case status
- `GET /government_schemes` - List schemes
- `GET /laws` - List laws
- `POST /ask_question` - Ask legal questions

### Running Backend

```bash
cd "backend works/backend"
pip install -r requirements.txt
uvicorn main:app --reload
```

## Frontend

Built with React/Vite, mobile-first design.

### Running Frontend

```bash
cd frontend
npm install
npm run dev
```

## Data Sources

- Police stations, case timelines, escalation contacts, laws, government schemes
- AI response templates and legal disclaimers

## Usage

1. Start backend on port 8000
2. Start frontend on port 5173
3. Report incident via form
4. Receive guidance and track case