"""
Citizen Assistance AI Platform v3.0
Advanced Legal & Emergency Assistance System for Indian Citizens
Production-Ready | BNS 2026 Compliant | Multi-Incident Support
"""

import os
import json
import logging
import re
import hashlib
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from uuid import uuid4
from pathlib import Path
from functools import lru_cache

import google.generativeai as genai
import pandas as pd
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from pydantic import BaseModel, Field, validator
from serpapi import Client

# ============================================================
# SECTION 1: CONFIGURATION & INITIALIZATION
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("CitizenAI")

# --- Path Configuration ---
BASE_DIR = Path("C:/Users/rudra/Desktop/citizen-assistance-ai")
DATA_DIR = BASE_DIR / "data"
CORE_DIR = DATA_DIR / "core"
DOCS_DIR = BASE_DIR / "docs"

# --- API Keys ---
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "394d4740-2079-11f1-b8af-cf23eff44fec")
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY",  "AIzaSyBSUOUtWf9DwTJqoZjoGgUhBHtRaE-LKqM")

# --- Initialize Gemini ---
genai.configure(api_key=GEMINI_API_KEY)
try:
    gemini_model = genai.GenerativeModel("gemini-1.5-flash")
    logger.info("Gemini model initialized successfully.")
except Exception as e:
    logger.error(f"Gemini initialization failed: {e}")
    gemini_model = None

# ============================================================
# SECTION 2: DATA LOADING
# ============================================================

