import json

paths = [
    "c:/Users/rudra/Desktop/citizen-assistance-ai/docs/ai_response_templates.json",
    "c:/Users/rudra/Desktop/citizen-assistance-ai/data/core/incident_types.json",
]

for p in paths:
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(p, "OK")
    except Exception as e:
        print(p, "ERROR", e)

# show mobile_theft template names/counts
with open(paths[0], "r", encoding="utf-8") as f:
    d = json.load(f)
print("mobile_theft present in templates?", "mobile_theft" in d)
print("mobile_theft immediate steps", len(d["mobile_theft"]["immediate_steps_0_24_hours"]))

with open(paths[1], "r", encoding="utf-8") as f:
    d2 = json.load(f)
ids = [item["id"] for item in d2["incident_legal_mapping"]]
print("mobile_theft present in incident types?", "mobile_theft" in ids)
print("mobile_theft emergency?", next(i for i in d2["incident_legal_mapping"] if i["id"] == "mobile_theft")["emergency"])
