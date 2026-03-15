from serpapi import Client
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
from geopy.distance import geodesic
import json
import uuid
from fastapi.middleware.cors import CORSMiddleware
from geopy.geocoders import Nominatim

# Load SerpApi API key from environment (set SERPAPI_API_KEY). If absent, fall back to the provided default key.
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
if not SERPAPI_API_KEY:
    # Default key (provided by user) - override this with your own key in the environment for production.
    SERPAPI_API_KEY = "394d4740-2079-11f1-b8af-cf23eff44fec"
    print("Warning: SERPAPI_API_KEY not set in environment; using default key (not recommended for production).")
os.environ["SERPAPI_API_KEY"] = SERPAPI_API_KEY

app = FastAPI(title="Citizen Assistance AI Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_serpapi_client():
    """Return a configured SerpApi client, or None if the API key is missing/invalid."""
    if not SERPAPI_API_KEY:
        return None
    try:
        return Client()
    except Exception as e:
        print(f"SerpApi client init failed: {e}")
        return None

# Load data
police_df = pd.read_csv('c:/Users/rudra/Desktop/citizen-assistance-ai/data/police_stations.csv')
resolution_df = pd.read_csv('c:/Users/rudra/Desktop/citizen-assistance-ai/data/core/case_resolution_times.csv')
esc_df = pd.read_csv('c:/Users/rudra/Desktop/citizen-assistance-ai/data/core/escalation_contacts.csv')
schemes_df = pd.read_csv('c:/Users/rudra/Desktop/citizen-assistance-ai/data/core/government_schemes.csv')
laws_df = pd.read_csv('c:/Users/rudra/Desktop/citizen-assistance-ai/data/core/laws.csv')

with open('c:/Users/rudra/Desktop/citizen-assistance-ai/data/core/incident_types.json') as f:
    incident_types = json.load(f)

incident_types = incident_types["incident_legal_mapping"]

with open('c:/Users/rudra/Desktop/citizen-assistance-ai/docs/ai_response_templates.json') as f:
    templates = json.load(f)

with open('c:/Users/rudra/Desktop/citizen-assistance-ai/data/compliance/legal_disclaimers.json') as f:
    disclaimers = json.load(f)

cases = {}  # In-memory storage, use DB in production

class IncidentReport(BaseModel):
    name: str
    age: int
    gender: str
    description: str
    location: str  # "lat,lon"
    date_time: str
    severity: int = 5  # 1-10

def score_severity(description: str) -> int:
    score = 5
    high_severity = ["violence", "attack", "assault", "rape", "murder"]
    med_severity = ["threat", "abuse", "fraud", "scam", "theft"]
    for word in high_severity:
        if word in description.lower():
            score += 3
    for word in med_severity:
        if word in description.lower():
            score += 1
    return min(score, 10)

def detect_incident_type(description: str) -> str:
    description_lower = description.lower()

    # Emergency phone theft keyword detection (covers common phrasing variations)
    if "phone" in description_lower and any(k in description_lower for k in ["stolen", "stole", "lost"]):
        return "mobile_theft"

    for item in incident_types:
        for keyword in item["keywords"]:
            if keyword in description_lower:
                return item["id"]
    return "general"  # default

def get_legal_sections(incident_type: str):
    # Simple mapping
    mappings = {
        "cyber_fraud": ["IT Act 66C", "IT Act 66D", "IPC 420"],
        "domestic_violence": ["DV Act 2005", "IPC 498A"],
        "theft": ["IPC 379"],
        "assault": ["IPC 323", "IPC 324"]
    }
    sections = mappings.get(incident_type, [])
    if not sections:
        # Search web for legal sections (requires SERPAPI_API_KEY)
        client = get_serpapi_client()
        if client:
            try:
                results = client.search(
                    q=f"{incident_type} legal sections Indian law",
                    location="India",
                    num=3
                )
                if "organic_results" in results:
                    for result in results["organic_results"]:
                        snippet = result.get("snippet", "")
                        # Extract potential sections
                        import re
                        secs = re.findall(r'(IPC \d+|IT Act \d+[A-Z]?|DV Act \d+)', snippet)
                        sections.extend(secs)
                sections = list(set(sections))  # unique
            except Exception as e:
                print(f"Legal sections search failed: {e}")
    return sections if sections else ["Please consult a legal expert"]

def generate_complaint_template(report, incident_type, nearest, legal_sections):
    template = f"""
    FIR / Complaint Template

    Date: {report.date_time.split('T')[0]}
    Time: {report.date_time.split('T')[1] if 'T' in report.date_time else report.date_time}

    Victim Details:
    Name: {report.name}
    Age: {report.age}
    Gender: {report.gender}

    Incident Description:
    {report.description}

    Incident Type: {incident_type.replace('_', ' ').title()}
    Location: {report.location}

    Nearest Police Station:
    {nearest['name']}
    {nearest['address']}
    Phone: {nearest['phone']}
    Email: {nearest['email']}

    Applicable Legal Sections:
    {', '.join(legal_sections)}

    Signature: ____________________
    """
    return template.strip()

def get_nearest_station(lat: float, lon: float, location_query: str = None):
    """Try to resolve a nearby police station.

    Priority:
    1) Match the user-provided location string against the local police stations list.
    2) Use reverse geocoding to find a district/city and match against the list.
    3) Fallback to SerpApi local search.
    """

    def _fallback():
        return {
            "name": "Unable to find police station",
            "address": "Please contact local authorities",
            "phone": "112",
            "email": "N/A"
        }

    # 1) Try to match the raw location string (e.g., city/district name) against our police stations list.
    if location_query:
        query = location_query.strip().lower()
        if query:
            for _, row in police_df.iterrows():
                city = str(row.get("District/City", "")).lower()
                office = str(row.get("Office/Designation", "")).lower()
                state = str(row.get("State", "")).lower()
                if query in city or query in office or query in state:
                    return {
                        "name": row.get("Office/Designation", "Unknown"),
                        "address": f"{row.get('District/City', '')}, {row.get('State', '')}",
                        "phone": row.get("Contact Number", "Unknown"),
                        "email": "N/A"
                    }

    # 2) Try reverse geocoding to get a place name and match it against the list.
    try:
        geolocator = Nominatim(user_agent="citizen-assistance-ai")
        location = geolocator.reverse((lat, lon), exactly_one=True, language="en")
        if location and location.raw and "address" in location.raw:
            addr = location.raw["address"]
            candidates = [
                addr.get("city"),
                addr.get("town"),
                addr.get("village"),
                addr.get("county"),
                addr.get("state"),
                addr.get("state_district"),
                addr.get("district"),
            ]
            candidates = [c.lower() for c in candidates if c]
            for candidate in candidates:
                for _, row in police_df.iterrows():
                    city = str(row.get("District/City", "")).lower()
                    office = str(row.get("Office/Designation", "")).lower()
                    state = str(row.get("State", "")).lower()
                    if candidate in city or candidate in office or candidate in state:
                        return {
                            "name": row.get("Office/Designation", "Unknown"),
                            "address": f"{row.get('District/City', '')}, {row.get('State', '')}",
                            "phone": row.get("Contact Number", "Unknown"),
                            "email": "N/A"
                        }
    except Exception as e:
        print(f"Reverse geocoding failed: {e}")

    # 3) Fallback: use SerpApi local search if available.
    client = get_serpapi_client()
    if not client:
        return _fallback()

    try:
        results = client.search(
            q=f"police station near {lat},{lon}",
            location="India",
            num=1
        )
        if "local_results" in results and results["local_results"]:
            place = results["local_results"][0]
            return {
                "name": place.get("title", "Unknown"),
                "address": place.get("address", "Unknown"),
                "phone": place.get("phone", "Unknown"),
                "email": "N/A"
            }
    except Exception as e:
        print(f"Search failed: {e}")

    return _fallback()

@app.post("/report_incident")
def report_incident(report: IncidentReport):
    try:
        incident_type = detect_incident_type(report.description)
        severity = score_severity(report.description)  # or use report.severity

        emergency_mode = any(
            item.get("id") == incident_type and item.get("emergency")
            for item in incident_types
        )
        emergency_message = (
            "⚠ EMERGENCY DETECTED. Call 112 immediately."
            if emergency_mode
            else ""
        )
        offline_help_points = []

        try:
            lat, lon = map(float, report.location.split(','))
        except ValueError:
            geolocator = Nominatim(user_agent="citizen-assistance-ai")
            location = geolocator.geocode(report.location)
            if location:
                lat, lon = location.latitude, location.longitude
            else:
                raise HTTPException(status_code=400, detail="Invalid location: could not geocode")
        nearest = get_nearest_station(lat, lon, report.location)
        guidance = templates.get(incident_type, {})
        if not guidance:
            client = get_serpapi_client()
            if client:
                try:
                    results = client.search(
                        q=f"what to do if {incident_type} in India",
                        location="India",
                        num=3
                    )
                    guidance_text = ""
                    if "organic_results" in results:
                        for result in results["organic_results"]:
                            guidance_text += result.get("snippet", "") + " "
                    # Parse into steps
                    immediate_steps = guidance_text.split(". ")[:5]  # rough split
                    expected_response = ["Consult local authorities for updates"]
                    escalation_steps = ["Contact higher police officials", "Approach court"]
                except Exception as e:
                    print(f"Guidance search failed: {e}")
                    immediate_steps = ["Report to nearest police station", "Seek immediate help if needed"]
                    expected_response = ["Police will investigate"]
                    escalation_steps = ["Contact local authorities"]
            else:
                immediate_steps = ["Report to nearest police station", "Seek immediate help if needed"]
                expected_response = ["Police will investigate"]
                escalation_steps = ["Contact local authorities"]
            legal_sections = get_legal_sections(incident_type)
        else:
            legal_sections = guidance.get("legal_sections_applied", [])
            immediate_steps = guidance.get("immediate_steps_0_24_hours", [])
            expected_24h = guidance.get("expected_response_24_hours", {})
            expected_48h = guidance.get("expected_response_48_hours", {})
            expected_response = []
            if expected_24h:
                expected_response.extend([f"24h: {k} - {v}" for k, v in expected_24h.items()])
            if expected_48h:
                expected_response.extend([f"48h: {k} - {v}" for k, v in expected_48h.items()])
            escalation_steps = guidance.get("if_police_do_not_act", [])
            if isinstance(escalation_steps, dict):
                escalation_steps = [f"{k}: {v}" for k, v in escalation_steps.items()]

            offline_help_points = guidance.get("offline_help_points", [])
            emergency_mode = any(
                item.get("id") == incident_type and item.get("emergency")
                for item in incident_types
            )
            emergency_message = (
                "⚠ EMERGENCY DETECTED. Call 112 immediately."
                if emergency_mode
                else ""
            )

        timeline = resolution_df[resolution_df['incident_type'] == incident_type]['average_resolution_days']
        timeline_est = int(timeline.iloc[0]) if not timeline.empty else 30
        complaint_template = generate_complaint_template(report, incident_type, nearest, legal_sections)
        case_id = str(uuid.uuid4())
        cases[case_id] = {
            "status": "Reported",
            "incident_type": incident_type,
            "severity": severity,
            "nearest_station": nearest,
            "timeline_estimate": timeline_est,
            "created_at": report.date_time
        }
        return {
            "case_id": case_id,
            "incident_type": incident_type,
            "severity_score": severity,
            "legal_sections": legal_sections,
            "emergency_mode": emergency_mode,
            "emergency_message": emergency_message,
            "immediate_steps": immediate_steps,
            "nearest_police_station": nearest,
            "expected_response_24_48h": expected_response,
            "escalation_steps": escalation_steps,
            "offline_help_points": offline_help_points,
            "timeline_estimate_days": timeline_est,
            "complaint_template": complaint_template,
            "disclaimer": disclaimers["disclaimers"].get(incident_type, disclaimers["default_disclaimer"])
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/nearest_station")
def nearest_station(lat: float, lon: float):
    return get_nearest_station(lat, lon)

@app.get("/case_tracker/{case_id}")
def track_case(case_id: str):
    if case_id not in cases:
        raise HTTPException(status_code=404, detail="Case not found")
    return cases[case_id]

@app.get("/government_schemes")
def get_schemes():
    return schemes_df.to_dict('records')

@app.get("/laws")
def get_laws():
    return laws_df.to_dict('records')

# Simple RAG for questions
@app.post("/ask_question")
def ask_question(question: str):
    # First, check local data
    response = ""
    disclaimer = disclaimers["default_disclaimer"]
    if "fraud" in question.lower():
        response = "Refer to IT Act 66 for cyber crimes."
    elif "violence" in question.lower():
        response = "Refer to DV Act 2005 for domestic violence."
    elif "theft" in question.lower():
        response = "Refer to IPC 379 for theft."
    elif "assault" in question.lower():
        response = "Refer to IPC 323 or 324 for assault."
    
    if not response:
        client = get_serpapi_client()
        if client:
            try:
                results = client.search(
                    q=question + " Indian law",
                    location="India",
                    num=5
                )
                if "organic_results" in results:
                    for result in results["organic_results"][:3]:
                        response += result.get("snippet", "") + " "
            except Exception as e:
                print(f"Question search failed: {e}")
                response = "Please consult a legal expert for advice."
        else:
            response = "Please consult a legal expert for advice."
    
    return {"answer": response.strip(), "disclaimer": disclaimer}