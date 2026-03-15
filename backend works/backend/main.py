import os
from serpapi import Client
import pandas as pd
from geopy.distance import geodesic
import json
import uuid
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
from geopy.geocoders import Nominatim
from fastapi.middleware.cors import CORSMiddleware

# Load SerpApi API key from environment (set SERPAPI_API_KEY). If absent, fall back to the provided default key.
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
if not SERPAPI_API_KEY:
    # Default key (provided by user) - override this with your own key in the environment for production.
    SERPAPI_API_KEY = "394d4740-2079-11f1-b8af-cf23eff44fec"
    print("Warning: SERPAPI_API_KEY not set in environment; using default key (not recommended for production).")
os.environ["SERPAPI_API_KEY"] = SERPAPI_API_KEY

# Gemini API setup
GEMINI_API_KEY = "AIzaSyBSUOUtWf9DwTJqoZjoGgUhBHtRaE-LKqM"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

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

# Gemini-based functions for enhanced processing

def detect_incident_type_gemini(description: str) -> str:
    incident_ids = [item["id"] for item in incident_types]
    prompt = f"""
Analyze the following incident description and classify it into one of these categories: {', '.join(incident_ids)}.
If none match closely, use 'general'.

Description: {description}

Respond with only the category ID.
"""
    try:
        response = model.generate_content(prompt)
        category = response.text.strip().lower()
        if category in incident_ids:
            return category
        else:
            return "general"
    except Exception as e:
        print(f"Gemini incident detection failed: {e}")
        return detect_incident_type(description)  # fallback

def score_severity_gemini(description: str) -> int:
    prompt = f"""
Rate the severity of this incident on a scale of 1-10, where 1 is minor and 10 is life-threatening or extremely serious.

Description: {description}

Respond with only a number between 1 and 10.
"""
    try:
        response = model.generate_content(prompt)
        score = int(response.text.strip())
        return max(1, min(10, score))
    except Exception as e:
        print(f"Gemini severity scoring failed: {e}")
        return score_severity(description)  # fallback

def get_legal_sections_gemini(incident_type: str) -> list:
    prompt = f"""
List the relevant Indian legal sections (like IPC, IT Act, etc.) for the incident type: {incident_type}.

Provide a comma-separated list of sections. If unsure, say "Please consult a legal expert".
"""
    try:
        response = model.generate_content(prompt)
        sections = [s.strip() for s in response.text.split(',') if s.strip()]
        return sections if sections else ["Please consult a legal expert"]
    except Exception as e:
        print(f"Gemini legal sections failed: {e}")
        return get_legal_sections(incident_type)  # fallback

def get_action_guide_gemini(incident_type: str) -> list:
    prompt = f"""
Provide immediate action steps (within 24 hours) for someone who experienced: {incident_type} in India.

List 5-7 concise steps.
"""
    try:
        response = model.generate_content(prompt)
        steps = [line.strip() for line in response.text.split('\n') if line.strip() and not line.startswith('*')]
        return steps[:7]
    except Exception as e:
        print(f"Gemini action guide failed: {e}")
        return ["Report to nearest police station", "Seek immediate help if needed"]

def get_helpline_suggestions_gemini(incident_type: str) -> list:
    prompt = f"""
Suggest relevant helplines or support services in India for: {incident_type}.

List 3-5 helplines with contact numbers if possible.
"""
    try:
        response = model.generate_content(prompt)
        suggestions = [line.strip() for line in response.text.split('\n') if line.strip()]
        return suggestions[:5]
    except Exception as e:
        print(f"Gemini helplines failed: {e}")
        return ["Police: 100", "Women Helpline: 1091"]

def get_escalation_path_gemini(incident_type: str) -> list:
    prompt = f"""
If police do not respond adequately to: {incident_type}, what are the escalation steps in India?

List 4-6 escalation steps.
"""
    try:
        response = model.generate_content(prompt)
        steps = [line.strip() for line in response.text.split('\n') if line.strip()]
        return steps[:6]
    except Exception as e:
        print(f"Gemini escalation failed: {e}")
        return ["Contact local authorities", "Approach court"]

