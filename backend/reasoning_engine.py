import json
import re
import google.generativeai as genai

# Gemini API setup
GEMINI_API_KEY = "AIzaSyBSUOUtWf9DwTJqoZjoGgUhBHtRaE-LKqM"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Load knowledge base
with open("../data/core/victim_help_guides.json", "r", encoding="utf-8") as f:
    GUIDES = json.load(f)


# Keywords used to detect incidents
INCIDENT_KEYWORDS = {
    "cyber_fraud": [
        "upi fraud",
        "online scam",
        "money stolen",
        "bank fraud",
        "otp scam"
    ],

    "mobile_theft": [
        "phone stolen",
        "mobile stolen",
        "lost phone",
        "phone theft"
    ],

    "domestic_violence": [
        "husband beating",
        "family violence",
        "domestic abuse"
    ],

    "sexual_harassment": [
        "stalking",
        "molestation",
        "sexual harassment"
    ],

    "kidnapping": [
        "kidnap",
        "abducted",
        "someone tried to kidnap me",
        "forced into car"
    ]
}


EMERGENCY_KEYWORDS = [
    "help",
    "danger",
    "kidnap",
    "abduct",
    "attack",
    "threat"
]


# Keywords used to detect incidents
INCIDENT_KEYWORDS = {
    "cyber_fraud": [
        "upi fraud",
        "online scam",
        "money stolen",
        "bank fraud",
        "otp scam"
    ],

    "mobile_theft": [
        "phone stolen",
        "mobile stolen",
        "lost phone",
        "phone theft"
    ],

    "domestic_violence": [
        "husband beating",
        "family violence",
        "domestic abuse"
    ],

    "sexual_harassment": [
        "stalking",
        "molestation",
        "sexual harassment"
    ],

    "kidnapping": [
        "kidnap",
        "abducted",
        "someone tried to kidnap me",
        "forced into car"
    ]
}


EMERGENCY_KEYWORDS = [
    "help",
    "danger",
    "kidnap",
    "abduct",
    "attack",
    "threat"
]


def detect_incident(user_message):
    """Detect incident type based on keywords"""

    message = user_message.lower()

    for incident, keywords in INCIDENT_KEYWORDS.items():
        for word in keywords:
            if word in message:
                return incident

    return "unknown"


def detect_emergency(user_message):
    """Detect if the situation is an emergency"""

    message = user_message.lower()

    for word in EMERGENCY_KEYWORDS:
        if word in message:
            return True

    return False


