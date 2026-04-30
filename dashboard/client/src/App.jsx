import React, { useState, useEffect } from 'react';
import { io } from 'socket.io-client';
import { Activity, Cpu, Hash, Clock, Box } from 'lucide-react';
import './App.css';

const socket = io('http://' + window.location.hostname + ':8080');

function App() {
  const [registers, setRegisters] = useState([]);
  const [connected, setConnected] = useState(false);
  const [manifest, setManifest] = useState(null);

  useEffect(() => {
    socket.on('connect', () => setConnected(true));
    socket.on('disconnect', () => setConnected(false));
    
    socket.on('registers', (data) => {
      setRegisters(data);
    });

    // マニフェストの取得
    fetch('http://' + window.location.hostname + ':8080/api/manifest')
      .then(res => res.json())
      .then(data => setManifest(data))
      .catch(err => console.error('Failed to fetch manifest', err));

    return () => {
      socket.off('connect');
      socket.off('disconnect');
      socket.off('registers');
    };
  }, []);

  return (
    <div className="dashboard-container">
      <header>
        <div className="logo">VirtualFPGALab <span style={{fontSize: '0.8rem', fontWeight: 300, opacity: 0.6}}>v2.0</span></div>
        <div className="status-badge">
          <div className={`status-dot ${connected ? 'active' : ''}`}></div>
          {connected ? 'LIVE CONNECTION' : 'DISCONNECTED'}
        </div>
      </header>

      <section style={{marginBottom: '2rem'}}>
        <div style={{display: 'flex', gap: '2rem', flexWrap: 'wrap'}}>
          <div className="info-stat">
            <Box size={16} color="#94a3b8" />
            <span>Board: <strong>{manifest?.board || '---'}</strong></span>
          </div>
          <div className="info-stat">
            <Clock size={16} color="#94a3b8" />
            <span>Update Rate: 200ms</span>
          </div>
        </div>
      </section>

      <div className="grid">
        {registers.length > 0 ? (
          registers.map((reg, idx) => (
            <div key={idx} className="card">
              <div className="reg-label">Register Mapping</div>
              <div className="reg-name">{reg.name}</div>
              <div className="reg-value-container">
                <div className="reg-hex">{reg.value}</div>
                <div className="reg-dec">Decimal: {reg.decimal.toLocaleString()}</div>
              </div>
              <div className="reg-footer">
                <span>Offset: {reg.offset}</span>
                <span className="device-tag">{reg.deviceName}</span>
              </div>
            </div>
          ))
        ) : (
          <div style={{gridColumn: '1/-1', textAlign: 'center', padding: '4rem', opacity: 0.5}}>
            <Activity size={48} style={{marginBottom: '1rem'}} />
            <p>Waiting for register data from simulation engine...</p>
          </div>
        )}
      </div>

      <style>{`
        .info-stat {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          font-size: 0.9rem;
          color: #94a3b8;
        }
        .info-stat strong {
          color: #f0f4f8;
        }
      `}</style>
    </div>
  );
}

export default App;
