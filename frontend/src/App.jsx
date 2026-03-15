import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

const API_BASE = 'http://localhost:8000'; // Adjust if backend port differs

function App() {
  const [formData, setFormData] = useState({
    name: '',
    age: '',
    gender: '',
    description: '',
    location: '',
    date_time: '',
    severity: 5
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState('report'); // 'report', 'track'

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE}/report_incident`, formData);
      setResult(response.data);
      setView('result');
    } catch (error) {
      console.error(error);
      alert('Error submitting report: ' + (error.response?.data?.detail || error.message));
    }
    setLoading(false);
  };

  const handleTrack = async () => {
    const caseId = prompt('Enter Case ID');
    if (caseId) {
      try {
        const response = await axios.get(`${API_BASE}/case_tracker/${caseId}`);
        alert(JSON.stringify(response.data, null, 2));
      } catch (error) {
        alert('Case not found');
      }
    }
  };

  return (
    <div className="app">
      <header>
        <h1>Citizen Assistance AI Platform</h1>
        <nav>
          <button onClick={() => setView('report')}>Report Incident</button>
          <button onClick={handleTrack}>Track Case</button>
        </nav>
      </header>
      {view === 'report' && (
        <form onSubmit={handleSubmit} className="report-form">
          <h2>Report an Incident</h2>
          <input name="name" placeholder="Name" value={formData.name} onChange={handleChange} required />
          <input name="age" type="number" placeholder="Age" value={formData.age} onChange={handleChange} required />
          <select name="gender" value={formData.gender} onChange={handleChange} required>
            <option value="">Select Gender</option>
            <option value="Male">Male</option>
            <option value="Female">Female</option>
            <option value="Other">Other</option>
          </select>
          <textarea name="description" placeholder="Incident Description" value={formData.description} onChange={handleChange} required />
          <input name="location" placeholder="Location (lat,lon)" value={formData.location} onChange={handleChange} required />
          <input name="date_time" type="datetime-local" value={formData.date_time} onChange={handleChange} required />
          <input name="severity" type="number" min="1" max="10" placeholder="Severity (1-10)" value={formData.severity} onChange={handleChange} />
          <button type="submit" disabled={loading}>{loading ? 'Submitting...' : 'Submit Report'}</button>
        </form>
      )}
      {view === 'result' && result && (
        <div className="result">
          <h2>Report Submitted</h2>
          <p><strong>Case ID:</strong> {result.case_id}</p>
          <p><strong>Incident Type:</strong> {result.incident_type}</p>
          <p><strong>Severity:</strong> {result.severity_score}</p>
          <h3>Immediate Steps</h3>
          <ul>
            {result.immediate_steps.map((step, i) => <li key={i}>{step}</li>)}
          </ul>
          <h3>Nearest Police Station</h3>
          <p>{result.nearest_police_station.name}</p>
          <p>{result.nearest_police_station.address}</p>
          <p>Phone: {result.nearest_police_station.phone}</p>
          <p>Email: {result.nearest_police_station.email}</p>
          <h3>Expected Response (24-48h)</h3>
          <ul>
            {result.expected_response_24_48h.map((resp, i) => <li key={i}>{resp}</li>)}
          </ul>
          <h3>Escalation Steps</h3>
          <ul>
            {result.escalation_steps.map((step, i) => <li key={i}>{step}</li>)}
          </ul>
          <p><strong>Timeline Estimate:</strong> {result.timeline_estimate_days} days</p>
          <h3>Complaint Template</h3>
          <pre>{result.complaint_template}</pre>
          <button onClick={() => {
            const blob = new Blob([result.complaint_template], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'complaint_template.txt';
            a.click();
            URL.revokeObjectURL(url);
          }}>Download Template</button>
          <p><em>{result.disclaimer}</em></p>
        </div>
      )}
    </div>
  );
}

export default App;