def generate_response(user_message):
    """Main AI reasoning function using Gemini"""

    prompt = f"""
You are an AI Legal Emergency Assistance System designed to help citizens in India during emergencies, crimes, and legal incidents.

Your task is to analyze the user's message and generate clear, structured guidance to help the victim understand the situation and take the correct actions.

Always prioritize:
• Safety
• Government procedures
• Verified official resources
• Clear step-by-step guidance

Include official Indian government portals, helpline numbers, and legal references whenever possible.

Always structure the response in the following format.

-----------------------------------------------------

1. Situation Analysis

Analyze the user's message and determine what incident may have occurred.

Examples:
• kidnapping attempt
• cyber fraud
• phone theft
• domestic violence
• sexual harassment
• police refusing to register FIR

Also determine the risk level:

LOW  
MEDIUM  
HIGH  
EMERGENCY

Explain briefly why the situation is classified this way.

-----------------------------------------------------

2. Immediate Actions (0–1 Hour)

Provide the most important safety steps the victim must take immediately.

Examples:

• Move to a safe public location  
• Seek help from nearby people  
• Contact emergency services  

Include official emergency numbers:

112 – National Emergency Number  
100 – Police  
1091 – Women Helpline  
1098 – Child Helpline  
1930 – Cybercrime Helpline  

-----------------------------------------------------

3. Actions After Reaching Safety

Explain the next steps the victim should take after reaching safety.

Examples:

• Visit nearest police station  
• File a First Information Report (FIR)  
• Provide evidence to investigators  
• Seek medical help if necessary  

-----------------------------------------------------

4. Digital & Financial Protection (if relevant)

If the case involves phone theft, cybercrime, or identity theft, explain digital safety actions.

Examples:

• Block SIM card through telecom provider  
• Block device IMEI through government CEIR portal  
• Freeze UPI or banking services  
• Change important passwords  

Include official resources such as:

CEIR Portal  
https://ceir.gov.in

National Cybercrime Reporting Portal  
https://cybercrime.gov.in

-----------------------------------------------------

5. Expected Police Actions (Within 24 Hours)

Explain what authorities are expected to do within the first day.

Examples:

• Register FIR  
• Record victim statement  
• Start investigation  
• Collect CCTV evidence  
• Notify district control room  

-----------------------------------------------------

6. Expected Investigation Actions (Within 48 Hours)

Explain possible actions authorities may take within 48 hours.

Examples:

• Track mobile IMEI  
• Analyze bank transactions  
• Contact telecom providers  
• Identify suspects  

-----------------------------------------------------

7. Relevant Legal Sections

List relevant Indian laws when applicable.

Examples:

IPC Section 363 – Kidnapping  
IPC Section 379 – Theft  
IPC Section 420 – Fraud  
IT Act Section 66D – Online cheating  

For legal references include official law source:

India Code  
https://www.indiacode.nic.in

-----------------------------------------------------

8. Escalation if Police Do Not Act

Explain what the victim can do if authorities do not respond.

Examples:

• Contact Superintendent of Police (SP)  
• Submit complaint to District Magistrate  
• File petition under CrPC Section 156(3)  
• Approach State Human Rights Commission  

-----------------------------------------------------

9. Offline Help Options

If the victim has no internet or phone, suggest safe places where help can be obtained.

Examples:

• Police stations  
• Government hospitals  
• Railway police offices  
• Bus station security desks  
• Government administrative offices  

-----------------------------------------------------

10. Official Resources

Always provide useful official government resources when relevant.

Examples:

National Cybercrime Portal  
https://cybercrime.gov.in

Emergency Helpline  
https://112.gov.in

CEIR Mobile Blocking Portal  
https://ceir.gov.in

India Code Legal Database  
https://www.indiacode.nic.in

-----------------------------------------------------

11. Emergency Warning (if situation is dangerous)

If the user message suggests immediate danger, show this alert:

⚠ EMERGENCY DETECTED

Call 112 immediately or seek help at the nearest public place.

-----------------------------------------------------

12. Professional Police Complaint Draft

Automatically generate a professional complaint letter that the victim can submit to the police.

The letter must include:

• Date  
• Victim description  
• Incident summary  
• Request for FIR registration  
• Polite formal language  

-----------------------------------------------------

Important Instructions

• Focus on helping the victim immediately.
• Provide practical steps.
• Use clear structured sections.
• Always include official government resources where relevant.
• Assume the victim may be scared and needs simple guidance.
• Do not provide vague answers.

Now analyze the user's message and generate guidance.

User message: {user_message}
"""

    try:
        response = model.generate_content(prompt)
        guidance_text = response.text.strip()

        # Parse the response into structured format
        sections = guidance_text.split("---------------------------------------------")
        structured_response = {
            "user_message": user_message,
            "guidance": guidance_text
        }

        # Try to extract emergency if present
        if "EMERGENCY DETECTED" in guidance_text:
            structured_response["emergency_mode"] = True
        else:
            structured_response["emergency_mode"] = False

        return structured_response

    except Exception as e:
        print(f"Gemini response failed: {e}")
        # Fallback to keyword-based
        incident = detect_incident(user_message)
        emergency = detect_emergency(user_message)

        response = {
            "user_message": user_message,
            "incident_detected": incident,
            "emergency_mode": emergency
        }

        if incident in GUIDES:
            guide = GUIDES[incident]
            response["guidance"] = {
                "incident_name": guide["incident_name"],
                "description": guide["description"],
                "immediate_actions": guide["immediate_actions"],
                "next_24_hours": guide.get("next_24_hours", []),
                "next_48_hours": guide.get("next_48_hours", []),
                "legal_support": guide.get("legal_support", {}),
                "expected_resolution_time": guide.get("expected_resolution_time", "")
            }
        else:
            response["guidance"] = {
                "message": "Unable to detect incident type. Please contact emergency services if you are in danger."
            }

        return response


# Demo test
if __name__ == "__main__":

    test_message = input("Describe your situation: ")

    result = generate_response(test_message)

    print("\nAI RESPONSE\n")
    print(json.dumps(result, indent=2))