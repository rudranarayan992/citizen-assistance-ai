import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Circle, ImageOverlay } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import axios from 'axios';

const API_BASE = 'http://localhost:8000';

const MapPage = () => {
  const [policeStations, setPoliceStations] = useState([]);
  const [volunteers, setVolunteers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const stationsRes = await axios.get(`${API_BASE}/api/v3/all-stations`);
        setPoliceStations(stationsRes.data);

        const volunteersRes = await axios.get(`${API_BASE}/api/v3/volunteers`);
        setVolunteers(volunteersRes.data);
      } catch (error) {
        console.error('Error fetching data:', error);
      }
      setLoading(false);
    };
    fetchData();
  }, []);

  if (loading) return <div>Loading map...</div>;

  return (
    <div style={{ height: '100vh', width: '100%', position: 'relative' }}>
      {/* Legend */}
      <div style={{
        position: 'absolute',
        top: '10px',
        right: '10px',
        background: 'white',
        padding: '10px',
        border: '1px solid #ccc',
        borderRadius: '5px',
        zIndex: 1000
      }}>
        <h4>Crime Zones</h4>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '5px' }}>
          <div style={{ width: '20px', height: '20px', backgroundColor: 'red', opacity: 0.3, marginRight: '10px' }}></div>
          <span>High Crime</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '5px' }}>
          <div style={{ width: '20px', height: '20px', backgroundColor: 'yellow', opacity: 0.3, marginRight: '10px' }}></div>
          <span>Medium Crime</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <div style={{ width: '20px', height: '20px', backgroundColor: 'green', opacity: 0.2, marginRight: '10px' }}></div>
          <span>Safe Zone</span>
        </div>
      </div>
      <MapContainer center={[20.2961, 85.8245]} zoom={8} style={{ height: '100%', width: '100%' }}>
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />
        {policeStations.map((station, idx) => (
          <React.Fragment key={idx}>
            <Marker position={[station.lat, station.lon]}>
              <Popup>
                <strong>{station.name}</strong><br />
                {station.address}<br />
                Phone: {station.phone}
              </Popup>
            </Marker>
            {/* Safe zone: green circle around police station */}
            <Circle
              center={[station.lat, station.lon]}
              radius={1000} // 1km radius
              pathOptions={{ color: 'green', fillColor: 'green', fillOpacity: 0.2 }}
            />
          </React.Fragment>
        ))}
        {/* Crime-based zones for Odisha */}
        {/* Yellow zones: Medium crime areas */}
        <Circle
          center={[20.2961, 85.8245]} // Bhubaneswar
          radius={3000} // 3km radius
          pathOptions={{ color: 'yellow', fillColor: 'yellow', fillOpacity: 0.3 }}
        />
        <Circle
          center={[20.4625, 85.8830]} // Cuttack
          radius={3000}
          pathOptions={{ color: 'yellow', fillColor: 'yellow', fillOpacity: 0.3 }}
        />
        {/* Add image overlay for Odisha safety map if provided */}
        {/* <ImageOverlay url="path/to/odisha_safety_map.png" bounds={[[17.7800, 81.3700], [22.5700, 87.5300]]} /> */}
        {volunteers.map((vol, idx) => (
          <Marker key={idx} position={[vol.lat, vol.lon]}>
            <Popup>
              <strong>Volunteer: {vol.name}</strong><br />
              {vol.role}<br />
              {vol.city}<br />
              Phone: {vol.phone}<br />
              Email: {vol.email}
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
};

export default MapPage;