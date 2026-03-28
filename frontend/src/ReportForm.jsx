import React, { useState } from 'react';
import axios from 'axios';

const API_BASE = 'http://157.41.240.85:8003';
const steps = [
  'Incident',
  'Details',
  'Personal',
  'Review'
];

const ReportForm = () => {
  const [formData, setFormData] = useState({
    description: '',
    date_time: '',
    location: '',
    gender: '',
    age: '',
    name: '',
    severity: 5
  });
  const [step, setStep] = useState(0);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleNext = () => setStep(step + 1);
  const handleBack = () => setStep(step - 1);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE}/api/v3/report`, formData);
      setResult(response.data);
      setStep(steps.length);
    } catch (error) {
      alert('Error submitting report: ' + (error.response?.data?.detail || error.message));
    }
    setLoading(false);
  };

  const Stepper = () => (
    <div className="stepper">
      {steps.map((label, idx) => (
        <span key={label} className={step === idx ? 'active' : ''}>
          ● {label}
        </span>
      ))}
    </div>
  );

  return (
    <div className="app">
      <div className="design-credit">design by <span>rudra</span></div>
      <header>
        <div className="flag-banner">
          <div className="flag-saffron"></div>
          <div className="flag-white"></div>
          <div className="flag-green"></div>
        </div>
        <h1>Jan Suraksha</h1>
        <p className="subtitle">National Citizen Safety Platform</p>
      </header>
      <Stepper />
      {step === 0 && (
        <div className="step-form">
          <h2>What happened with you?</h2>
          <textarea name="description" value={formData.description} onChange={handleChange} required placeholder="Describe your incident..." />
          <button onClick={handleNext} disabled={!formData.description}>Next</button>
        </div>
      )}
      {step === 1 && (
        <div className="step-form">
          <h2>Incident Details</h2>
          <input name="date_time" type="datetime-local" value={formData.date_time} onChange={handleChange} required placeholder="Date & Time" />
          <input name="location" placeholder="Location" value={formData.location} onChange={handleChange} required />
          <button onClick={handleBack}>Back</button>
          <button onClick={handleNext} disabled={!formData.date_time || !formData.location}>Next</button>
        </div>
      )}
      {step === 2 && (
        <div className="step-form">
          <h2>Personal Info</h2>
          <input name="name" placeholder="Name" value={formData.name} onChange={handleChange} required />
          <input name="age" type="number" placeholder="Age" value={formData.age} onChange={handleChange} required />
          <select name="gender" value={formData.gender} onChange={handleChange} required>
            <option value="">Select Gender</option>
            <option value="Male">Male</option>
            <option value="Female">Female</option>
            <option value="Transgender">Transgender</option>
          </select>
          <button onClick={handleBack}>Back</button>
          <button onClick={handleNext} disabled={!formData.name || !formData.age || !formData.gender}>Next</button>
        </div>
      )}
      {step === 3 && (
        <form onSubmit={handleSubmit} className="step-form">
          <h2>Review & Submit</h2>
          <ul>
            <li><strong>Incident:</strong> {formData.description}</li>
            <li><strong>Date & Time:</strong> {formData.date_time}</li>
            <li><strong>Location:</strong> {formData.location}</li>
            <li><strong>Name:</strong> {formData.name}</li>
            <li><strong>Age:</strong> {formData.age}</li>
            <li><strong>Gender:</strong> {formData.gender}</li>
          </ul>
          <button onClick={handleBack}>Back</button>
          <button type="submit" disabled={loading}>{loading ? 'Submitting...' : 'Submit Report'}</button>
        </form>
      )}
      {step === steps.length && result && (
        <div className="result">
          <h2>Report Submitted</h2>
          <p><strong>Case ID:</strong> {result.case_id}</p>
          {!result.structured_advice && (
            <div style={{color: 'red', padding: '10px', border: '1px solid red', marginBottom: '10px'}}>
              ⚠️ Warning: structured_advice is missing from response. Response keys: {Object.keys(result).join(', ')}
            </div>
          )}
          {result.structured_advice?.situation_analysis && (
            <div className="structured-section">
              <h3>Situation Analysis</h3>
              <p><strong>Incident Type:</strong> {result.structured_advice.situation_analysis.incident_type}</p>
              <p><strong>Risk Level:</strong> {result.structured_advice.situation_analysis.risk_level}</p>
              <p>{result.structured_advice.situation_analysis.reason}</p>
            </div>
          )}
          {result.emergency_alert && (
            <div className="emergency-alert">
              <strong>{result.emergency_alert.alert}</strong>
              <p>{result.emergency_alert.action}</p>
              <ul>
                {result.emergency_alert.hotlines.map((h, i) => <li key={i}>{h}</li>)}
              </ul>
            </div>
          )}
          {result.structured_advice?.immediate_actions && (
            <div className="structured-section">
              <h3>Immediate Actions (0-1 Hour)</h3>
              <ul>
                {result.structured_advice.immediate_actions.actions.map((item, i) => <li key={i}>{item}</li>)}
              </ul>
              <h4>Emergency Contacts</h4>
              <ul>
                {result.structured_advice.immediate_actions.emergency_contacts.map((item, i) => <li key={i}>{item}</li>)}
              </ul>
            </div>
          )}
          {result.structured_advice?.safety_guidance && (
            <div className="structured-section">
              <h3>Safety Guidance</h3>
              <ul>
                {result.structured_advice.safety_guidance.map((item, i) => <li key={i}>{item}</li>)}
              </ul>
            </div>
          )}
          {result.structured_advice?.next_steps && (
            <div className="structured-section">
              <h3>Actions After Reaching Safety</h3>
              <ul>
                {result.structured_advice.next_steps.map((item, i) => <li key={i}>{item}</li>)}
              </ul>
            </div>
          )}
          {result.structured_advice?.digital_financial_protection && (
            <div className="structured-section">
              <h3>Digital & Financial Protection</h3>
              <ul>
                {result.structured_advice.digital_financial_protection.map((item, i) => <li key={i}>{item}</li>)}
              </ul>
            </div>
          )}
          {result.structured_advice?.nearby_help && (
            <div className="structured-section">
              <h3>Nearby Help</h3>
              <p><strong>Police Station:</strong> {result.structured_advice.nearby_help.station}</p>
              <p><strong>Address:</strong> {result.structured_advice.nearby_help.address}</p>
              <p><strong>Phone:</strong> {result.structured_advice.nearby_help.phone}</p>
              {result.structured_advice.nearby_help.distance_km && (
                <p><strong>Distance:</strong> {result.structured_advice.nearby_help.distance_km} km</p>
              )}
            </div>
          )}
          {result.structured_advice?.expected_police_actions_24h && (
            <div className="structured-section">
              <h3>Expected Police Actions (Within 24 Hours)</h3>
              <ul>
                {result.structured_advice.expected_police_actions_24h.map((item, i) => <li key={i}>{item}</li>)}
              </ul>
            </div>
          )}
          {result.structured_advice?.expected_investigation_48h && (
            <div className="structured-section">
              <h3>Expected Investigation Steps (48 Hours)</h3>
              <ul>
                {result.structured_advice.expected_investigation_48h.map((item, i) => <li key={i}>{item}</li>)}
              </ul>
            </div>
          )}
          {result.structured_advice?.legal_sections && (
            <div className="structured-section">
              <h3>Relevant Legal Sections</h3>
              <ul>
                {result.structured_advice.legal_sections.map((item, i) => <li key={i}>{item}</li>)}
              </ul>
            </div>
          )}
          {result.structured_advice?.statutory_references && (
            <div className="structured-section">
              <h3>Statutory References</h3>
              <ul>
                {result.structured_advice.statutory_references.map((ref, i) => (
                  <li key={i}>
                    {ref.act ? `${ref.act} Section ${ref.section} (${ref.year || 'year unknown'})` : ref.raw}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {result.structured_advice?.escalation_options && (
            <div className="structured-section">
              <h3>Escalation If Police Do Not Respond</h3>
              <ul>
                {result.structured_advice.escalation_options.map((item, i) => <li key={i}>{item}</li>)}
              </ul>
            </div>
          )}
          {result.structured_advice?.offline_help_points && (
            <div className="structured-section">
              <h3>Offline Help Points</h3>
              <ul>
                {result.structured_advice.offline_help_points.map((item, i) => <li key={i}>{item}</li>)}
              </ul>
            </div>
          )}
          {result.structured_advice?.volunteers && result.structured_advice.volunteers.length > 0 && (
            <div className="structured-section volunteer-section">
              <h3>Local Volunteer Support</h3>
              <p>Community volunteers available to assist with your case:</p>
              <div className="volunteer-list">
                {result.structured_advice.volunteers.map((vol, i) => (
                  <div key={i} className="volunteer-card">
                    <p><strong>{vol.name}</strong> - {vol.role}</p>
                    <p><em>{vol.category.replace('_', ' ')}</em></p>
                    <p>📍 {vol.city}</p>
                    <p>☎️ <a href={`tel:${vol.phone}`}>{vol.phone}</a></p>
                    <p>📧 <a href={`mailto:${vol.email}`}>{vol.email}</a></p>
                    {vol.notes && <p style={{ fontSize: '0.9em', color: '#666' }}>{vol.notes}</p>}
                  </div>
                ))}
              </div>
            </div>
          )}
          {result.structured_advice?.official_resources && (
            <div className="structured-section">
              <h3>Official Government Resources</h3>
              <ul>
                {result.structured_advice.official_resources.map((item, i) => <li key={i}><a href={item.url} target="_blank" rel="noopener noreferrer">{item.name}</a></li>)}
              </ul>
            </div>
          )}
          {result.structured_advice?.emergency_warning && (
            <div className="emergency-alert">
              <strong>{result.structured_advice.emergency_warning.alert}</strong>
              <p>{result.structured_advice.emergency_warning.message}</p>
              <p>{result.structured_advice.emergency_warning.recommended_action}</p>
            </div>
          )}
          {result.structured_advice?.web_sources && (
            <div className="structured-section">
              <h3>Web Sources & Resources</h3>
              <ul>
                {result.structured_advice.web_sources.map((source, i) => <li key={i}><a href={source.url} target="_blank" rel="noopener noreferrer">{source.title}</a> - {source.snippet}</li>)}
              </ul>
            </div>
          )}
          {result.structured_advice?.police_complaint_draft && (
            <div className="structured-section">
              <h3>Professional Police Complaint Draft</h3>
              <pre>{result.structured_advice.police_complaint_draft}</pre>
              <button onClick={() => {
                const blob = new Blob([result.structured_advice.police_complaint_draft], { type: 'text/plain' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'police_complaint_draft.txt';
                a.click();
                URL.revokeObjectURL(url);
              }}>Download Complaint Draft</button>
            </div>
          )}
          <p><em>{result.disclaimer}</em></p>
        </div>
      )}
    </div>
  );
};

export default ReportForm;