def load_json_file(path: Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            logger.info(f"Loaded JSON: {path.name} ({len(data)} keys)")
            return data
    except FileNotFoundError:
        logger.error(f"File NOT found: {path}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error in {path.name}: {e}")
        return {}


def save_json_file(path: Path, data: dict):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved JSON: {path.name} ({len(data)} keys)")
    except Exception as e:
        logger.error(f"Failed to save JSON {path}: {e}")


def load_csv_file(path: Path) -> pd.DataFrame:
    try:
        df = pd.read_csv(path)
        logger.info(f"Loaded CSV: {path.name} ({len(df)} rows)")
        return df
    except FileNotFoundError:
        logger.warning(f"CSV NOT found: {path}")
        return pd.DataFrame()

# Load all data files
GUIDES         = load_json_file(CORE_DIR / "victim_help_guides.json")
INCIDENT_TYPES = load_json_file(CORE_DIR / "incident_types.json")
DISCLAIMERS    = load_json_file(DATA_DIR / "compliance" / "legal_disclaimers.json")
TEMPLATES      = load_json_file(DOCS_DIR / "ai_response_templates.json")
VOLUNTEERS     = load_json_file(CORE_DIR / "volunteers.json").get("volunteers", [])

police_df      = load_csv_file(DATA_DIR / "police_stations.csv")
resolution_df  = load_csv_file(CORE_DIR / "case_resolution_times.csv")
schemes_df     = load_csv_file(CORE_DIR / "government_schemes.csv")
laws_df        = load_csv_file(CORE_DIR / "laws.csv")
escalation_df  = load_csv_file(CORE_DIR / "escalation_contacts.csv")

# Load or initialize cache
try:
    AI_CACHE = load_json_file(CORE_DIR / "ai_cache.json")
except Exception:
    AI_CACHE = {}

# ============================================================
# SECTION 3: KEYWORD ENGINE (COMPREHENSIVE)
# ============================================================

INCIDENT_KEYWORD_MAP: Dict[str, Dict] = {

    "cyber_fraud": {
        "priority": 8,
        "emergency": False,
        "keywords": [
            # UPI / Payment fraud
            "upi fraud", "upi scam", "upi hack", "google pay fraud", "phonepe fraud",
            "paytm fraud", "bhim fraud", "upi transaction failed refund",
            # Banking fraud
            "bank fraud", "unauthorized transaction", "money deducted without permission",
            "account hacked", "net banking fraud", "debit card fraud", "credit card fraud",
            "emi fraud", "loan fraud", "fake loan app",
            # OTP / Phishing
            "otp fraud", "otp shared by mistake", "otp given to stranger",
            "phishing link", "phishing website", "fake bank website",
            "clicked suspicious link", "malicious link",
            # Scam calls
            "fake customer care", "customer care scam", "impersonating bank",
            "false police call", "fake cbi call", "fake rbi call",
            "digital arrest", "sextortion", "blackmail online",
            # Investment / Trading fraud
            "investment fraud", "trading scam", "stock market fraud",
            "crypto fraud", "bitcoin scam", "ponzi scheme",
            "high return scam", "multi level marketing fraud",
            # Remote access
            "anydesk fraud", "teamviewer scam", "screen share fraud",
            "remote access scam",
            # Job / Part-time fraud
            "part time job fraud", "work from home scam", "online job fraud",
            "task completion fraud", "fake recruitment",
            # Other online
            "kyc fraud", "kyc update scam", "lottery fraud", "kbc scam",
            "fake prize", "online shopping fraud", "ecommerce fraud",
            "facebook marketplace scam", "olx scam", "quikr fraud",
            "dating app fraud", "matrimony fraud",
            # Simple user phrasing
            "money stolen online", "online money gone", "fraud call",
            "scam message", "cheated online", "lost money online"
        ]
    },

    "mobile_theft": {
        "priority": 9,
        "emergency": False,
        "keywords": [
            # Direct theft
            "phone stolen", "mobile stolen", "phone theft", "mobile theft",
            "phone snatched", "mobile snatched", "phone grabbed",
            "snatching phone", "bike snatching phone",
            # Lost
            "lost phone", "phone missing", "lost my mobile",
            "mobile not found", "phone left behind", "phone misplaced",
            # Pickpocket
            "pickpocket phone", "phone from pocket", "phone from bag stolen",
            "bag stolen with phone", "purse stolen phone",
            # Specific locations
            "phone stolen in metro", "phone stolen in bus", "phone stolen at railway",
            "phone stolen at market", "phone stolen at mall",
            "phone stolen while walking", "phone snatched on road",
            # Identity risk
            "phone stolen bank app", "phone stolen upi", "phone stolen otp",
            "stolen phone misuse", "imei block", "ceir block",
            # Simple user phrasing
            "stole my phone", "took my phone", "ran with my phone",
            "someone grabbed phone", "my mobile is gone"
        ]
    },

    "domestic_violence": {
        "priority": 10,
        "emergency": True,
        "keywords": [
            # Physical violence
            "husband beating", "husband hits", "husband slapped me",
            "husband kicked", "in-laws beating", "family beating",
            "physically abused", "domestic abuse", "domestic violence",
            "wife beating", "beaten at home", "attacked by husband",
            # Dowry
            "dowry harassment", "dowry demand", "dowry torture",
            "harassed for money", "in-laws demanding money",
            # Emotional abuse
            "mental torture by husband", "emotional abuse at home",
            "husband threatens", "family threats", "threatened to kill",
            "verbal abuse at home", "constantly insulted",
            # Control / Isolation
            "locked in room", "not allowed to go out",
            "mobile taken away", "isolated from family",
            "not given food", "economic abuse", "no money for food",
            # Thrown out
            "thrown out of house", "forced to leave home",
            "husband asked to leave", "in-laws threw me out",
            # Simple user phrasing
            "husband tortured me", "family harassing me",
            "my husband is violent", "suffering at home",
            "married life problem violence"
        ]
    },

    "sexual_harassment": {
        "priority": 10,
        "emergency": True,
        "keywords": [
            # Physical
            "molested", "groped", "touched inappropriately",
            "unwanted touching", "physical harassment", "eve teasing",
            "catcalling", "sexually assaulted",
            # Verbal / Gesture
            "sexual comments", "obscene remarks", "lewd gestures",
            "sexual jokes at work", "vulgar comments",
            # Stalking
            "stalking", "being followed", "someone following me",
            "stranger following", "following on road", "following online",
            "cyberstalking", "harassing on instagram", "harassing on whatsapp",
            # Online
            "obscene messages", "unsolicited photos", "dick pic",
            "morphed photos", "revenge porn", "intimate images shared",
            "blackmail with photos", "sextortion",
            # Workplace
            "sexual harassment at office", "boss harassing", "colleague harassment",
            "posh act complaint", "icc complaint",
            "sexual favors demanded", "harassed at work",
            # Simple user phrasing
            "man touching me", "someone following me home",
            "getting obscene calls", "obscene messages received",
            "uncomfortable with someone's behavior"
        ]
    },

    "kidnapping": {
        "priority": 10,
        "emergency": True,
        "keywords": [
            "kidnap", "kidnapped", "abducted", "abduction",
            "forced into car", "dragged into vehicle", "taken by force",
            "held captive", "locked up", "cannot escape",
            "missing person", "child missing", "child abducted",
            "my child is missing", "someone took my child",
            "ransom demand", "ransom call", "pay money for release",
            "held hostage", "hostage", "cannot contact family",
            "need help escaping", "help me get out"
        ]
    },

    "assault": {
        "priority": 9,
        "emergency": True,
        "keywords": [
            "attacked", "physically attacked", "beaten up", "hit by someone",
            "assault", "assaulted", "road rage attack",
            "gang attack", "mob attack", "lynching",
            "stabbed", "knife attack", "weapon attack",
            "acid attack", "acid thrown",
            "injured by someone", "someone hurt me",
            "neighbour attacked", "landlord attacked",
            "attacked on road", "attacked at night"
        ]
    },

    "theft": {
        "priority": 8,
        "emergency": False,
        "keywords": [
            "theft", "stolen", "robbery", "robbed", "house robbed",
            "house broken into", "burglary", "vehicle stolen",
            "bike stolen", "car stolen", "bicycle stolen",
            "gold stolen", "jewellery stolen", "cash stolen",
            "bag snatched", "chain snatching", "purse snatched",
            "wallet stolen", "shop robbed", "break in",
            "someone stole from me", "missing valuables"
        ]
    },

    "police_refusal": {
        "priority": 8,
        "emergency": False,
        "keywords": [
            "police refused fir", "police not registering",
            "police sent me away", "fir not registered",
            "police not helping", "police ignoring",
            "police demanding bribe", "police corruption",
            "police bias", "police threatening me",
            "police support accused", "police partial",
            "station refused complaint", "no fir taken",
            "police not taking action", "police said civil matter",
            "police refused to write complaint"
        ]
    },

    "child_abuse": {
        "priority": 10,
        "emergency": True,
        "keywords": [
            "child abuse", "child beaten", "child tortured",
            "child sexual abuse", "pocso", "child molestation",
            "minor assaulted", "minor abused",
            "child marriage", "child labour",
            "my child is being abused", "someone harming my child",
            "teacher beating child", "child bullying"
        ]
    },

    "missing_person": {
        "priority": 10,
        "emergency": True,
        "keywords": [
            "missing person", "person missing", "disappeared",
            "family member missing", "wife missing", "husband missing",
            "child missing", "son missing", "daughter missing",
            "not come home", "not picking phone",
            "last seen", "not contacted since",
            "missing from home", "ran away from home"
        ]
    },

    "property_dispute": {
        "priority": 5,
        "emergency": False,
        "keywords": [
            "property dispute", "land dispute", "property fraud",
            "fake registry", "property forcefully taken",
            "illegal possession", "encroachment",
            "landlord issue", "tenant dispute",
            "eviction", "illegal eviction",
            "property cheated", "real estate fraud",
            "builder fraud", "flat not delivered"
        ]
    }
}

# Emergency incident types for quick detection
EMERGENCY_TYPES = {k for k, v in INCIDENT_KEYWORD_MAP.items() if v.get("emergency")}

# Flat keyword list for ultra-fast search
ALL_KEYWORDS_FLAT = {
    kw: incident
    for incident, data in INCIDENT_KEYWORD_MAP.items()
    for kw in data["keywords"]
}

# ============================================================
# SECTION 4: PYDANTIC MODELS
# ============================================================

class IncidentReport(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, example="Priya Sharma")
    age: int = Field(..., ge=1, le=120, example=28)
    gender: str = Field(..., example="Female")
    description: str = Field(..., min_length=10, max_length=2000,
                              example="I was snatched my phone near the metro station by a person on a bike")
    location: str = Field(..., min_length=2, max_length=500,
                           example="Connaught Place, New Delhi")
    date_time: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        example="2026-03-15T18:30:00"
    )
    severity: Optional[int] = Field(None, ge=1, le=10, example=7)
    contact: Optional[str] = Field(None, example="9876543210")
    father_or_spouse_name: Optional[str] = Field(None, example="Rajesh Sharma")
    address: Optional[str] = Field(None, example="123 Main Street, Delhi 110001")
    email: Optional[str] = Field(None, example="priya@email.com")
    evidence_available: Optional[List[str]] = Field(
        None, example=["screenshots", "call recordings"]
    )
    accused_details: Optional[str] = Field(
        None, example="Unknown male, age ~30, wearing red shirt"
    )
    witness_details: Optional[str] = Field(None, example="Colleague: Arun, 9876500000")
    immediate_actions_taken: Optional[str] = Field(
        None, example="Called bank and blocked account"
    )

    @validator("date_time", pre=True, always=True)
    def validate_datetime(cls, v):
        if not v:
            return datetime.now().isoformat()
        return v

