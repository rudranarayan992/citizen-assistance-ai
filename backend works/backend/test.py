import requests

data = {
    'name': 'Test User',
    'age': 30,
    'gender': 'male',
    'description': 'I was assaulted on the street',
    'location': '13.0827,80.2707',
    'date_time': '2026-03-15T10:00',
    'severity': 7
}
response = requests.post('http://localhost:8000/report_incident', json=data)
print('Status:', response.status_code)
if response.status_code == 200:
    res = response.json()
    print('Incident Type:', res['incident_type'])
    print('Severity:', res['severity_score'])
    print('Legal Sections:', res['legal_sections'])
    print('Helpline:', res['helpline_suggestion'])
    print('Case ID:', res['case_id'])
    print('Template preview:', res['complaint_template'][:200] + '...')
else:
    print('Error:', response.text)