def get_deep_web_intelligence(incident_type: str, city: str):
    """
    Combines SerpApi and Gemini to find specific URLs and local procedures.
    """
    queries = [
        f"how to file {incident_type} in {city} online portal",
        f"official police circular for {incident_type} reporting India 2026",
        f"NGOs providing legal aid for {incident_type} in {city}",
        f"latest BNS sections for {incident_type}"
    ]
    
    web_intel = []
    client = get_serpapi_client()
    if client:
        for q in queries:
            search = client.search(q=q, location="India", num=2)
            for res in search.get("organic_results", []):
                web_intel.append({"title": res.get("title"), "link": res.get("link")})
    
    return web_intel

def get_strategic_advice_gemini(incident_type: str, description: str):
    """
    Generates a 360-degree legal and tactical strategy.
    """
    prompt = f"""
Act as a high-level Legal Strategist and Citizen Advocate in India. 
Incident: {incident_type}
Details: {description}

Provide a structured response in JSON format with the following keys:
1. 'risk_mitigation': Immediate technical/physical steps to stop further damage.
2. 'legal_remedies': Specific BNS/BNSS sections and specialized acts.
3. 'administrative_path': How to deal with bureaucracies (Banks, ISPs, NGOs).
4. 'judicial_path': How to use the courts if the police fail.
5. 'evidence_checklist': Specific items to collect (metadata, screenshots, MLC).
6. 'psychosocial_support': Relevant helplines and NGOs.

Ensure the tone is supportive, direct, and authoritative. 
Use the new Bharatiya Nyaya Sanhita (BNS) terminology for 2026.
"""
    try:
        response = model.generate_content(prompt)
        # Parse the JSON from Gemini (ensure it's clean JSON)
        json_text = response.text.strip()
        if json_text.startswith('```json'):
            json_text = json_text[7:]
        if json_text.endswith('```'):
            json_text = json_text[:-3]
        return json.loads(json_text.strip())
    except Exception as e:
        print(f"Strategic advice failed: {e}")
        return {"error": "Could not generate advanced strategy."}

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

def get_relevant_updates(incident_type: str, last_checked: str = None):
    """Get relevant portal updates for the incident type since last checked."""
    if not os.path.exists('portal_updates.csv'):
        return []
    
    df = pd.read_csv('portal_updates.csv')
    
    # Mapping portals to incident types
    portal_mapping = {
        "NALSA": ["rape", "domestic_violence", "child_marriage", "abandonment_of_child"],
        "CyberCrime": ["cyber_fraud", "mobile_theft"],
        "SancharSaathi": ["mobile_theft"]
    }
    
    relevant_portals = [p for p, types in portal_mapping.items() if incident_type in types]
    df_filtered = df[df['portal'].isin(relevant_portals)]
    
    if last_checked:
        df_filtered = df_filtered[df_filtered['scraped_at'] > last_checked]
    
    return df_filtered.to_dict('records')