class StrategyRequest(BaseModel):
    description: str = Field(..., min_length=10)
    location: str = Field(..., min_length=2)
    incident_type: Optional[str] = None
    language: Optional[str] = Field(default="english", example="hindi")

class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=5, example="What should I do if police refuse FIR?")
    incident_context: Optional[str] = None

# ============================================================
# SECTION 5: KEYWORD DETECTION ENGINE
# ============================================================

class IncidentDetector:

    @staticmethod
    def detect(description: str) -> Tuple[str, float, bool]:
        """
        Returns: (incident_type, confidence_score, is_emergency)
        Uses weighted multi-pass keyword matching.
        """
        desc_lower = description.lower().strip()
        scores: Dict[str, float] = {}

        # Pass 1: Exact keyword match (flat dictionary O(1) lookup)
        words_and_phrases = IncidentDetector._extract_phrases(desc_lower)
        for phrase in words_and_phrases:
            if phrase in ALL_KEYWORDS_FLAT:
                incident = ALL_KEYWORDS_FLAT[phrase]
                priority = INCIDENT_KEYWORD_MAP[incident]["priority"]
                scores[incident] = scores.get(incident, 0) + priority

        # Pass 2: Partial / fuzzy match for single words
        for kw, incident in ALL_KEYWORDS_FLAT.items():
            if len(kw.split()) == 1 and kw in desc_lower:
                scores[incident] = scores.get(incident, 0) + 2

        # Pass 3: Gemini LLM fallback if no match
        if not scores and gemini_model:
            try:
                categories = list(INCIDENT_KEYWORD_MAP.keys())
                prompt = (
                    f"You are an Indian legal incident classifier.\n"
                    f"Categories: {', '.join(categories)}\n"
                    f"Classify ONLY into one of the above. Reply with ONLY the category name.\n"
                    f"Incident: {description}"
                )
                resp = gemini_model.generate_content(prompt)
                cat = resp.text.strip().lower().replace(" ", "_")
                if cat in INCIDENT_KEYWORD_MAP:
                    return cat, 0.6, cat in EMERGENCY_TYPES
            except Exception as e:
                logger.warning(f"Gemini classification fallback failed: {e}")

        if not scores:
            return "general", 0.3, False

        # Pick best match
        best = max(scores, key=lambda x: scores[x])
        total = sum(scores.values())
        confidence = round(scores[best] / total, 2) if total > 0 else 0.5
        is_emergency = best in EMERGENCY_TYPES

        return best, confidence, is_emergency

    @staticmethod
    def _extract_phrases(text: str) -> List[str]:
        """Extract unigrams, bigrams, and trigrams from text"""
        words = text.split()
        phrases = words.copy()
        phrases += [" ".join(words[i:i+2]) for i in range(len(words)-1)]
        phrases += [" ".join(words[i:i+3]) for i in range(len(words)-2)]
        return phrases

    @staticmethod
    def assess_severity(description: str) -> int:
        """
        Multi-factor severity assessment.
        Returns 1-10.
        """
        desc_lower = description.lower()
        score = 4  # Base score

        critical = ["kill", "murder", "rape", "kidnap", "abduct", "acid",
                    "stab", "knife", "gun", "weapon", "die", "death",
                    "suicide", "life threatening", "unconscious", "bleeding"]
        high =     ["attack", "assault", "beaten", "violence", "theft",
                    "robbery", "fraud", "missing", "child", "fire"]
        medium =   ["threat", "abuse", "harass", "stolen", "scam", "follow",
                    "stalk", "intimidate", "blackmail"]
        low =      ["dispute", "annoy", "disturb", "minor", "verbal", "argument"]

        for w in critical:
            if w in desc_lower:
                score = min(10, score + 3)
        for w in high:
            if w in desc_lower:
                score = min(10, score + 2)
        for w in medium:
            if w in desc_lower:
                score = min(10, score + 1)
        for w in low:
            if w in desc_lower:
                score = max(1, score - 1)

        return max(1, min(10, score))

# ============================================================
# SECTION 6: LOCATION SERVICE
# ============================================================

class LocationService:

    def __init__(self):
        self.geolocator = Nominatim(user_agent="citizen-ai-v3-india")

    def resolve_coords(self, location_str: str) -> Tuple[Optional[float], Optional[float], str]:
        """Returns (lat, lon, address_string)"""
        try:
            parts = [p.strip() for p in location_str.split(",")]
            if len(parts) == 2:
                try:
                    lat, lon = float(parts[0]), float(parts[1])
                    loc = self.geolocator.reverse((lat, lon), language="en", timeout=10)
                    return lat, lon, loc.address if loc else location_str
                except ValueError:
                    pass  # Not a coordinate pair, treat as address

            loc = self.geolocator.geocode(location_str, timeout=10)
            if loc:
                return loc.latitude, loc.longitude, loc.address
        except Exception as e:
            logger.error(f"Geocoding failed for '{location_str}': {e}")

        return None, None, location_str

    def find_nearest_station(self, lat: Optional[float], lon: Optional[float], query: str) -> dict:
        """
        Priority:
        1. Geodesic distance from local police_df CSV
        2. SerpApi local search
        3. Static fallback
        """

        # Priority 1: Local CSV geodesic match
        if lat and lon and not police_df.empty:
            try:
                if {"Latitude", "Longitude"}.issubset(police_df.columns):
                    df = police_df.dropna(subset=["Latitude", "Longitude"])
                    df = df.copy()
                    df["distance_km"] = df.apply(
                        lambda row: geodesic(
                            (lat, lon), (row["Latitude"], row["Longitude"])
                        ).km,
                        axis=1
                    )
                    nearest = df.nsmallest(1, "distance_km").iloc[0]
                    return {
                        "name": nearest.get("Office/Designation", "Police Station"),
                        "address": f"{nearest.get('District/City', '')}, {nearest.get('State', '')}",
                        "phone": str(nearest.get("Contact Number", "100")),
                        "distance_km": round(nearest["distance_km"], 2),
                        "source": "local_database"
                    }
                else:
                    # String-based fallback using query
                    query_lower = query.lower()
                    for _, row in police_df.iterrows():
                        city = str(row.get("District/City", "")).lower()
                        state = str(row.get("State", "")).lower()
                        if any(q in city or q in state for q in query_lower.split(",")):
                            return {
                                "name": row.get("Office/Designation", "Police Station"),
                                "address": f"{row.get('District/City', '')}, {row.get('State', '')}",
                                "phone": str(row.get("Contact Number", "100")),
                                "source": "local_database"
                            }
            except Exception as e:
                logger.warning(f"Local station lookup error: {e}")

        # Priority 2: SerpApi
        if SERPAPI_API_KEY:
            try:
                client = Client(api_key=SERPAPI_API_KEY)
                result = client.search(
                    q=f"police station near {query}",
                    location="India",
                    num=1
                )
                local = result.get("local_results", [])
                if local:
                    r = local[0]
                    return {
                        "name": r.get("title", "Police Station"),
                        "address": r.get("address", query),
                        "phone": r.get("phone", "100"),
                        "gps": r.get("gps_coordinates", {}),
                        "source": "web_search"
                    }
            except Exception as e:
                logger.error(f"SerpApi police station search failed: {e}")

        # Priority 3: Fallback
        return {
            "name": "Your Local Police Station",
            "address": query,
            "phone": "100",
            "emergency": "112",
            "source": "fallback"
        }

