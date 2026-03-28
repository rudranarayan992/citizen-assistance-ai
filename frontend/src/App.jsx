import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import ReportForm from './ReportForm';
import MapPage from './MapPage';
import './App.css';

function App() {
  return (
    <Router>
      <div className="app">
        <nav style={{ padding: '10px', background: '#f0f0f0' }}>
          <Link to="/" style={{ marginRight: '20px' }}>Report Incident</Link>
          <Link to="/map">Safety Map</Link>
        </nav>
        <Routes>
          <Route path="/" element={<ReportForm />} />
          <Route path="/map" element={<MapPage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;