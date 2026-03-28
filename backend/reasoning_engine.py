
import json
import re
import os
import time
import uuid
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from enum import Enum
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class RiskLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EMERGENCY = "EMERGENCY"

class IncidentType(Enum):
    CYBER_FRAUD = "cyber_fraud"
    MOBILE_THEFT = "mobile_theft"
    DOMESTIC_VIOLENCE = "domestic_violence"
    SEXUAL_HARASSMENT = "sexual_harassment"
    KIDNAPPING = "kidnapping"
    POLICE_REFUSAL = "police_refusal"
    OTHER = "other"
    UNKNOWN = "unknown"


class IncidentKeywords:
    """Incident type keyword mapping with priority weights"""
    
    INCIDENT_KEYWORDS = {
        IncidentType.CYBER_FRAUD.value: {
            "keywords": [
                "upi fraud", "online scam", "money stolen", "bank fraud", 
                "otp scam", "cyber crime", "phishing", "cheated online",
                "transaction unauthorized", "hack my account", "scam call",
                "fake website", "refunded money not received", "investment fraud"
            ],
            "weight": 8,
            "priority_keywords": ["upi fraud", "money stolen", "bank fraud", "hack"]
        },
        
        IncidentType.MOBILE_THEFT.value: {
            "keywords": [
                "phone stolen", "mobile stolen", "lost phone", "phone theft",
                "stole my mobile", "snatched phone", "mobile missing",
                "phone snatching", "bag stolen with phone", "theft on metro"
            ],
            "weight": 9,
            "priority_keywords": ["stolen", "theft", "snatched"]
        },
        
        IncidentType.DOMESTIC_VIOLENCE.value: {
            "keywords": [
                "husband beating", "family violence", "domestic abuse",
                "in-laws torture", "wife beaten", "abused by family",
                "thrown out of house", "forced to leave home", "dowry harassment"
            ],
            "weight": 9,
            "priority_keywords": ["beating", "torture", "violence", "abuse"]
        },
        
        IncidentType.SEXUAL_HARASSMENT.value: {
            "keywords": [
                "stalking", "molestation", "sexual harassment",
                "eve teasing", "followed by stranger", "groped",
                "unwanted touching", "obscene messages", "cyber stalking"
            ],
            "weight": 9,
            "priority_keywords": ["stalking", "molestation", "harassment", "groped"]
        },
        
        IncidentType.KIDNAPPING.value: {
            "keywords": [
                "kidnap", "abducted", "taken away", "forced into car",
                "missing person", "held captive", "cannot contact anyone",
                "threatened to kill", "locked in room"
            ],
            "weight": 10,
            "priority_keywords": ["kidnap", "abduct", "captured", "threatened to kill"]
        },
        
        IncidentType.POLICE_REFUSAL.value: {
            "keywords": [
                "police refused fir", "police not helping", "police corruption",
                "police demanding bribe", "fir not registered",
                "police sent me away", "no action taken"
            ],
            "weight": 7,
            "priority_keywords": ["refused", "not helping", "corruption", "bribe"]
        }
    }

    EMERGENCY_KEYWORDS = {
        "help", "emergency", "danger", "dangerous", "life threat",
        "kidnap", "abduct", "attack", "assault", "violent",
        "murder", "rape", "suicide", "threaten life", "immediately need help",
        "saving myself", "save me", "kill me", "hurt me"
    }

    DANGER_LEVEL_KEYWORDS = {
        "EMERGENCY": ["kill", "murder", "knife", "gun", "suicide", "life threatened"],
        "HIGH": ["attack", "assault", "violent", "beat", "hit", "chasing", "following"],
        "MEDIUM": ["threatening", "harassing", "uncomfortable", "unsafe"],
        "LOW": ["annoying", "minor", "disturbed", "unpleasant"]
    }