# ============================================================
# SECTION 7: LEGAL ENGINE (COMPLAINT GENERATOR)
# ============================================================

class LegalEngine:

    @staticmethod
    def generate_complaint(report: IncidentReport, incident_type: str,
                           station: dict, sections: list) -> str:
        """
        Generates a complete, formal FIR application letter
        following the professional template format.
        """
        now = datetime.now().strftime("%d-%m-%Y")
        
        # Parse date and time
        try:
            dt_obj = datetime.fromisoformat(report.date_time)
            incident_date = dt_obj.strftime("%d-%m-%Y")
            incident_time = dt_obj.strftime("%I:%M %p")
        except Exception:
            incident_date = report.date_time.split("T")[0] if "T" in report.date_time else report.date_time
            incident_time = report.date_time.split("T")[1][:5] if "T" in report.date_time else "Unknown"

        # Format sections
        sections_str = "\n".join(f"       • {s}" for s in sections) if sections else "       • As applicable under IPC/BNS/IT Act"

        # Evidence list
        evidence = report.evidence_available or ["[To be provided]"]
        evidence_str = "\n".join(f"   {chr(9312 + i)}{e}" for i, e in enumerate(evidence[:6]))

        # Subject line based on incident type
        subject_map = {
            "cyber_fraud":       "Cyber Fraud / Unauthorized Financial Transaction",
            "mobile_theft":      "Theft / Snatching of Mobile Phone",
            "domestic_violence": "Domestic Violence / Physical & Mental Cruelty",
            "sexual_harassment": "Sexual Harassment / Stalking",
            "kidnapping":        "Kidnapping / Abduction",
            "assault":           "Physical Assault / Bodily Harm",
            "theft":             "Theft / Robbery / Snatching",
            "police_refusal":    "Non-Registration of FIR by Police",
            "child_abuse":       "Child Abuse / POCSO Violation",
            "missing_person":    "Missing Person Report",
            "property_dispute":  "Property Fraud / Illegal Encroachment",
            "general":           "Criminal Complaint"
        }
        subject = subject_map.get(incident_type, "Criminal Complaint / FIR Request")

        # S/o or D/o line
        relation = ""
        if report.father_or_spouse_name:
            if report.gender.lower() in ["male", "m"]:
                relation = f"S/o {report.father_or_spouse_name}"
            else:
                relation = f"D/o / W/o {report.father_or_spouse_name}"

        complaint = f"""
{now}

To,
The Station House Officer (SHO),
{station.get('name', '[POLICE STATION NAME]')},
{station.get('address', '[CITY], [STATE]')}

Subject: Request for Registration of FIR regarding {subject}

Respected Sir/Madam,

I, {report.name}{f', {relation}' if relation else ''}, aged {report.age} years ({report.gender}),
residing at {report.address or report.location},
bearing mobile number {report.contact or '[CONTACT NUMBER]'}{f' and email {report.email}' if report.email else ''},
respectfully submit the following facts for your kind consideration and immediate action:

1. INCIDENT DATE & TIME:
   The incident occurred on {incident_date} at around {incident_time}.

2. PLACE OF INCIDENT:
   The incident took place at / near {report.location}.

3. BRIEF FACTS OF THE INCIDENT (Chronological):
   {report.description}

4. NATURE OF LOSS / HARM / DAMAGE:
   • Nature: {incident_type.replace('_', ' ').title()}
   • Details: [Please specify amount/items/injury as applicable]
   {"• Evidence preserved: " + ', '.join(report.evidence_available) if report.evidence_available else ""}

5. ACCUSED / SUSPECT DETAILS (if known):
   {report.accused_details or '• Name / Description: Unknown at present'}
   • [Add vehicle number / phone number / social media ID if known]

6. EVIDENCE AVAILABLE (copies attached):
{evidence_str}

7. WITNESS DETAILS (if any):
   {report.witness_details or 'No witnesses known at present'}

8. IMMEDIATE ACTIONS ALREADY TAKEN:
   {report.immediate_actions_taken or '• None taken prior to this complaint'}

In view of the above stated facts, I most humbly request you to kindly:
   (a) Take immediate cognizance of this matter;
   (b) Register a First Information Report (FIR) under the following
       applicable provisions of the Bharatiya Nyaya Sanhita (BNS) / IPC
       and/or Information Technology Act, 2000:

{sections_str}

   (c) Initiate prompt investigation and take necessary legal action
       against the unknown / known accused.

I assure you of my full cooperation throughout the investigation and
undertake to provide any additional information, documents, or assistance
as and when required.

Thanking you,

Yours faithfully,


(Signature)
Name    : {report.name}
Mobile  : {report.contact or '[Phone Number]'}
Email   : {report.email or '[Email Address]'}
Address : {report.address or report.location}

Place   : {report.location.split(',')[0]}
Date    : {now}

---------------------------------------------------------------
LIST OF ENCLOSURES:
{''.join(f'{chr(9312 + i)}{e}' + chr(10) for i, e in enumerate(evidence[:6]))}
---------------------------------------------------------------
        """.strip()

        return complaint


def _get_cache_key(incident_type: str, description: str, city: str) -> str:
    key = f"{incident_type}|{description.strip().lower()}|{city.strip().lower()}"
    # Use a stable hash to persist across process restarts
    return hashlib.sha256(key.encode('utf-8')).hexdigest()