@app.post("/report_incident")
def report_incident(report: IncidentReport):
    try:
        incident_type = detect_incident_type_gemini(report.description)
        severity = score_severity_gemini(report.description)  # or use report.severity

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
            # Use Gemini for guidance
            immediate_steps = get_action_guide_gemini(incident_type)
            expected_response = ["Police will investigate within 24-48 hours"]
            escalation_steps = get_escalation_path_gemini(incident_type)
            helplines = get_helpline_suggestions_gemini(incident_type)
            legal_sections = get_legal_sections_gemini(incident_type)
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

        helplines = get_helpline_suggestions_gemini(incident_type)

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
            "created_at": report.date_time,
            "last_checked": report.date_time
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
            "helplines": helplines,
            "offline_help_points": offline_help_points,
            "timeline_estimate_days": timeline_est,
            "complaint_template": complaint_template,
            "relevant_updates": get_relevant_updates(incident_type),
            "disclaimer": disclaimers["disclaimers"].get(incident_type, disclaimers["default_disclaimer"])
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/report_incident_pro")
def report_incident_pro(report: IncidentReport):
    # 1. Classification & Severity
    incident_type = detect_incident_type_gemini(report.description)
    severity = score_severity_gemini(report.description)
    
    # 2. Get the Multi-Dimensional Strategy
    strategy = get_strategic_advice_gemini(incident_type, report.description)
    
    # 3. Dynamic Escalation Logic (The "What if" Path)
    # We define a hierarchy: SHO -> SP -> Magistrate -> High Court
    escalation_logic = [
        {"step": 1, "authority": "Station House Officer (SHO)", "action": "File FIR/Zero FIR", "timeline": "Immediate"},
        {"step": 2, "authority": "Superintendent of Police (SP)", "action": "Written complaint via Regd Post u/s 154(3) BNSS", "timeline": "After 48h of inaction"},
        {"step": 3, "authority": "Judicial Magistrate", "action": "Application u/s 156(3) to compel FIR", "timeline": "If SP fails"},
        {"step": 4, "authority": "High Court", "action": "Writ of Mandamus", "timeline": "Final Resort"}
    ]

    # 4. Evidence Strategy (Specific to Incident)
    evidence_guide = strategy.get('evidence_checklist', ["Document all interactions"])

    # 5. Geolocation for Nearest Help
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

    return {
        "incident_analysis": {
            "category": incident_type,
            "severity": severity,
            "legal_foundation": strategy.get('legal_remedies')
        },
        "action_plan": {
            "immediate_risk_mitigation": strategy.get('risk_mitigation'),
            "administrative_steps": strategy.get('administrative_path'),
            "support_resources": strategy.get('psychosocial_support')
        },
        "legal_warfare": {
            "escalation_protocol": escalation_logic,
            "judicial_options": strategy.get('judicial_path'),
            "evidence_preservation": evidence_guide
        },
        "document_automation": {
            "template": generate_complaint_template(report, incident_type, nearest, strategy.get('legal_remedies', []))
        }
    }

@app.post("/generate_full_strategy")
def generate_strategy(report: IncidentReport):
    # 1. Classification & Severity
    incident_type = detect_incident_type_gemini(report.description)
    severity = score_severity_gemini(report.description)
    
    # 2. Local Data Fetch
    local_info = {}
    for item in incident_types:
        if item["id"] == incident_type:
            local_info = item
            break
    
    # 3. Geolocation for City
    try:
        lat, lon = map(float, report.location.split(','))
        geolocator = Nominatim(user_agent="citizen-assistance-ai")
        location = geolocator.reverse((lat, lon), exactly_one=True, language="en")
        city_name = location.raw.get("address", {}).get("city", "Delhi") if location else "Delhi"
    except:
        city_name = "Delhi"  # fallback
    
    # 4. Real-time Web Intelligence (Search)
    web_links = get_deep_web_intelligence(incident_type, city_name)
    
    # 5. Gemini Strategic Synthesis
    strategy_prompt = f"""
    Create a 'High-Performance' legal strategy for {incident_type}.
    Context: {report.description}.
    Current Law: Bharatiya Nyaya Sanhita (BNS) 2026.
    
    Structure the response into:
    - Step-by-Step Tactical Guide
    - Evidence Preservation (Technical)
    - Escalation logic if Police refuse FIR
    - Top 3 official Gov URLs for this issue
    """
    
    strategy_response = model.generate_content(strategy_prompt)
    
    # 6. Nearest Station
    nearest = get_nearest_station(lat, lon, report.location)
    
    return {
        "incident_analysis": {
            "category": incident_type,
            "severity": severity,
            "local_data": local_info
        },
        "tactical_strategy": strategy_response.text,
        "verified_resources": web_links,
        "nearest_station": nearest,
        "relevant_updates": get_relevant_updates(incident_type),
        "legal_template_ready": True
    }

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