class CaseFileManager:
    """Manages case files and evidence"""
    
    def __init__(self, storage_path: str = "./case_files"):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
    
    def generate_case_id(self) -> str:
        """Generate unique case ID"""
        return f"CASE-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    
    def save_case_file(self, case_data: dict) -> str:
        """Save case file to disk"""
        case_id = self.generate_case_id()
        filename = f"{case_id}.json"
        filepath = os.path.join(self.storage_path, filename)
        
        case_data["case_metadata"] = {
            "case_id": case_id,
            "created_at": datetime.now().isoformat(),
            "version": "2.0"
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(case_data, f, indent=2, ensure_ascii=False)
        
        return case_id
    
    def save_complaint_letter(self, content: str, case_id: str) -> str:
        """Save complaint letter as text file"""
        filename = f"{case_id}_complaint.txt"
        filepath = os.path.join(self.storage_path, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filepath


class EvidenceTracker:
    """Track and validate evidence collection"""
    
    EVIDENCE_CATEGORIES = {
        "cyber_fraud": [
            "Transaction Screenshot", "Bank Statement", "UPI App Records",
            "Chat/Messages with Scammer", "Email Correspondence",
            "Call Logs", "Phishing URL", "Scammer Phone Number",
            "KYC Documents", "Police FIR Copy"
        ],
        "mobile_theft": [
            "IMEI Number", "Phone Box Photo", "Purchase Invoice",
            "FIR Copy", "SIM Card Details", "Find My Device Status",
            "CEIR Blocking Proof", "Phone Insurance Policy",
            "CCTV Footage Request", "Last Known Location"
        ],
        "domestic_violence": [
            "Medical Report", "Injury Photos", "Hospital Bills",
            "Threat Messages", "Audio Recordings", "Witness Statements",
            "Property Documents", "Children's Details", "Shelter Information",
            "Protection Officer Contact", "Legal Aid Documentation"
        ],
        "sexual_harassment": [
            "Screenshot of Messages", "Chat History", "Social Media Posts",
            "Voice Recordings", "Video Evidence", "Witness Statements",
            "Medical Examination Report", "CCTV Footage",
            "Workplace ICC Complaint", "Police Complaint Acknowledgment"
        ]
    }
    
    @classmethod
    def get_required_evidence(cls, incident_type: str) -> List[str]:
        """Get list of recommended evidence for incident type"""
        return cls.EVIDENCE_CATEGORIES.get(incident_type, [])
    
    @classmethod
    def create_evidence_checklist(cls, incident_type: str) -> str:
        """Create formatted evidence checklist"""
        evidence_list = cls.get_required_evidence(incident_type)
        lines = ["📋 EVIDENCE COLLECTION CHECKLIST:", "=" * 50]
        for i, evidence in enumerate(evidence_list, 1):
            lines.append(f"  ☐ {i}. {evidence}")
        lines.append("=" * 50)
        return "\n".join(lines)


class IncidentAnalyzer:
    """Advanced incident detection and analysis"""
    
    def __init__(self):
        self.keyword_map = IncidentKeywords.INCIDENT_KEYWORDS
        self.emergency_keywords = IncidentKeywords.EMERGENCY_KEYWORDS
        self.danger_levels = IncidentKeywords.DANGER_LEVEL_KEYWORDS
    
    def detect_incidents(self, user_message: str) -> List[Tuple[IncidentType, float]]:
        """Detect multiple incidents with confidence scores"""
        message_lower = user_message.lower()
        detected = []
        
        for incident_type, config in self.keyword_map.items():
            score = 0
            weight = config["weight"]
            
            # Check regular keywords
            for keyword in config["keywords"]:
                if keyword in message_lower:
                    score += 2
            
            # Bonus for priority keywords
            for keyword in config.get("priority_keywords", []):
                if keyword in message_lower:
                    score += 3
            
            if score > 0:
                confidence = min(score / 10, 1.0)  # Normalize to 0-1
                detected.append((IncidentType(incident_type), confidence))
        
        # Sort by confidence
        detected.sort(key=lambda x: x[1], reverse=True)
        return detected
    
    def is_emergency(self, user_message: str) -> bool:
        """Check if situation is emergency"""
        message_lower = user_message.lower()
        return any(keyword in message_lower for keyword in self.emergency_keywords)
    
    def assess_risk_level(self, user_message: str) -> RiskLevel:
        """Assess risk level based on message content"""
        message_lower = user_message.lower()
        
        # Check danger levels in reverse priority
        for level, keywords in reversed(list(self.danger_levels.items())):
            if any(keyword in message_lower for keyword in keywords):
                return RiskLevel(level)
        
        return RiskLevel.LOW
    
    def extract_entities(self, user_message: str) -> dict:
        """Extract key entities from user message"""
        entities = {
            "amount": None,
            "location": None,
            "date": None,
            "time": None,
            "contact_number": None,
            "bank_name": None,
            "upii_id": None
        }
        
        # Amount extraction
        amount_pattern = r'\b₹?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:rupees?|rs|amount)?'
        amount_match = re.search(amount_pattern, user_message, re.IGNORECASE)
        if amount_match:
            entities["amount"] = amount_match.group(1).replace(',', '')
        
        # Location patterns
        location_patterns = [
            r'in\s+(?:(?:.*?\b(?:chennai|mumbai|delhi|bangalore|kolkata|hyderabad|pune|jaipur|ahmedabad)\b.*?))',
            r'at\s+(?:.*)?(?:metro|bus|train|station|market|road)'
        ]
        for pattern in location_patterns:
            match = re.search(pattern, user_message, re.IGNORECASE)
            if match:
                entities["location"] = match.group(0)
                break
        
        # Date patterns
        date_patterns = [
            r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
            r'\b(\d{1,2}\s+\w+\s+\d{4})\b'
        ]
        for pattern in date_patterns:
            match = re.search(pattern, user_message)
            if match:
                entities["date"] = match.group(1)
                break
        
        # Time patterns
        time_pattern = r'\b(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm|Hours?))\b'
        match = re.search(time_pattern, user_message, re.IGNORECASE)
        if match:
            entities["time"] = match.group(1)
        
        # Phone number
        phone_pattern = r'\b\d{10}\b'
        match = re.search(phone_pattern, user_message)
        if match:
            entities["contact_number"] = match.group(0)
        
        # Bank names
        banks = ['hdfc', 'sbi', 'icici', 'axis', 'kotak', 'indusind', 'yes bank']
        for bank in banks:
            if bank.lower() in user_message.lower():
                entities["bank_name"] = bank
                break
        
        # UPI ID
        upi_pattern = r'\b[a-z0-9._-]+\@[a-z]+\b'
        match = re.search(upi_pattern, user_message.lower())
        if match:
            entities["upii_id"] = match.group(0)
        
        return entities


class ResponseGenerator:
    """Generate structured, professional responses"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.analyzer = IncidentAnalyzer()
        self.case_manager = CaseFileManager()
        self.evidence_tracker = EvidenceTracker()
        self.guides = self._load_victim_guides()

    def _load_victim_guides(self) -> dict:
        """Load guidance templates from data/core/victim_help_guides.json"""
        try:
            root = Path(__file__).resolve().parents[1]
            guide_path = root / "data" / "core" / "victim_help_guides.json"
            with open(guide_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    
    def _build_prompt(self, user_message: str, incident_types: List[IncidentType]) -> str:
        """Build optimized prompt for LLM"""
        
        top_incident = incident_types[0][0].value if incident_types else "unknown"
        
        guide = self.guides.get(top_incident, {})
        guide_section = ""
        if guide:
            immediate = guide.get("immediate_actions", [])
            next24 = guide.get("next_24_hours", [])
            legal = guide.get("legal_sections", [])

            guide_section = (
                "\n---\nDATABASE GUIDANCE (from victim_help_guides.json):\n"
                f"Incident: {guide.get('incident_name', top_incident)}\n"
                "Immediate Actions:\n"
                + "\n".join([f"- {a}" for a in immediate])
                + "\n\nNext 24 Hours:\n"
                + "\n".join([f"- {a}" for a in next24])
                + "\n\nLegal Sections: "
                + (", ".join(legal) if legal else "N/A")
                + "\n---\n"
            )

        return f"""You are an expert AI Legal Emergency Assistant for India with expertise in criminal law, police procedures, and victim assistance.

ANALYZE THIS CASE FIRST:
<case_analysis>
User Message: \"{user_message}\"
Detected Incident Type: {top_incident}
Risk Assessment: CRITICAL - Analyze urgency carefully
{guide_section}

THINKING REQUIRED (Internal):
1. What exactly happened? Extract facts only.
2. Is user in immediate physical danger? (YES/NO)
3. What are the top 3 critical actions they must take NOW?
4. Which specific helplines apply to this exact scenario?
5. What Indian laws specifically protect them in this situation?
6. How would you customize generic advice for THIS specific victim's needs?
</case_analysis>

OUTPUT REQUIREMENTS:
Provide EXACTLY structured guidance following this template precisely:

[SECTION_FORMAT_START]
-----------------------------------------------------
<thinking>
[Your detailed internal analysis here - be thorough but concise]
</thinking>

1. Situation Analysis

✓ Incident Type: [Be specific based on user details]
✓ Risk Level: [EMERGENCY/HIGH/MEDIUM/LOW]
✓ Why: [Brief explanation based on their exact words]

-----------------------------------------------------

2. Immediate Actions (0–1 Hour)

[Provide 3-5 SPECIFIC steps based on their situation, NOT generic]
✓ Include exact helpline numbers with context
✓ Mention WHERE to go if possible (nearest public place/policestation)
✓ If cyber: mention specific apps/services to contact

-----------------------------------------------------

3. Actions After Reaching Safety

[Next 24-hour priorities]
• What documents to gather IMMEDIATELY
• Which authorities to approach first
• Medical attention if needed

-----------------------------------------------------

4. Digital & Financial Protection (If Relevant)

[Only include if cyber/fraud/theft applies]
• Specific portal URLs: https://ceir.gov.in, https://cybercrime.gov.in
• Bank actions with reference numbers to request
• Password/PIN change sequence

-----------------------------------------------------

5. Expected Police Actions (Within 24 Hours)

[Fixed standard police obligations - use exactly this text]
• FIR Registration obligation under CrPC Section 154
• Evidence preservation responsibilities
• Victim statement recording rights

-----------------------------------------------------

6. Expected Investigation Actions (Within 48 Hours)

[Technical investigation expectations]
• Digital forensics (for cyber)
• IMEI blocking verification (for theft)
• CCTV collection timeline
• Bank coordination requirements

-----------------------------------------------------

7. Relevant Legal Sections

[Specific sections with punishment ranges]
IPC/IT Act Section [XX] - [Brief description] - Punishment: [Range]

Official Law Source: https://www.indiacode.nic.in

-----------------------------------------------------

8. Escalation if Police Do Not Act

[Fixed escalation hierarchy - use exactly this text]
Day 1: Contact Station House Officer (SHO) with written complaint and demand FIR registration
Day 2: Approach Police Superintendent/Dy.SP with escalation request
Day 3+: File application under CrPC 156(3) in Magistrate Court for police inaction

-----------------------------------------------------

9. Offline Help Options

[Places accessible without internet]
✓ Police Stations
✓ Government Hospitals
✓ Railway Station Security
✓ Bus Terminal Control Rooms
✓ District Collector Office

-----------------------------------------------------

10. Official Resources (WITH VERIFIED LINKS)

[Only include relevant portals for this case type]
• National Portal Name | https://official-gov-link
• Helpline Number | Available Hours
• State-Specific Portal (if applicable)

-----------------------------------------------------

11. Emergency Warning (IF APPLICABLE)

⚠️ EMERGENCY DETECTED - TAKE ACTION NOW
[Customize warning based on their specific danger indicators]

-----------------------------------------------------

12. Professional Police Complaint Letter Template

[COMPLETE TEMPLATE PRE-FILLED with extracted case details where available]

Format Instructions:
• Use ALL CAPS for placeholders like [DATE], [NAME], etc.
• Fill in ANY details you extracted from user message
• Mark clearly which parts still need manual filling
• Maintain formal legal tone throughout
• Include specific IPC/IT Act sections based on their case

-----------------------------------------------------

CRITICAL GUIDELINES:
✓ NEVER give generic template answers - always tailor to user's exact words
✓ Include AT LEAST one specific helpline that matches their incident type
✓ If medical/emergency - put 112 or 1091 FIRST
✓ For cyber fraud - mention fund recovery chances vs time elapsed
✓ For domestic violence - mention shelter homes and women's commission
✓ For theft - emphasize IMEI blocking within 48 hours window
✓ Always explain WHY each step matters
✓ Keep language SIMPLE for panicked victims
✓ Include follow-up expectations so they know what to anticipate

Now provide your complete response below:
"""
    def generate_response(self, user_message: str, session_id: str = None) -> dict:
        """Generate complete structured response"""
        
        try:
            # Step 1: Analyze incident
            detected_incidents = self.analyzer.detect_incidents(user_message)
            is_emergency = self.analyzer.is_emergency(user_message)
            risk_level = self.analyzer.assess_risk_level(user_message)
            extracted_entities = self.analyzer.extract_entities(user_message)
            
            # Build prompt
            prompt = self._build_prompt(user_message, detected_incidents)
            
            # Get LLM response
            response = self.model.generate_content(prompt)
            raw_text = response.text.strip()
            
            # Remove thinking block
            guidance_text = re.sub(r'<thinking>.*?</thinking>\s*\n*', '', raw_text, flags=re.DOTALL).strip()
            
            # Create structured response
            case_data = {
                "session_id": session_id or str(uuid.uuid4()),
                "user_message": user_message,
                "guidance_text": guidance_text,
                "analysis": {
                    "detected_incidents": [(i.value, c) for i, c in detected_incidents],
                    "is_emergency": is_emergency,
                    "risk_level": risk_level.value,
                    "extracted_entities": extracted_entities,
                    "timestamp": datetime.now().isoformat()
                },
                "evidence_checklist": self.evidence_tracker.create_evidence_checklist(detected_incidents[0][0].value if detected_incidents else "other")
            }
            
            # Save case file for record-keeping
            if session_id:
                case_file_path = self.case_manager.save_case_file(case_data)
                case_data["case_file_saved"] = True
                case_data["case_file_path"] = case_file_path
            
            return {
                "status": "success",
                "data": case_data,
                "metadata": {
                    "response_generated_at": datetime.now().isoformat(),
                    "model_used": "gemini-1.5-flash",
                    "processing_time_ms": 0  # Would track actual time in production
                }
            }
            
        except Exception as e:
            # Fallback to keyword-based response
            return {
                "status": "error",
                "error_message": str(e),
                "fallback_response": self._generate_fallback_response(user_message)
            }
    
    def _generate_fallback_response(self, user_message: str) -> str:
        """Generate basic response if LLM fails"""
        
        detected = self.analyzer.detect_incidents(user_message)
        top_incident = detected[0][0].value if detected else "unknown"
        is_emergency = self.analyzer.is_emergency(user_message)
        
        response_parts = []
        
        if is_emergency:
            response_parts.append("\u26A0\ufe0f EMERGENCY DETECTED\n")
            response_parts.append("Call 112 IMMEDIATELY or go to nearest police station.\n")
            response_parts.append("This is a critical safety alert.\n\n")
        
        response_parts.append("INCIDENT TYPE DETECTED: " + top_incident.upper() + "\n")
        response_parts.append("=" * 50 + "\n\n")
        
        response_parts.append("IMMEDIATE ACTIONS:\n")
        response_parts.append("1. Ensure personal safety\n")
        response_parts.append("2. Contact appropriate helpline (112/1091/1930)\n")
        response_parts.append("3. Visit nearest police station to file complaint\n")
        response_parts.append("4. Collect and preserve all evidence\n\n")
        
        response_parts.append("IMPORTANT HELPLINES:\n")
        response_parts.append("\u2022 112 - National Emergency Number\n")
        response_parts.append("\u2022 1091 - Women Helpline\n")
        response_parts.append("\u2022 1930 - Cybercrime Helpline\n")
        response_parts.append("\u2022 100 - Police\n\n")
        
        response_parts.append("For detailed guidance, please try again or contact\n")
        response_parts.append("your local police station directly.\n")
        
        return "\n".join(response_parts)


class CommandInterface:
    """Interactive command-line interface"""
    
    def __init__(self):
        self.generator = ResponseGenerator(api_key=os.getenv('GEMINI_API_KEY'))
        self.session_active = False
        self.current_session = None
    
    def display_banner(self):
        """Display application banner"""
        banner = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║     \u25B6\u25B6\u25B6 LEGAL EMERGENCY ASSISTANCE SYSTEM v2.0 \u25B6\u25B6\u25B6           ║
║                                                           ║
║     India's AI-Powered Crime Victim Support System        ║
║                                                           ║
║     \u260E\ufe0f Call 112 for Immediate Emergencies                 ║
║     \ud83d\udee1\ufe0f Available 24/7 for Legal Guidance                   ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
"""
        print(banner)
    
    def display_menu(self):
        """Display main menu options"""
        menu = """
MAIN MENU:
----------
[1] Start New Case Consultation
[2] View Recent Case Files
[3] Search Case History
[4] Quick Helpline Numbers
[5] Download Complaint Templates
[6] Exit System
"""
        print(menu)
    
    def quick_helplines(self):
        """Display quick helpline references"""
        helplines = """
\ud83d\udcf1 QUICK HELPLINE REFERENCE CARD
====================================

\u26A0\ufe0f  EMERGENCY (All Cases)
---------------------------
112     - National Emergency Number (24/7)
100     - Police General Helpline

\ud83d\udc69 WOMEN'S PROTECTION
-----------------------
1091    - Women Helpline (Toll-Free)
181     - Integrated Women's Helpline
7827170170 - NCW Helpline (National Commission for Women)

\ud83d\udcb3 CYBER CRIME
---------------
1930    - Cybercrime Helpline (24/7)
https://cybercrime.gov.in - Report Online

\ud83d\udcf1 PHONE THEFT
---------------
112     - Police Emergency
14422   - CEIR IMEI Helpline
https://ceir.gov.in - Block IMEI Online

\ud83d\udcac CHILD SUPPORT
------------------
1098    - Child Helpline (24/7)
1091    - Also covers child protection cases

\ud83d\udcbc BANKING FRAUD
-----------------
Bank Customer Care (check your card)
14448   - Banking Ombudsman Helpline
https://cms.rbi.org.in - RBI Grievance Portal

\ud83c\udfdb LEGAL AID
------------
15100   - NALSA Free Legal Aid
https://nalsa.gov.in - Legal Services Authority

\ud83e\udd1d HUMAN RIGHTS
----------------
State Human Rights Commission
National Human Rights Commission

====================================
\u26a0\ufe0f In Life-Threatening Danger: CALL 112 NOW!
====================================
"""
        print(helplines)
    
    def start_consultation(self):
        """Start new consultation session"""
        print("\n" + "=" * 60)
        print("NEW CASE CONSULTATION")
        print("=" * 60)
        print("\nPlease describe your situation in detail.")
        print("Include: What happened, when, where, amounts/items involved,")
        print("any suspect details, and actions already taken.")
        print("\nType your message below (type 'quit' to exit):\n")
        
        while True:
            user_input = input("> ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            
            if not user_input:
                continue
            
            # Process query
            print("\n" + "-" * 60)
            print("ANALYZING YOUR SITUATION...")
            print("-" * 60)
            print("This may take 10-20 seconds...\n")
            
            result = self.generator.generate_response(user_input)
            
            if result["status"] == "success":
                data = result["data"]
                
                # Display risk level prominently
                risk_color = {
                    "EMERGENCY": "\u001b[31m",  # Red
                    "HIGH": "\u001b[33m",      # Yellow
                    "MEDIUM": "\u001b[36m",     # Cyan
                    "LOW": "\u001b[32m"          # Green
                }.get(data["analysis"]["risk_level"], "\u001b[39m")
                
                print(f"\n\u26a0\ufe0f RISK LEVEL: {risk_color}{data['analysis']['risk_level']}\u001b[0m")
                
                if data["analysis"]["is_emergency"]:
                    print("\n" + "\u001b[91m" + "*" * 60 + "\u001b[0m")
                    print("\u001b[91m\u26a0\ufe0f EMERGENCY SITUATION DETECTED\u001b[0m")
                    print("\u001b[91mCALL 112 IMMEDIATELY OR SEEK HELP NOW!\u001b[0m")
                    print("\u001b[91m*" * 60 + "\u001b[0m\n")
                
                # Display guidance
                print("\n" + "=" * 60)
                print("YOUR PERSONALIZED GUIDANCE:")
                print("=" * 60 + "\n")
                print(data["guidance_text"])
                
                # Display evidence checklist
                print("\n" + "=" * 60)
                print(data["evidence_checklist"])
                print("=" * 60)
                
                # Ask if they want to save
                save_choice = input("\nWould you like to save this consultation? (y/n): ").lower()
                if save_choice == 'y':
                    print(f"\nCase saved successfully!")
                    print("Keep this conversation for future reference.")
                
                # Additional actions
                additional = input("\nDo you need: (1) Complaint Letter PDF  (2) Next Steps  (3) Done: ")
                if additional == '1':
                    print("\nComplaint letter will be generated in document format...")
                    # This would integrate with pdf generation library
                elif additional == '2':
                    print("\nAdditional next steps would appear here...")
            else:
                print("\nError processing your request.")
                print(result.get("fallback_response", ""))
            
            print("\n" + "-" * 60)
            continue_query = input("\nEnter another query or type 'quit': ").strip()
            if continue_query.lower() in ['quit', 'exit', 'q']:
                break
    
    def run(self):
        """Run the main application loop"""
        self.display_banner()
        
        while True:
            self.display_menu()
            choice = input("Select option (1-6): ").strip()
            
            if choice == '1':
                self.start_consultation()
            elif choice == '2':
                print("\nView recent cases feature coming soon...")
            elif choice == '3':
                print("\nSearch functionality coming soon...")
            elif choice == '4':
                self.quick_helplines()
                input("\nPress Enter to continue...")
            elif choice == '5':
                print("\nDownload templates feature coming soon...")
            elif choice == '6':
                print("\nExiting system. Stay safe!")
                break
            else:
                print("\nInvalid option. Please try again.")


def main():
    """Main entry point"""
    app = CommandInterface()
    app.run()


if __name__ == "__main__":
    main()