def _get_cached_response(key: str) -> Optional[dict]:
    return AI_CACHE.get(key)


def _save_cached_response(key: str, payload: dict):
    AI_CACHE[key] = payload
    save_json_file(CORE_DIR / "ai_cache.json", AI_CACHE)


def _extract_statutory_references(sections: List[str]) -> List[dict]:
    year_map = {
        "IPC": 1860,
        "CrPC": 1973,
        "IT Act": 2000,
        "DV Act": 2005,
        "POSH Act": 2013,
        "BNS": 2026
    }
    refs = []
    for sec in sections:
        match = re.match(r"([A-Za-z ]+?)\s*(\d+)", sec)
        if match:
            act_key = match.group(1).strip()
            section_num = match.group(2).strip()
            year = year_map.get(act_key, None)
            refs.append({
                "act": act_key,
                "section": section_num,
                "year": year,
                "raw": sec
            })
        else:
            refs.append({"raw": sec})
    return refs


def _find_volunteers(category: str, city: str) -> List[dict]:
    city_lower = (city or "").strip().lower()
    cat_lower = (category or "").strip().lower()
    matches = []
    for v in VOLUNTEERS:
        v_city = v.get("city", "").strip().lower()
        v_cat = v.get("category", "").strip().lower()
        if (v_city == "all" or v_city == city_lower or city_lower in v_city) and (
            v_cat == cat_lower or v_cat == "general" or cat_lower == ""
        ):
            matches.append(v)
    return matches


def build_structured_response(
    report: IncidentReport,
    incident_type: str,
    severity: int,
    is_emergency: bool,
    guide: dict,
    nearest_station: dict,
    web_sources: list,
    complaint_text: str
) -> dict:
    """Builds a 12-section structured response following the requested format."""

    risk_level = "LOW"
    if is_emergency or severity >= 8:
        risk_level = "HIGH"
    elif severity >= 5:
        risk_level = "MEDIUM"

    # 1️⃣ Situation Analysis
    situation = {
        "incident_type": incident_type.replace("_", " ").title(),
        "risk_level": risk_level,
        "reason": (
            f"The description indicates a {incident_type.replace('_', ' ')} incident "
            f"with a severity score of {severity}. "
            f"This may require immediate action to protect your safety and legal rights."
        )
    }

    # 2️⃣ Immediate Actions
    immediate_actions = guide.get("immediate_actions", [])
    helplines = [
        "112 – National Emergency",
        "100 – Police"
    ]

    # Only include additional helplines that are relevant to the incident type
    if incident_type in ["cyber_fraud", "online_fraud", "identity_theft"]:
        helplines.append("1930 – Cybercrime Helpline")

    if incident_type in ["sexual_harassment", "domestic_violence", "child_abuse"]:
        helplines.append("1091 – Women Helpline")

    # Provide legal aid helpline as a general fallback for any non-emergency
    if not is_emergency:
        helplines.append("15100 – Legal Aid")

    # 3️⃣ Safety Guidance
    safety = [
        "Avoid confronting the suspect.",
        "Stay in a crowded, well-lit public place.",
        "Inform nearby security guards or shopkeepers if available."
    ]

    # 4️⃣ Actions After Reaching Safety
    next_steps = guide.get("next_24_hours", [])

    # 5️⃣ Digital & Financial Protection
    digital = []
    if incident_type in ["mobile_theft", "cyber_fraud"]:
        digital = [
            "Block your SIM with your telecom provider immediately.",
            "Block your device IMEI via the CEIR portal: https://ceir.gov.in",
            "Change passwords for banking, UPI, email, and social apps.",
            "Notify your bank and freeze UPI / cards if used on the device."
        ]
        if incident_type == "cyber_fraud":
            digital.append("Report to the National Cyber Crime Portal: https://cybercrime.gov.in")
    else:
        digital = [
            "Keep all digital evidence such as messages, call logs, screenshots.",
            "Do not delete any chat or communication related to the incident."
        ]

    # 6️⃣ Nearby Help
    nearby = {
        "station": nearest_station.get("name"),
        "address": nearest_station.get("address"),
        "phone": nearest_station.get("phone"),
        "distance_km": nearest_station.get("distance_km")
    }

    # 7️⃣ Expected Police Actions (Within 24 Hours)
    police_24 = [
        "Register the FIR and take your statement.",
        "Collect basic details and incident location.",
        "Check for CCTV or witness information.",
        "Inform telecom operators if required (IMEI tracking)."
    ]

    # 8️⃣ Expected Investigation Steps (48 Hours)
    investigation_48 = [
        "Follow up on leads including CCTV and witness statements.",
        "Coordinate with telecom providers for IMEI/SIM tracing.",
        "Identify and question suspects or persons of interest.",
        "Prepare a preliminary report for further action."
    ]

    # 9️⃣ Relevant Legal Sections
    legal_sections = guide.get("legal_support", {}).get("sections", [])
    if not legal_sections:
        legal_sections = ["Consult a lawyer for applicable laws."]

    # Statutory references (section + year)
    statutory_references = _extract_statutory_references(legal_sections)

    # 🔟 Escalation If Police Do Not Respond
    escalation = [
        "Contact the Superintendent of Police (SP) if FIR is not registered.",
        "File a complaint with the District Magistrate.",
        "Submit an application under CrPC Section 156(3) to a Magistrate."
    ]

    # 1️⃣1️⃣ Offline Help Points
    offline_help = [
        "Police stations nearby.",
        "Government hospitals for medical support.",
        "Railway/metro police booths.",
        "Local municipal or administrative offices."
    ]

    # 1️⃣2️⃣ Official Government Resources
    gov_links = [
        {"name": "National Emergency Helpline", "url": "https://112.gov.in"},
        {"name": "National Cybercrime Portal", "url": "https://cybercrime.gov.in"},
        {"name": "CEIR Mobile Blocking", "url": "https://ceir.gov.in"},
        {"name": "India Code Legal Database", "url": "https://www.indiacode.nic.in"},
        {"name": "Bhubaneswar/Cuttack Police Complaint Portal", "url": "https://bhubaneswarcuttackpolice.gov.in/register-your-complaint/"}
    ]

    # Merge web sources (SerpApi + AI sources) and dedupe by URL
    combined_sources = []
    seen_urls = set()
    for src in (web_sources or []) + guide.get("web_sources", []):
        url = (src.get("url") or src.get("link") or "").strip()
        if url and url not in seen_urls:
            seen_urls.add(url)
            combined_sources.append(src)

    # 1️⃣3️⃣ Emergency Warning
    emergency_warning = None
    if is_emergency or risk_level == "HIGH":
        emergency_warning = {
            "alert": "⚠ EMERGENCY DETECTED",
            "message": "Call 112 immediately or move to the nearest public place.",
            "recommended_action": "Don’t remain alone; find a safe, busy location."
        }

    # 1️⃣4️⃣ Professional Police Complaint Draft
    complaint_draft = complaint_text

    # Volunteers (local / category-based)
    volunteers = _find_volunteers(incident_type, report.location)

    return {
        "situation_analysis": situation,
        "immediate_actions": {
            "actions": immediate_actions,
            "emergency_contacts": helplines
        },
        "safety_guidance": safety,
        "next_steps": next_steps,
        "digital_financial_protection": digital,
        "nearby_help": nearby,
        "expected_police_actions_24h": police_24,
        "expected_investigation_48h": investigation_48,
        "legal_sections": legal_sections,
        "statutory_references": statutory_references,
        "escalation_options": escalation,
        "offline_help_points": offline_help,
        "official_resources": gov_links,
        "volunteers": volunteers,
        "emergency_warning": emergency_warning,
        "police_complaint_draft": complaint_draft,
        "web_sources": combined_sources
    }


