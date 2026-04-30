import React, { useState, useEffect, useRef } from 'react';
import { io } from 'socket.io-client';
import { Activity, Cpu, Hash, Clock, Box, Terminal as TerminalIcon, Send, AlertCircle, ToggleRight } from 'lucide-react';
import './App.css';

const socket = io('http://' + window.location.hostname + ':8080');

function App() {
  const [registers, setRegisters] = useState([]);
  const [connected, setConnected] = useState(false);
  const [manifest, setManifest] = useState(null);
  const [uartLogs, setUartLogs] = useState({});
  const [activeUart, setActiveUart] = useState(null);
  const [uartInput, setUartInput] = useState("");
  const terminalViewportRef = useRef(null);

  useEffect(() => {
    socket.on('connect', () => setConnected(true));
    socket.on('disconnect', () => setConnected(false));
    socket.on('registers', (data) => setRegisters(data));
    socket.on('uart-init', (data) => {
      setUartLogs(data);
      if (!activeUart && Object.keys(data).length > 0) setActiveUart(Object.keys(data)[0]);
    });
    socket.on('uart-data', ({ name, text }) => {
      setUartLogs(prev => ({ ...prev, [name]: (prev[name] || "") + text }));
      if (!activeUart) setActiveUart(name);
    });

    fetch('/api/manifest').then(res => res.json()).then(setManifest);

    return () => {
      socket.off('connect');
      socket.off('disconnect');
      socket.off('registers');
      socket.off('uart-data');
      socket.off('uart-init');
    };
  }, [activeUart]);

  useEffect(() => {
    const viewport = terminalViewportRef.current;
    if (viewport) {
      viewport.scrollTop = viewport.scrollHeight;
    }
  }, [uartLogs, activeUart]);

  const sendUart = (e) => {
    e.preventDefault();
    if (activeUart && uartInput) {
      socket.emit('uart-send', { name: activeUart, text: uartInput + '\n' });
      setUartInput("");
    }
  };

  const hasRegisters = registers.length > 0;
  const gpioDevices = manifest?.devices?.filter(d => d.type === 'gpio') || [];

  return (
    <div className="dashboard-container">
      <header className="main-header">
        <div className="brand">
          <span className="logo-text">VirtualFPGALab</span>
          <span className="version-tag">v2.2 Premium</span>
        </div>
        <div className="system-meta">
          <div className="meta-item"><Box size={14} /> {manifest?.board || 'Loading...'}</div>
          <div className={`conn-status ${connected ? 'online' : 'offline'}`}>
            {connected ? '● LIVE' : '○ DISCONNECTED'}
          </div>
        </div>
      </header>

      <main className={`content-layout ${hasRegisters ? 'with-sidebar' : 'full-width'}`}>
        {hasRegisters && (
          <aside className="sidebar">
            <div className="panel-header"><Cpu size={16} /> Registers</div>
            <div className="register-list">
              {registers.map((reg, i) => (
                <div key={i} className="reg-card">
                  <div className="reg-info">
                    <span className="reg-name">{reg.name}</span>
                    <span className="reg-offset">{reg.offset}</span>
                  </div>
                  <div className="reg-val">{reg.value}</div>
                </div>
              ))}
            </div>
            
            {gpioDevices.map((dev, i) => {
              const dataReg = registers.find(r => r.deviceName === dev.name && r.name.startsWith('DATA'));
              const triReg = registers.find(r => r.deviceName === dev.name && r.name.startsWith('TRI'));
              
              if (!dataReg || !triReg) return null;
              
              const dataVal = dataReg.decimal || 0;
              const triVal = triReg.decimal || 0;
              
              return (
                <div key={`gpio-${i}`} className="gpio-panel">
                  <div className="panel-header"><ToggleRight size={16} /> GPIO: {dev.name}</div>
                  <div className="gpio-bits">
                    {Array.from({ length: 8 }).map((_, bitIndex) => {
                      const isInput = (triVal & (1 << bitIndex)) !== 0;
                      const isOn = (dataVal & (1 << bitIndex)) !== 0;
                      return (
                        <div key={bitIndex} className={`gpio-bit ${isInput ? 'input' : 'output'} ${isOn ? 'on' : 'off'}`}>
                          <div className="gpio-indicator"></div>
                          <span className="gpio-label">B{bitIndex}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </aside>
        )}

        <section className="terminal-section">
          <div className="panel-header">
            <div className="tab-group">
              <TerminalIcon size={16} />
              {Object.keys(uartLogs).map(name => (
                <button 
                  key={name} 
                  className={`tab ${activeUart === name ? 'active' : ''}`}
                  onClick={() => setActiveUart(name)}
                >
                  {name.replace('vfpga_uart_', 'UART ')}
                </button>
              ))}
              {Object.keys(uartLogs).length === 0 && <span className="no-uart">No active UART detected</span>}
            </div>
          </div>
          
          <div className="terminal-viewport" ref={terminalViewportRef}>
            <pre className="terminal-output">
              {activeUart ? uartLogs[activeUart] : 'Waiting for system startup...\n[Action Required] Run your FW application with LD_PRELOAD to enable UART.'}
            </pre>
          </div>

          <form className="terminal-prompt" onSubmit={sendUart}>
            <Send size={16} className="prompt-icon" />
            <input 
              type="text" 
              placeholder="Type command and press Enter..." 
              value={uartInput}
              onChange={e => setUartInput(e.target.value)}
              disabled={!activeUart}
            />
          </form>
        </section>
      </main>

      <style>{`
        * { box-sizing: border-box; }
        html, body, #root { 
          margin: 0; 
          padding: 0; 
          height: 100vh; 
          width: 100vw;
          overflow: hidden; 
          background: #0d1117;
        }
        .dashboard-container {
          height: 100vh;
          width: 100vw;
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }
        .main-header {
          flex: 0 0 60px;
          padding: 0 2rem;
          background: #161b22;
          border-bottom: 1px solid #30363d;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .logo-text { font-weight: 800; font-size: 1.2rem; color: #58a6ff; }
        .version-tag { margin-left: 0.5rem; font-size: 0.7rem; color: #8b949e; border: 1px solid #30363d; padding: 2px 6px; border-radius: 4px; }
        .system-meta { display: flex; gap: 1.5rem; align-items: center; }
        .meta-item { display: flex; align-items: center; gap: 0.5rem; font-size: 0.8rem; color: #8b949e; }
        .conn-status { font-size: 0.8rem; font-weight: 700; padding: 4px 12px; border-radius: 99px; }
        .conn-status.online { background: rgba(35, 134, 54, 0.15); color: #3fb950; }
        .conn-status.offline { background: rgba(248, 81, 73, 0.15); color: #f85149; }

        .content-layout { 
          flex: 1; 
          display: grid; 
          background: #30363d; 
          overflow: hidden; 
          min-height: 0;
        }
        .content-layout.with-sidebar { grid-template-columns: 300px 1fr; }
        .content-layout.full-width { grid-template-columns: 1fr; }

        .sidebar, .terminal-section { 
          background: #0d1117; 
          display: flex; 
          flex-direction: column; 
          overflow: hidden; 
          min-height: 0;
        }
        .panel-header { 
          flex: 0 0 40px; 
          padding: 0 1rem; 
          background: #161b22; 
          font-size: 0.8rem; 
          font-weight: 600; 
          color: #8b949e; 
          border-bottom: 1px solid #30363d; 
          display: flex; 
          align-items: center; 
          gap: 0.5rem; 
        }
        
        .register-list { flex: 1; overflow-y: auto; padding: 1rem; }
        .reg-card { background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 0.75rem; margin-bottom: 0.75rem; }
        .reg-info { display: flex; justify-content: space-between; margin-bottom: 0.5rem; font-size: 0.7rem; color: #8b949e; }
        .reg-name { color: #e6edf3; font-weight: 600; font-size: 0.85rem; }
        .reg-val { font-family: 'JetBrains Mono', monospace; font-size: 1.2rem; color: #58a6ff; }

        .gpio-panel { margin-top: 1rem; border-top: 1px solid #30363d; }
        .gpio-bits { display: flex; flex-wrap: wrap; gap: 0.5rem; padding: 1rem; }
        .gpio-bit { display: flex; flex-direction: column; align-items: center; gap: 0.25rem; }
        .gpio-indicator { width: 16px; height: 16px; border-radius: 50%; border: 2px solid #30363d; background: #0d1117; }
        .gpio-bit.output.on .gpio-indicator { background: #3fb950; border-color: #2ea043; box-shadow: 0 0 8px rgba(63, 185, 80, 0.4); }
        .gpio-bit.input.on .gpio-indicator { background: #58a6ff; border-color: #388bfd; box-shadow: 0 0 8px rgba(88, 166, 255, 0.4); }
        .gpio-label { font-size: 0.6rem; color: #8b949e; font-weight: 600; }

        .terminal-section { min-width: 0; position: relative; }
        .tab-group { display: flex; align-items: center; gap: 0.5rem; }
        .tab { background: transparent; border: none; color: #8b949e; padding: 4px 12px; cursor: pointer; font-size: 0.8rem; border-radius: 4px; }
        .tab.active { background: #30363d; color: #f0f6fc; }

        .terminal-viewport { 
          flex: 1; 
          overflow-y: auto; 
          padding: 1.5rem; 
          background: #010409; 
          scrollbar-width: thin;
          scrollbar-color: #30363d transparent;
        }
        .terminal-output { margin: 0; font-family: 'JetBrains Mono', monospace; font-size: 0.95rem; line-height: 1.5; color: #d1d5db; white-space: pre-wrap; }
        
        .terminal-prompt { 
          flex: 0 0 60px; 
          padding: 0 1rem; 
          background: #161b22; 
          border-top: 1px solid #30363d; 
          display: flex; 
          align-items: center; 
          gap: 1rem; 
        }
        .terminal-prompt input { 
          flex: 1; 
          background: #0d1117; 
          border: 1px solid #30363d; 
          border-radius: 6px; 
          padding: 8px 12px; 
          color: white; 
          outline: none; 
          font-family: inherit;
        }
        .terminal-prompt input:focus { border-color: #58a6ff; box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.1); }
      `}</style>
    </div>
  );
}

export default App;
