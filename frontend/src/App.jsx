import React, { useState, useEffect, useRef } from 'react';
import { 
  Activity, 
  Upload, 
  Database, 
  User, 
  CheckCircle, 
  RefreshCw, 
  ArrowRight,
  TrendingUp,
  FileText,
  Search,
  Check,
  AlertCircle
} from 'lucide-react';
import { Radar, Bar } from 'react-chartjs-2';
import confetti from 'canvas-confetti';
import {
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  BarElement
} from 'chart.js';

ChartJS.register(
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  BarElement
);

export default function App() {
  const [activeTab, setActiveTab] = useState('home');
  const [toasts, setToasts] = useState([]);

  // Toast Notification System
  const showToast = (message, type = 'success') => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  };

  // --- PATIENT PORTAL STATE ---
  const [patientName, setPatientName] = useState('');
  const [patientEmail, setPatientEmail] = useState('');
  const [patientErrors, setPatientErrors] = useState({ name: false, email: false });
  const [activeSession, setActiveSession] = useState(null); // { id, name, email }
  const [uploadFile, setUploadFile] = useState(null);
  const [selectedProfileKey, setSelectedProfileKey] = useState('');
  const [availableProfiles, setAvailableProfiles] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [predictionResults, setPredictionResults] = useState(null); // { report_id, predictions: [...] }

  // --- DOCTOR DASHBOARD STATE ---
  const [doctorPatients, setDoctorPatients] = useState([]);
  const [doctorStats, setDoctorStats] = useState({
    total_patients: 0,
    population_sensitivity: 0,
    most_sensitive_drug: 'N/A',
    model_confidence: null
  });
  const [dashboardSearch, setDashboardSearch] = useState('');
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Sync Doctor Dashboard
  const fetchDashboardData = async () => {
    setIsRefreshing(true);
    try {
      const res = await fetch('/doctor/dashboard');
      if (!res.ok) throw new Error('Failed to fetch stats');
      const data = await res.json();
      setDoctorPatients(data.patients || []);
      setDoctorStats(data.stats || {});
    } catch (err) {
      showToast('Error syncing dashboard: ' + err.message, 'danger');
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'doctor') {
      fetchDashboardData();
    }
  }, [activeTab]);

  // Handle Patient Registration
  const handleConnectProfile = async (e) => {
    e.preventDefault();
    const hasName = patientName.trim().length > 1;
    const hasEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(patientEmail);

    setPatientErrors({ name: !hasName, email: !hasEmail });

    if (!hasName || !hasEmail) return;

    try {
      const res = await fetch('/patients', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: patientName, email: patientEmail })
      });
      if (!res.ok) throw new Error('API server returned error');
      const data = await res.json();
      
      setActiveSession(data);
      showToast(data.status === 'created' ? 'Profile registered successfully!' : 'Connected to existing session.');
    } catch (err) {
      showToast('Could not register profile: ' + err.message, 'danger');
    }
  };

  // Drag and Drop Logic
  const onDragOver = (e) => {
    e.preventDefault();
  };

  const processFile = (file) => {
    if (!file || !file.name.endsWith('.json')) {
      showToast('Please upload a valid JSON profile file.', 'danger');
      return;
    }
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const parsed = JSON.parse(e.target.result);
        setAvailableProfiles(parsed);
        setUploadFile(file);
        
        // Auto-select first key
        const keys = Object.keys(parsed);
        if (keys.length > 0) {
          setSelectedProfileKey(keys[0]);
        }
        showToast('Molecular profile loaded. Select a profile block.');
      } catch (err) {
        showToast('Failed to parse JSON file.', 'danger');
      }
    };
    reader.readAsText(file);
  };

  const onDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    processFile(file);
  };

  // Submit Molecular Data
  const handleGenerateReport = async () => {
    if (!activeSession) return;
    const features = availableProfiles[selectedProfileKey];
    if (!features) {
      showToast('Please select a profile block first.', 'danger');
      return;
    }

    setIsLoading(true);
    try {
      const res = await fetch(`/patients/${activeSession.id}/upload`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(features)
      });
      if (!res.ok) throw new Error('Failed to run predictions');
      const data = await res.json();
      
      setPredictionResults(data);
      showToast('Therapeutic recommendations computed!');
      confetti({
        particleCount: 80,
        spread: 60,
        origin: { y: 0.8 },
        colors: ['#0d9488', '#0f766e', '#14b8a6']
      });
    } catch (err) {
      showToast('Prediction run failed: ' + err.message, 'danger');
    } finally {
      setIsLoading(false);
    }
  };

  // --- CHARTS PREPARATION ---
  const prepareChartData = () => {
    if (!predictionResults) return { radar: {}, bar: {} };
    
    // Sort predictions alphabetically by drug name for charts consistency
    const sorted = [...predictionResults.predictions].sort((a, b) => a.drug_name.localeCompare(b.drug_name));
    const labels = sorted.map((p) => p.drug_name);
    const scores = sorted.map((p) => p.probability_sensitive * 100);

    const radar = {
      labels,
      datasets: [
        {
          label: 'Efficacy Index (%)',
          data: scores,
          backgroundColor: 'rgba(13, 148, 136, 0.2)',
          borderColor: '#0d9488',
          borderWidth: 2,
          pointBackgroundColor: '#0f766e',
          pointBorderColor: '#ffffff',
          pointHoverBackgroundColor: '#ffffff',
          pointHoverBorderColor: '#0f766e'
        }
      ]
    };

    const bar = {
      labels,
      datasets: [
        {
          label: 'Probability of Sensitivity (%)',
          data: scores,
          backgroundColor: sorted.map((p) => p.predicted_label === 'Sensitive' ? '#0d9488' : '#cbd5e1'),
          borderRadius: 6,
          borderWidth: 0
        }
      ]
    };

    return { radar, bar };
  };

  const { radar: radarData, bar: barData } = prepareChartData();

  // Filtered Patients for Dashboard Search
  const filteredPatients = doctorPatients.filter((p) => {
    const term = dashboardSearch.toLowerCase();
    return p.name.toLowerCase().includes(term) || p.email.toLowerCase().includes(term);
  });

  return (
    <div>
      {/* Navbar */}
      <nav className="nav">
        <div className="nav-inner">
          <button className="nav-brand" onClick={() => setActiveTab('home')}>
            <div className="nav-brand-icon">
              <Activity />
            </div>
            <span>Medicate <span style={{ fontWeight: 800, color: 'var(--blue-500)' }}>AI</span></span>
          </button>
          <ul className="nav-links">
            <li>
              <button 
                className={`nav-link ${activeTab === 'home' ? 'active' : ''}`}
                onClick={() => setActiveTab('home')}
              >
                Home
              </button>
            </li>
            <li>
              <button 
                className={`nav-link ${activeTab === 'patient' ? 'active' : ''}`}
                onClick={() => setActiveTab('patient')}
              >
                Patient Portal
              </button>
            </li>
            <li>
              <button 
                className={`nav-link ${activeTab === 'doctor' ? 'active' : ''}`}
                onClick={() => setActiveTab('doctor')}
              >
                Clinical Dashboard
              </button>
            </li>
          </ul>
        </div>
      </nav>

      {/* Toast Notifications */}
      <div className="toast-container">
        {toasts.map((t) => (
          <div key={t.id} className="toast" style={{ borderLeft: `4px solid ${t.type === 'danger' ? 'var(--danger-text)' : 'var(--blue-500)'}` }}>
            {t.type === 'danger' ? <AlertCircle className="text-danger" style={{ color: 'var(--danger-text)' }} /> : <CheckCircle style={{ color: 'var(--blue-500)' }} />}
            <span>{t.message}</span>
          </div>
        ))}
      </div>

      <div className="container animate-fade-in">
        {/* --- VIEW: HOME --- */}
        {activeTab === 'home' && (
          <div>
            <div style={{ textAlign: 'center', padding: '6rem 1rem 5rem', maxWidth: '800px', margin: '0 auto' }}>
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', padding: '0.375rem 1rem', background: 'white', border: '1px solid var(--slate-200)', borderRadius: 'var(--radius-pill)', marginBottom: '2rem', boxShadow: 'var(--shadow-sm)', fontSize: '0.75rem', fontWeight: 700, color: 'var(--slate-600)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                <span style={{ display: 'block', width: '6px', height: '6px', background: 'var(--blue-500)', borderRadius: '50%', boxShadow: '0 0 8px var(--blue-500)' }}></span>
                Powered by GDSC1 + GDSC2 + XGBoost
              </div>

              <h1 style={{ fontSize: 'clamp(2.5rem, 6vw, 4.5rem)', fontWeight: 800, lineHeight: 1.1, letterSpacing: '-0.04em', color: 'var(--slate-950)', marginBottom: '1.5rem' }}>
                Clinical oncology,<br />
                <span style={{ background: 'linear-gradient(135deg, var(--blue-500), #00b4d8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>optimized by AI.</span>
              </h1>

              <p style={{ fontSize: '1.125rem', color: 'var(--slate-500)', lineHeight: 1.6, marginBottom: '3rem', fontWeight: 400 }}>
                Translate complex genomic data into actionable therapeutic insights. Our machine learning models identify the most effective cancer therapies with state-of-the-art precision.
              </p>

              <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
                <button onClick={() => setActiveTab('doctor')} className="btn btn-primary btn-lg">
                  Access Dashboard
                  <ArrowRight size={18} />
                </button>
                <button onClick={() => setActiveTab('patient')} className="btn btn-secondary btn-lg">
                  Patient Portal
                </button>
              </div>
            </div>

            <div className="grid-3 mt-4">
              <div className="card">
                <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'var(--blue-50)', color: 'var(--blue-500)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '1.25rem' }}>
                  <Activity size={20} />
                </div>
                <h3 style={{ fontSize: '1.125rem', marginBottom: '0.5rem', color: 'var(--slate-900)' }}>Molecular Indexing</h3>
                <p style={{ color: 'var(--slate-500)', fontSize: '0.875rem', lineHeight: 1.6 }}>Upload cellular profiles to receive AI-driven sensitivity predictions across a wide array of therapeutic targets.</p>
              </div>

              <div className="card">
                <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'var(--success-bg)', color: 'var(--success-text)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '1.25rem' }}>
                  <TrendingUp size={20} />
                </div>
                <h3 style={{ fontSize: '1.125rem', marginBottom: '0.5rem', color: 'var(--slate-900)' }}>Clinical Analytics</h3>
                <p style={{ color: 'var(--slate-500)', fontSize: '0.875rem', lineHeight: 1.6 }}>Track cohort-level drug response patterns, monitor trial enrollment, and evaluate predictive confidence metrics.</p>
              </div>

              <div className="card">
                <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'var(--warning-bg)', color: 'var(--warning-text)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '1.25rem' }}>
                  <Database size={20} />
                </div>
                <h3 style={{ fontSize: '1.125rem', marginBottom: '0.5rem', color: 'var(--slate-900)' }}>Unified Training</h3>
                <p style={{ color: 'var(--slate-500)', fontSize: '0.875rem', lineHeight: 1.6 }}>Our models train concurrently on GDSC1 and GDSC2 screening data, mapping targets through continuous validation.</p>
              </div>
            </div>
          </div>
        )}

        {/* --- VIEW: PATIENT PORTAL --- */}
        {activeTab === 'patient' && (
          <div>
            <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2.5rem' }}>
              <div>
                <h1 style={{ fontSize: '1.5rem', marginBottom: '0.25rem' }}>Patient Portal</h1>
                <p style={{ color: 'var(--slate-500)', fontSize: '0.875rem' }}>Secure access to predictive therapeutic models.</p>
              </div>
              {activeSession && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <div className="avatar">
                    {activeSession.name.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 0.875, color: 'var(--slate-900)' }}>{activeSession.name}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--success-text)', fontWeight: 600 }}>Active Session</div>
                  </div>
                </div>
              )}
            </header>

            {!activeSession ? (
              <div style={{ maxWidth: '440px', margin: '4rem auto' }}>
                <div className="card">
                  <div className="text-center mb-4">
                    <h2 style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>Join the Trial</h2>
                    <p style={{ color: 'var(--slate-500)', fontSize: '0.875rem' }}>Connect your profile to access AI-powered sensitivity analysis.</p>
                  </div>

                  <form onSubmit={handleConnectProfile}>
                    <div className={`form-group ${patientErrors.name ? 'form-error' : ''}`}>
                      <label className="form-label">Full Name</label>
                      <div className="search-input-wrapper">
                        <User />
                        <input 
                          type="text" 
                          className="form-input" 
                          value={patientName} 
                          onChange={(e) => setPatientName(e.target.value)} 
                          placeholder="e.g. Jane Doe"
                        />
                      </div>
                      <div className="form-error-msg">Please enter a valid full name.</div>
                    </div>

                    <div className={`form-group ${patientErrors.email ? 'form-error' : ''}`}>
                      <label className="form-label">Email Address</label>
                      <div className="search-input-wrapper">
                        <FileText />
                        <input 
                          type="email" 
                          className="form-input" 
                          value={patientEmail} 
                          onChange={(e) => setPatientEmail(e.target.value)} 
                          placeholder="jane@example.com"
                        />
                      </div>
                      <div className="form-error-msg">Please enter a valid email address.</div>
                    </div>

                    <button type="submit" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center', marginTop: '1rem' }}>
                      Connect Profile
                    </button>
                  </form>
                </div>
              </div>
            ) : (
              <div className="grid-2">
                {/* Upload & Select */}
                <div className="card">
                  <div className="card-header">
                    <div className="card-title">
                      <Upload />
                      Molecular Profile Upload
                    </div>
                  </div>
                  <p style={{ color: 'var(--slate-500)', fontSize: '0.875rem', marginBottom: '1.5rem' }}>
                    Securely transmit your cellular profile for indexing and prediction.
                  </p>

                  <div 
                    className={`drop-zone mb-3 ${uploadFile ? 'active' : ''}`} 
                    onDragOver={onDragOver}
                    onDrop={onDrop}
                    onClick={() => document.getElementById('fileInput').click()}
                  >
                    <input 
                      type="file" 
                      id="fileInput" 
                      accept=".json" 
                      style={{ display: 'none' }} 
                      onChange={(e) => processFile(e.target.files[0])}
                    />
                    <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🧬</div>
                    <h4 style={{ fontWeight: 600, color: 'var(--slate-900)', marginBottom: '0.25rem' }}>
                      {uploadFile ? uploadFile.name : 'Upload Profile JSON'}
                    </h4>
                    <p style={{ fontSize: '0.8125rem', color: 'var(--slate-500)', margin: 0 }}>
                      Drag & drop or click to upload demo file
                    </p>
                  </div>

                  {Object.keys(availableProfiles).length > 0 && (
                    <div className="form-group">
                      <label className="form-label">Select Tissue Profile Block</label>
                      <select 
                        className="form-input" 
                        style={{ paddingLeft: '1rem' }} 
                        value={selectedProfileKey}
                        onChange={(e) => setSelectedProfileKey(e.target.value)}
                      >
                        {Object.keys(availableProfiles).map((k) => (
                          <option key={k} value={k}>{k.replace(/_/g, ' ').toUpperCase()}</option>
                        ))}
                      </select>
                    </div>
                  )}

                  <button 
                    onClick={handleGenerateReport} 
                    className="btn btn-primary" 
                    style={{ width: '100%', justifyContent: 'center' }}
                    disabled={isLoading || !uploadFile}
                  >
                    {isLoading ? (
                      <>
                        <RefreshCw className="animate-spin" size={16} style={{ marginRight: '0.5rem' }} />
                        Analyzing...
                      </>
                    ) : 'Generate AI Report'}
                  </button>
                </div>

                {/* Predictions Results / Charts */}
                <div className="card">
                  <div className="card-header">
                    <div className="card-title">
                      <Activity />
                      Analysis Results
                    </div>
                  </div>

                  {isLoading ? (
                    <div className="scan-container">
                      <div className="scan-bar"></div>
                      <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>🧬</div>
                      <h4 style={{ fontWeight: 700, color: 'var(--slate-800)', marginBottom: '0.5rem' }}>Analyzing Tissue Profile...</h4>
                      <p style={{ color: 'var(--text-muted)', fontSize: '0.8125rem', textAlign: 'center', maxWidth: '240px' }}>
                        Mapping expression targets and computing XGBoost drug sensitivity index.
                      </p>
                    </div>
                  ) : !predictionResults ? (
                    <div style={{ textAlign: 'center', padding: '4rem 1rem', color: 'var(--slate-400)' }}>
                      <Database size={48} style={{ margin: '0 auto 1rem', strokeWidth: 1.5 }} />
                      <p style={{ fontSize: '0.875rem' }}>Upload a profile to compute drug response probability charts.</p>
                    </div>
                  ) : (
                    <div>
                      <div className="mb-3" style={{ height: '240px', display: 'flex', justifyContent: 'center' }}>
                        <Radar 
                          data={radarData} 
                          options={{
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {
                              r: {
                                min: 0,
                                max: 100,
                                ticks: { stepSize: 20 }
                              }
                            }
                          }} 
                        />
                      </div>
                      
                      <div className="table-wrapper">
                        <table className="table">
                          <thead>
                            <tr>
                              <th>Drug</th>
                              <th>Probability</th>
                              <th>Label</th>
                            </tr>
                          </thead>
                          <tbody>
                            {predictionResults.predictions.map((p, idx) => (
                              <tr key={idx}>
                                <td style={{ fontWeight: 600 }}>{p.drug_name}</td>
                                <td>{(p.probability_sensitive * 100).toFixed(1)}%</td>
                                <td>
                                  <span className={`badge ${p.predicted_label === 'Sensitive' ? 'badge-success' : 'badge-danger'}`}>
                                    {p.predicted_label}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* --- VIEW: CLINICAL DASHBOARD --- */}
        {activeTab === 'doctor' && (
          <div>
            <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '2rem' }}>
              <div>
                <h1 style={{ fontSize: '1.75rem', marginBottom: '0.25rem' }}>Clinical Observatory</h1>
                <p style={{ color: 'var(--slate-500)', fontSize: '0.875rem' }}>Monitor patient cohorts and predictive drug response analytics.</p>
              </div>
              <button onClick={fetchDashboardData} className="btn btn-secondary" disabled={isRefreshing}>
                <RefreshCw size={16} className={isRefreshing ? 'animate-spin' : ''} />
                Sync Data
              </button>
            </header>

            {/* Stats Panel */}
            <div className="grid-3 mb-3">
              <div className="card">
                <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--slate-500)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>Total Patients</div>
                <div style={{ fontSize: '2rem', fontWeight: 800 }}>{doctorStats.total_patients}</div>
              </div>

              <div className="card">
                <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--slate-500)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>Population Sensitivity</div>
                <div style={{ fontSize: '2rem', fontWeight: 800 }}>{doctorStats.population_sensitivity ? `${doctorStats.population_sensitivity.toFixed(1)}%` : '0%'}</div>
              </div>

              <div className="card">
                <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--slate-500)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>Model Confidence</div>
                <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--blue-500)' }}>
                  {doctorStats.model_confidence != null ? doctorStats.model_confidence.toFixed(2) : 'N/A'}
                </div>
              </div>
            </div>

            {/* Patients Table / Search */}
            <div className="card">
              <div className="card-header" style={{ flexWrap: 'wrap', gap: '1rem' }}>
                <div className="card-title">
                  <Database />
                  Patient Registry
                </div>
                <div className="search-input-wrapper" style={{ maxWidth: '240px' }}>
                  <Search />
                  <input 
                    type="text" 
                    className="form-input" 
                    placeholder="Search patients..." 
                    value={dashboardSearch}
                    onChange={(e) => setDashboardSearch(e.target.value)}
                  />
                </div>
              </div>

              <div className="table-wrapper">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Patient Name</th>
                      <th>Email</th>
                      <th>Latest Assessment</th>
                      <th>Primary Recommendations (Efficacy %)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredPatients.length === 0 ? (
                      <tr>
                        <td colSpan="4" style={{ textAlign: 'center', color: 'var(--slate-400)', padding: '2rem' }}>
                          No patients enrolled.
                        </td>
                      </tr>
                    ) : (
                      filteredPatients.map((p, idx) => (
                        <tr key={idx}>
                          <td style={{ fontWeight: 600 }}>{p.name}</td>
                          <td>{p.email}</td>
                          <td>
                            {p.latest_report_date 
                              ? new Date(p.latest_report_date).toLocaleDateString(undefined, { dateStyle: 'medium' }) 
                              : 'Pending upload'}
                          </td>
                          <td>
                            {p.top_recommendations && p.top_recommendations.length > 0 ? (
                              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                                {p.top_recommendations.map((rec, rIdx) => (
                                  <span key={rIdx} className="badge badge-success">
                                    {rec.drug} ({(rec.score * 100).toFixed(0)}%)
                                  </span>
                                ))}
                              </div>
                            ) : (
                              <span style={{ color: 'var(--slate-400)', fontSize: '0.8125rem' }}>No data</span>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        <footer style={{ marginTop: '5rem', textAlign: 'center', borderTop: '1px solid var(--border-light)', paddingTop: '2rem' }}>
          <p style={{ color: 'var(--slate-400)', fontSize: '0.8125rem' }}>Medicate AI Clinical Observatory &middot; Research Use Only</p>
        </footer>
      </div>
    </div>
  );
}