# ============================================================
# SECTION 8: AI STRATEGY ENGINE
# ============================================================

class AIStrategyEngine:

    @staticmethod
    def generate_basic_strategy(incident_type: str) -> dict:
        """Returns structured guide from victim_help_guides.json merged with ai_response_templates.json"""
        guide = GUIDES.get(incident_type, {})
        template = TEMPLATES.get(incident_type, {})
        
        # Merge guide and template, preferring template for more detailed info
        merged = guide.copy()
        merged.update(template)
        
        if not merged:
            return {
                "description": "Incident type not found in database.",
                "immediate_actions": ["Call 112 for emergency assistance"],
                "next_24_hours": [],
                "next_48_hours": [],
                "legal_support": {},
                "expected_resolution_time": "Unknown"
            }
        return merged

    @staticmethod
    def generate_advanced_strategy(incident_type: str, description: str, city: str) -> dict:
        """Gemini-powered 360° legal strategy (BNS 2026 compliant) with sources"""
        if not gemini_model:
            return {"error": "AI model unavailable. Please refer to basic guide."}

        # Get template for context
        template = TEMPLATES.get(incident_type, {})
        template_context = json.dumps(template, indent=2)[:2000] if template else "No specific template available."

        prompt = f"""
You are a Senior Legal Strategist and Victim Rights Expert in India.
Use Bharatiya Nyaya Sanhita (BNS) 2026, BNSS, BSA, and existing acts.

CASE:
- Incident Type: {incident_type}
- Description: {description}
- Location: {city}

TEMPLATE CONTEXT:
{template_context}

Generate a JSON response (NO markdown, pure JSON) with EXACTLY these keys:

{{
  "risk_mitigation": ["Step 1...", "Step 2...", "Step 3..."],
  "legal_remedies": ["BNS Section XX - Description", "IT Act XX..."],
  "evidence_checklist": ["Item 1", "Item 2", "Item 3", "Item 4", "Item 5"],
  "escalation_matrix": [
    {{"step": 1, "authority": "SHO", "action": "...", "timeline": "Immediate"}},
    {{"step": 2, "authority": "SP/DCP", "action": "...", "timeline": "48 hours"}},
    {{"step": 3, "authority": "Magistrate", "action": "CrPC 156(3)", "timeline": "If SP fails"}},
    {{"step": 4, "authority": "High Court", "action": "Writ Petition", "timeline": "Final resort"}}
  ],
  "helplines": ["112 - Emergency", "1930 - Cybercrime", "1091 - Women"],
  "expected_outcome": "Brief description of likely resolution timeline and outcome",
  "victim_rights": ["Right 1", "Right 2", "Right 3"],
  "sources": ["URL1 - Description", "URL2 - Description"]
}}
"""
        try:
            resp = gemini_model.generate_content(prompt)
            text = resp.text.strip()
            # Clean possible markdown fencing
            text = re.sub(r"^```json\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Strategy JSON parse failed: {e}\nRaw: {text[:500]}")
            return {"error": "Strategy generation returned invalid format.", "raw": text[:500]}
        except Exception as e:
            logger.error(f"Strategy generation failed: {e}")
            return {"error": str(e)}

    @staticmethod
    def enhance_guide_with_ai(incident_type: str, description: str, city: str, guide: dict) -> dict:
        """Use Gemini + web sources to fill missing guide sections.

        Caches AI-enhanced guide results so repeated queries return the same output
        and to avoid repeated API calls for identical cases.
        """
        if not gemini_model:
            return guide

        cache_key = _get_cache_key(incident_type, description, city)
        cached = _get_cached_response(cache_key)
        if cached and isinstance(cached, dict):
            # Merge cached AI output into the guide without overwriting existing data
            for k, v in cached.items():
                if not guide.get(k):
                    guide[k] = v
            return guide

        missing = []
        for key in ["immediate_actions", "next_24_hours", "next_48_hours", "legal_support", "expected_resolution_time"]:
            if not guide.get(key):
                missing.append(key)

        if not missing:
            return guide

        try:
            ai = AIStrategyEngine.generate_advanced_strategy(incident_type, description, city)
            if isinstance(ai, dict):
                # Populate missing keys
                if "risk_mitigation" in ai and "immediate_actions" in missing:
                    guide["immediate_actions"] = ai["risk_mitigation"]
                if "legal_remedies" in ai and "legal_support" in missing:
                    guide["legal_support"] = {"sections": ai.get("legal_remedies", [])}
                if "evidence_checklist" in ai and "next_24_hours" in missing:
                    guide.setdefault("next_24_hours", []).extend(ai.get("evidence_checklist", []))
                if "expected_outcome" in ai and "expected_resolution_time" in missing:
                    guide["expected_resolution_time"] = ai.get("expected_outcome")

                # Add sources to guide for transparency
                guide["web_sources"] = ai.get("sources", [])

                # Cache the enhanced guide so we can reuse it for identical queries
                _save_cached_response(cache_key, guide)

        except Exception as e:
            logger.warning(f"Failed to enhance guide with AI: {e}")

        return guide

    @staticmethod
    def get_web_intelligence(incident_type: str, city: str) -> List[dict]:
        """Get relevant web resources via SerpApi"""
        if not SERPAPI_API_KEY:
            return []

        results = []
        queries = [
            f"how to file FIR for {incident_type} in {city} India 2026",
            f"government portal {incident_type} victim help India",
            f"free legal aid {incident_type} {city} NGO India"
        ]
        try:
            client = Client(api_key=SERPAPI_API_KEY)
            for q in queries:
                res = client.search(q=q, location="India", num=2)
                for r in res.get("organic_results", []):
                    results.append({
                        "title": r.get("title"),
                        "url": r.get("link"),
                        "snippet": r.get("snippet", "")[:200]
                    })
        except Exception as e:
            logger.error(f"Web intelligence failed: {e}")

        return results[:6]  # Return top 6

    @staticmethod
    def answer_legal_question(question: str, context: Optional[str] = None) -> str:
        """RAG-style Q&A using local data + Gemini AI, with templates"""
        if not gemini_model:
            return "AI model unavailable. Please call 15100 for free legal aid."

        # Local data context
        local_context = ""
        if context and context in GUIDES:
            guide = GUIDES[context]
            local_context = json.dumps(guide, indent=2)[:1500]
        if context and context in TEMPLATES:
            template = TEMPLATES[context]
            local_context += "\n\nTEMPLATE:\n" + json.dumps(template, indent=2)[:1500]

        prompt = f"""
You are a legal aid assistant helping Indian citizens.
Answer the following question clearly in simple English.
Be specific, practical, and mention exact Indian laws/helplines if relevant.
If about FIR refusal, mention CrPC/BNSS Section 154 and 156(3).

{f"Context from database: {local_context}" if local_context else ""}

Question: {question}

Answer in 3-5 clear sentences. Include one relevant helpline number and any relevant URLs from context.
"""
        try:
            resp = gemini_model.generate_content(prompt)
            return resp.text.strip()
        except Exception as e:
            return f"Could not generate answer: {e}. Please call 15100 for free legal aid."

# ============================================================
# SECTION 9: FASTAPI APP SETUP
# ============================================================

app = FastAPI(
    title="Citizen Assistance AI Platform",
    description="Advanced Legal & Emergency Assistance for Indian Citizens | BNS 2026 | v3.0",
    version="3.0.0",
    contact={"name": "Citizen AI Support", "email": "support@citizenai.in"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info("=" * 60)
    logger.info("Citizen Assistance AI Platform v3.0 - STARTED")
    logger.info(f"Guides loaded      : {len(GUIDES)} incident types")
    logger.info(f"Keywords tracked   : {len(ALL_KEYWORDS_FLAT)}")
    logger.info(f"Police stations    : {len(police_df)} records")
    logger.info(f"Emergency types    : {', '.join(EMERGENCY_TYPES)}")
    logger.info("=" * 60)

# ============================================================
# SECTION 10: API ENDPOINTS
# ============================================================

@app.post("/api/v3/report", tags=["Core"])
async def report_incident(report: IncidentReport):
    """
    MAIN ENDPOINT:
    Accepts incident report → Detects type → Retrieves guide →
    Finds nearest station → Generates complaint letter →
    Returns complete assistance package.
    """
    try:
        # Step 1: Classify incident
        incident_type, confidence, is_emergency = IncidentDetector.detect(report.description)
        severity = report.severity or IncidentDetector.assess_severity(report.description)
        
        logger.info(f"Report: type={incident_type}, confidence={confidence}, emergency={is_emergency}")

        # Step 2: Location
        loc_service = LocationService()
        lat, lon, addr = loc_service.resolve_coords(report.location)
        nearest_station = loc_service.find_nearest_station(lat, lon, addr)

        # Step 3: Get guide from database and enhance with AI if incomplete
        guide = AIStrategyEngine.generate_basic_strategy(incident_type)
        guide = AIStrategyEngine.enhance_guide_with_ai(incident_type, report.description, addr, guide)
        legal_support = guide.get("legal_support", {})
        legal_sections = legal_support.get("sections", ["Consult legal expert"])

        # Step 4: Generate complaint letter
        complaint = LegalEngine.generate_complaint(report, incident_type, nearest_station, legal_sections)

        # Step 5: Get resolution time from CSV
        resolution_days = 30
        if not resolution_df.empty and "incident_type" in resolution_df.columns:
            mask = resolution_df["incident_type"] == incident_type
            if mask.any():
                resolution_days = int(resolution_df[mask]["average_resolution_days"].iloc[0])

        # Step 6: Emergency detection
        emergency_alert = None
        if is_emergency or severity >= 8:
            emergency_alert = {
                "alert": "⚠️ EMERGENCY SITUATION DETECTED",
                "action": "Call 112 IMMEDIATELY or move to nearest safe/public place",
                "hotlines": ["112 - Emergency", "100 - Police", "1091 - Women Helpline"]
            }

        # Step 7: Get web intelligence for sources
        web_intel = AIStrategyEngine.get_web_intelligence(incident_type, addr.split(",")[0].strip() if addr else report.location)

        # Step 8: Build final response
        case_id = f"CASE-{datetime.now().strftime('%Y%m%d%H%M')}-{uuid4().hex[:6].upper()}"

        structured = build_structured_response(
            report=report,
            incident_type=incident_type,
            severity=severity,
            is_emergency=is_emergency,
            guide=guide,
            nearest_station=nearest_station,
            web_sources=web_intel,
            complaint_text=complaint
        )

        logger.info(f"Structured response keys: {list(structured.keys())}")
        logger.info(f"Structured response size: {len(str(structured))} bytes")

        response_body = {
            "case_id": case_id,
            "timestamp": datetime.now().isoformat(),
            "structured_advice": structured,


            "incident_analysis": {
                "type": incident_type,
                "confidence": confidence,
                "severity_score": severity,
                "is_emergency": is_emergency,
                "description": guide.get("description", "")
            },

            "emergency_alert": emergency_alert,

            "immediate_guidance": {
                "overview": guide.get("description"),
                "immediate_actions": guide.get("immediate_actions", []),
                "evidence_checklist": guide.get("evidence_checklist", [])
            },

            "action_timeline": {
                "next_24_hours": guide.get("next_24_hours", []),
                "next_48_hours": guide.get("next_48_hours", [])
            },

            "legal_context": {
                "sections": legal_sections,
                "courts": legal_support.get("courts", "Local Magistrate Court"),
                "compensation": legal_support.get("compensation", ""),
                "official_resources": legal_support.get("official_resources", {})
            },

            "nearest_station": nearest_station,

            "escalation_path": {
                "step_1": "Station House Officer (SHO) - File FIR immediately",
                "step_2": "Superintendent of Police (SP) - If FIR refused within 48h",
                "step_3": "Judicial Magistrate - Application under BNSS Section 156(3)",
                "step_4": "High Court Writ Petition - Final legal remedy"
            },

            "support": {
                "offline_help": guide.get("offline_help_points", []),
                "helplines": legal_support.get("official_resources", {}).get("helplines", [
                    "112 - Emergency", "100 - Police", "1091 - Women Helpline",
                    "1930 - Cybercrime", "15100 - Legal Aid"
                ])
            },

            "web_sources": web_intel,

            "generated_complaint": complaint,

            "resolution_estimate": {
                "estimated_days": resolution_days,
                "note": guide.get("expected_resolution_time", "")
            },

            "disclaimer": DISCLAIMERS.get("disclaimers", {}).get(
                incident_type,
                DISCLAIMERS.get("default_disclaimer", "This is AI-generated guidance. Please consult a legal expert.")
            )
        }
        
        logger.info(f"Response body prepared with {len(response_body)} top-level keys")
        return JSONResponse(content=response_body)

    except Exception as e:
        logger.error(f"Report endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@app.post("/api/v3/strategy", tags=["Advanced"])
async def get_advanced_strategy(request: StrategyRequest):
    """
    ADVANCED ENDPOINT:
    Generates 360° legal strategy using Gemini AI + SerpApi web intelligence.
    """
    try:
        incident_type = request.incident_type or IncidentDetector.detect(request.description)[0]

        loc_service = LocationService()
        _, _, addr = loc_service.resolve_coords(request.location)
        city = addr.split(",")[0].strip() if addr else request.location

        # Parallel strategy generation
        ai_strategy = AIStrategyEngine.generate_advanced_strategy(incident_type, request.description, city)
        web_intel = AIStrategyEngine.get_web_intelligence(incident_type, city)
        basic_guide = AIStrategyEngine.generate_basic_strategy(incident_type)

        return {
            "incident_type": incident_type,
            "location": city,
            "ai_strategy": ai_strategy,
            "web_intelligence": web_intel,
            "database_guide": {
                "immediate_actions": basic_guide.get("immediate_actions", []),
                "legal_sections": basic_guide.get("legal_support", {}).get("sections", [])
            }
        }

    except Exception as e:
        logger.error(f"Strategy endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v3/ask", tags=["Q&A"])
async def ask_legal_question(request: QuestionRequest):
    """
    Q&A ENDPOINT:
    Answers legal questions using local data + Gemini AI.
    """
    try:
        answer = AIStrategyEngine.answer_legal_question(request.question, request.incident_context)
        return {
            "question": request.question,
            "answer": answer,
            "disclaimer": "This is AI-generated guidance. For critical matters, consult a lawyer. Free legal aid: 15100"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v3/detect", tags=["Utility"])
async def detect_incident_type(description: str):
    """
    QUICK DETECTION ENDPOINT:
    Detect incident type from a short description.
    """
    incident_type, confidence, is_emergency = IncidentDetector.detect(description)
    severity = IncidentDetector.assess_severity(description)
    return {
        "incident_type": incident_type,
        "confidence": confidence,
        "is_emergency": is_emergency,
        "severity": severity
    }


@app.get("/api/v3/station", tags=["Utility"])
async def find_station(lat: Optional[float] = None, lon: Optional[float] = None, location: Optional[str] = None):
    """Find nearest police station by coordinates or location name."""
    loc_service = LocationService()
    if not lat and location:
        lat, lon, addr = loc_service.resolve_coords(location)
    return loc_service.find_nearest_station(lat, lon, location or "India")


@app.get("/api/v3/all-stations", tags=["Data"])
async def get_all_stations():
    """Get all police stations for mapping."""
    stations = police_df.to_dict('records')
    return [{"name": s.get("Station Name", ""), "lat": s.get("Latitude", 0), "lon": s.get("Longitude", 0), "address": s.get("Address", ""), "phone": s.get("Phone", "")} for s in stations]


@app.get("/api/v3/volunteers", tags=["Data"])
async def get_volunteers():
    """Get all volunteers for mapping."""
    # Add coordinates based on city
    city_coords = {
        "Cuttack": {"lat": 20.4625, "lon": 85.8830},
        "Bhubaneswar": {"lat": 20.2961, "lon": 85.8245},
        "All": {"lat": 20.2961, "lon": 85.8245}  # Default to Bhubaneswar
    }
    enhanced_volunteers = []
    for vol in VOLUNTEERS:
        coords = city_coords.get(vol.get("city", "All"), city_coords["All"])
        enhanced_volunteers.append({
            **vol,
            "lat": coords["lat"],
            "lon": coords["lon"]
        })
    return enhanced_volunteers


@app.get("/api/v3/schemes", tags=["Data"])
async def get_schemes(incident_type: Optional[str] = None):
    """Get relevant government schemes."""
    if schemes_df.empty:
        return {"message": "No schemes data available", "data": []}
    if incident_type and "incident_type" in schemes_df.columns:
        filtered = schemes_df[schemes_df["incident_type"] == incident_type]
        return {"data": filtered.to_dict("records")}
    return {"data": schemes_df.to_dict("records")}


@app.get("/api/v3/laws", tags=["Data"])
async def get_laws(incident_type: Optional[str] = None):
    """Get relevant laws and sections."""
    if laws_df.empty:
        return {"message": "No laws data available", "data": []}
    if incident_type and "incident_type" in laws_df.columns:
        filtered = laws_df[laws_df["incident_type"] == incident_type]
        return {"data": filtered.to_dict("records")}
    return {"data": laws_df.to_dict("records")}


@app.get("/api/v3/keywords", tags=["Utility"])
async def get_keywords():
    """Returns all supported incident types and their detection keywords."""
    return {
        incident: {
            "keyword_count": len(data["keywords"]),
            "is_emergency": data.get("emergency", False),
            "sample_keywords": data["keywords"][:8]
        }
        for incident, data in INCIDENT_KEYWORD_MAP.items()
    }


@app.get("/health", tags=["System"])
async def health_check():
    """System health check."""
    return {
        "status": "online",
        "version": "3.0.0",
        "guides_loaded": len(GUIDES),
        "keywords_tracked": len(ALL_KEYWORDS_FLAT),
        "police_stations": len(police_df),
        "gemini_ready": gemini_model is not None,
        "serpapi_ready": bool(SERPAPI_API_KEY),
        "timestamp": datetime.now().isoformat()
    }


# ============================================================
# SECTION 11: ENTRY POINT
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )