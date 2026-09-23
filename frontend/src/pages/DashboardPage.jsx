import React, { useEffect, useState } from 'react';
import { 
  AlertTriangle, 
  ShieldAlert, 
  ShieldCheck, 
  Activity, 
  TrendingUp, 
  Layers, 
  RefreshCw,
  Clock, 
  ArrowRight, 
  AlertCircle,
  BellRing,
  CheckCircle,
  Check
} from 'lucide-react';
import { fetchDashboardSummary, fetchPatterns, fetchReports, fetchAlerts, acknowledgeAlert } from '../services/api';

export default function DashboardPage({ onNavigateTab, onSelectReport }) {
  const [summary, setSummary] = useState(null);
  const [patterns, setPatterns] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [trendData, setTrendData] = useState([]);
  const [recentHighRisk, setRecentHighRisk] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [ackLoading, setAckLoading] = useState(false);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sumRes, patRes, repRes, alertRes] = await Promise.all([
        fetchDashboardSummary(),
        fetchPatterns(),
        fetchReports({ limit: 50 }),
        fetchAlerts(null, 20),
      ]);

      setSummary(sumRes);
      setPatterns(patRes);
      setAlerts(alertRes?.alerts || sumRes?.active_alerts || []);

      // Compute actual risk trend by date from live reports
      if (repRes && repRes.items) {
        const dateMap = {};
        repRes.items.forEach(r => {
          const dateStr = new Date(r.created_at).toLocaleDateString(undefined, {
            month: 'short',
            day: 'numeric',
          });
          if (!dateMap[dateStr]) {
            dateMap[dateStr] = { date: dateStr, HIGH: 0, MEDIUM: 0, LOW: 0, total: 0 };
          }
          dateMap[dateStr][r.priority] = (dateMap[dateStr][r.priority] || 0) + 1;
          dateMap[dateStr].total += 1;
        });

        // Convert to sorted array
        const sortedTrend = Object.values(dateMap).slice(-7);
        setTrendData(sortedTrend);

        // Filter recent high risk reports
        const highRisk = repRes.items.filter(r => r.priority === 'HIGH').slice(0, 4);
        setRecentHighRisk(highRisk);
      }
    } catch (err) {
      console.error("Error loading dashboard data:", err);
      setError(err.message || "Failed to load live dashboard metrics from FastAPI.");
    } finally {
      setLoading(false);
    }
  };

  const handleAcknowledgeAlert = async (e, alertId) => {
    e.stopPropagation();
    setAckLoading(true);
    try {
      await acknowledgeAlert(alertId, 'HSE-OFFICER-01');
      setAlerts(prev => prev.map(a => a.alert_id === alertId ? { ...a, acknowledged: true } : a));
    } catch (err) {
      console.error("Failed to acknowledge alert:", err);
    } finally {
      setAckLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading && !summary) {
    return (
      <div className="loading-state">
        <RefreshCw size={28} className="spin" />
        <p>Loading real-time safety metrics from SIF Sentinel API...</p>
      </div>
    );
  }

  if (error && !summary) {
    return (
      <div className="empty-state">
        <AlertTriangle size={36} color="#dc2626" style={{ marginBottom: '0.75rem' }} />
        <h3>Unable to load dashboard data</h3>
        <p style={{ marginTop: '0.25rem', color: '#64748b' }}>{error}</p>
        <button className="btn btn-outline" style={{ marginTop: '1rem' }} onClick={loadData}>
          Retry Connection
        </button>
      </div>
    );
  }

  return (
    <div className="dashboard-page">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h2>Industrial Safety Precursor Dashboard</h2>
          <p>Real-time AI triage, deterministic barrier evaluation, and precursor intelligence</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button className="btn btn-outline" onClick={loadData} title="Refresh live metrics">
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      {/* Active High-Priority Escalation Alerts (Phase 13 Automated Workflow) */}
      {alerts.filter(a => !a.acknowledged && (a.severity === 'HIGH' || a.workflow_status === 'HSE_REVIEW_REQUIRED')).length > 0 && (
        <div className="card-panel" id="automated-hse-alerts" style={{ border: '2px solid var(--sif-high)', backgroundColor: '#fff', marginBottom: '1.5rem', boxShadow: '0 4px 12px rgba(220, 38, 38, 0.08)' }}>
          <div className="card-panel-header" style={{ backgroundColor: '#fee2e2', borderBottom: '1px solid #fecaca', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', color: 'var(--sif-high-text)', fontWeight: 800, fontSize: '0.95rem' }}>
              <BellRing size={20} color="var(--sif-high)" />
              <span>AUTOMATED SIF ESCALATION — INTERNAL NOTIFICATION SYSTEM</span>
              <span className="badge-priority HIGH" style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem' }}>
                {alerts.filter(a => !a.acknowledged && (a.severity === 'HIGH' || a.workflow_status === 'HSE_REVIEW_REQUIRED')).length} Active Alerts
              </span>
            </div>
            <button 
              className="btn btn-primary" 
              style={{ fontSize: '0.75rem', padding: '0.3rem 0.75rem', backgroundColor: 'var(--sif-high)', borderColor: 'var(--sif-high)' }}
              onClick={() => onNavigateTab('review')}
            >
              Open HSE Review Queue
            </button>
          </div>
          <div className="card-panel-body" style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {alerts
              .filter(a => !a.acknowledged && (a.severity === 'HIGH' || a.workflow_status === 'HSE_REVIEW_REQUIRED'))
              .slice(0, 3)
              .map((alt) => (
                <div 
                  key={alt.alert_id} 
                  style={{ 
                    backgroundColor: '#fef2f2', 
                    border: '1px solid #fecaca', 
                    borderRadius: '8px', 
                    padding: '1rem',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '1rem'
                  }}
                >
                  <div style={{ flex: 1, minWidth: '280px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.35rem', flexWrap: 'wrap' }}>
                      <div style={{ color: 'var(--sif-high)', fontWeight: 900, fontSize: '1rem', letterSpacing: '0.02em' }}>
                        HIGH PRIORITY → HSE REVIEW REQUIRED
                      </div>
                      <span className="mono-id" style={{ fontSize: '0.85rem' }}>{alt.report_id}</span>
                      <span className="badge-neutral" style={{ backgroundColor: '#fee2e2', color: '#991b1b', fontSize: '0.75rem', fontWeight: 700 }}>
                        {alt.workflow_status}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.85rem', color: '#334155', marginBottom: '0.4rem', lineHeight: 1.4 }}>
                      {alt.message}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#64748b', display: 'flex', gap: '1.25rem', flexWrap: 'wrap' }}>
                      <span>Triggered: <strong>{alt.created_at ? new Date(alt.created_at).toLocaleString() : 'Just now'}</strong></span>
                      {alt.hazard && <span>Hazard: <strong>{alt.hazard}</strong></span>}
                      {alt.barrier && <span>Barrier: <strong>{alt.barrier}</strong></span>}
                      {alt.sif_probability && <span>SIF Prob: <strong style={{ color: 'var(--sif-high)' }}>{(alt.sif_probability * 100).toFixed(1)}%</strong></span>}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexShrink: 0 }}>
                    <button 
                      className="btn btn-outline"
                      style={{ fontSize: '0.75rem', padding: '0.35rem 0.75rem', backgroundColor: '#fff' }}
                      disabled={ackLoading}
                      onClick={(e) => handleAcknowledgeAlert(e, alt.alert_id)}
                      title="Acknowledge alert"
                    >
                      <CheckCircle size={13} /> Acknowledge
                    </button>
                    <button 
                      className="btn btn-primary"
                      style={{ fontSize: '0.75rem', padding: '0.35rem 0.85rem', backgroundColor: '#dc2626', borderColor: '#dc2626' }}
                      onClick={() => onSelectReport(alt.report_id)}
                    >
                      Inspect Report <ArrowRight size={13} />
                    </button>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* KPI Cards: Total Reports, HIGH, MEDIUM, LOW, Precursor Rate */}
      <div className="kpi-grid">
        {/* Total Reports */}
        <div className="kpi-card" id="kpi-total">
          <div className="kpi-card-header">
            <span className="kpi-title">Total Reports</span>
            <div className="kpi-icon" style={{ backgroundColor: '#eff6ff', color: '#2563eb' }}>
              <Layers size={18} />
            </div>
          </div>
          <div className="kpi-value">{summary?.total_reports ?? 0}</div>
          <div className="kpi-subtext">Ingested & evaluated safety events</div>
        </div>

        {/* HIGH Priority Precursors */}
        <div className="kpi-card" id="kpi-high" style={{ borderLeft: '4px solid var(--sif-high)' }}>
          <div className="kpi-card-header">
            <span className="kpi-title" style={{ color: 'var(--sif-high)' }}>HIGH Priority</span>
            <div className="kpi-icon" style={{ backgroundColor: 'var(--sif-high-bg)', color: 'var(--sif-high)' }}>
              <AlertTriangle size={18} />
            </div>
          </div>
          <div className="kpi-value" style={{ color: 'var(--sif-high)' }}>
            {summary?.high_priority_count ?? 0}
          </div>
          <div className="kpi-subtext">
            {summary?.pending_reviews_count ?? 0} awaiting HSE officer verification
          </div>
        </div>

        {/* MEDIUM Priority */}
        <div className="kpi-card" id="kpi-medium" style={{ borderLeft: '4px solid var(--sif-medium)' }}>
          <div className="kpi-card-header">
            <span className="kpi-title" style={{ color: 'var(--sif-medium)' }}>MEDIUM Priority</span>
            <div className="kpi-icon" style={{ backgroundColor: 'var(--sif-medium-bg)', color: 'var(--sif-medium)' }}>
              <Activity size={18} />
            </div>
          </div>
          <div className="kpi-value" style={{ color: 'var(--sif-medium)' }}>
            {summary?.medium_priority_count ?? 0}
          </div>
          <div className="kpi-subtext">Elevated consequence / defense gap</div>
        </div>

        {/* LOW Priority */}
        <div className="kpi-card" id="kpi-low" style={{ borderLeft: '4px solid var(--sif-low)' }}>
          <div className="kpi-card-header">
            <span className="kpi-title" style={{ color: 'var(--sif-low)' }}>LOW Priority</span>
            <div className="kpi-icon" style={{ backgroundColor: 'var(--sif-low-bg)', color: 'var(--sif-low)' }}>
              <ShieldCheck size={18} />
            </div>
          </div>
          <div className="kpi-value" style={{ color: 'var(--sif-low)' }}>
            {summary?.low_priority_count ?? 0}
          </div>
          <div className="kpi-subtext">Controlled or non-critical condition</div>
        </div>

        {/* Precursor Rate */}
        <div className="kpi-card" id="kpi-precursor-rate">
          <div className="kpi-card-header">
            <span className="kpi-title">SIF Precursor Rate</span>
            <div className="kpi-icon" style={{ backgroundColor: '#f1f5f9', color: '#475569' }}>
              <TrendingUp size={18} />
            </div>
          </div>
          <div className="kpi-value">
            {summary ? `${summary.sif_precursor_rate.toFixed(1)}%` : '0%'}
          </div>
          <div className="kpi-subtext">Share of reports triaged as HIGH risk</div>
        </div>
      </div>

      {/* Human-in-the-Loop Governance: AI Result vs HSE Result & Review Status */}
      <div className="card-panel" id="hitl-governance-panel" style={{ border: '1px solid #cbd5e1', boxShadow: '0 2px 4px rgba(0,0,0,0.04)' }}>
        <div className="card-panel-header" style={{ backgroundColor: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
          <div className="card-panel-title">
            <ShieldCheck size={18} color="#0284c7" />
            <span>Human-in-the-Loop Governance: AI Predictions vs. HSE Determinations</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span style={{ fontSize: '0.8rem', color: '#64748b' }}>
              Non-destructive audit trail active
            </span>
            <button
              className="btn btn-outline"
              style={{ fontSize: '0.75rem', padding: '0.25rem 0.6rem' }}
              onClick={() => onNavigateTab('review')}
            >
              Open Review Queue ({summary?.pending_reviews_count ?? 0})
            </button>
          </div>
        </div>
        <div className="card-panel-body">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem' }}>
            {/* Column 1: AI Model Result */}
            <div style={{ 
              backgroundColor: '#fafbfc', 
              border: '1px solid #e2e8f0', 
              borderRadius: '8px', 
              padding: '1.1rem' 
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.85rem' }}>
                <div style={{ fontWeight: 700, fontSize: '0.9rem', color: '#0f172a', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <Activity size={15} color="#2563eb" />
                  <span>AI Result (Model Ingestion)</span>
                </div>
                <span className="badge-neutral" style={{ fontSize: '0.75rem' }}>Original Output</span>
              </div>
              <p style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '1rem', lineHeight: 1.4 }}>
                Unmodified probabilistic triage generated by DistilBERT classifier and deterministic safety rules.
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.25rem' }}>
                    <span style={{ fontWeight: 600, color: 'var(--sif-high)' }}>HIGH Priority</span>
                    <span style={{ fontWeight: 700 }}>
                      {summary?.ai_distribution?.HIGH ?? summary?.high_priority_count ?? 0}
                    </span>
                  </div>
                  <div className="bar-track">
                    <div 
                      className="bar-fill danger" 
                      style={{ width: `${((summary?.ai_distribution?.HIGH ?? summary?.high_priority_count ?? 0) / Math.max(1, summary?.total_reports ?? 1)) * 100}%` }} 
                    />
                  </div>
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.25rem' }}>
                    <span style={{ fontWeight: 600, color: 'var(--sif-medium)' }}>MEDIUM Priority</span>
                    <span style={{ fontWeight: 700 }}>
                      {summary?.ai_distribution?.MEDIUM ?? summary?.medium_priority_count ?? 0}
                    </span>
                  </div>
                  <div className="bar-track">
                    <div 
                      className="bar-fill warning" 
                      style={{ width: `${((summary?.ai_distribution?.MEDIUM ?? summary?.medium_priority_count ?? 0) / Math.max(1, summary?.total_reports ?? 1)) * 100}%` }} 
                    />
                  </div>
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.25rem' }}>
                    <span style={{ fontWeight: 600, color: 'var(--sif-low)' }}>LOW Priority</span>
                    <span style={{ fontWeight: 700 }}>
                      {summary?.ai_distribution?.LOW ?? summary?.low_priority_count ?? 0}
                    </span>
                  </div>
                  <div className="bar-track">
                    <div 
                      className="bar-fill success" 
                      style={{ width: `${((summary?.ai_distribution?.LOW ?? summary?.low_priority_count ?? 0) / Math.max(1, summary?.total_reports ?? 1)) * 100}%` }} 
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Column 2: HSE Result */}
            <div style={{ 
              backgroundColor: '#fafbfc', 
              border: '1px solid #e2e8f0', 
              borderRadius: '8px', 
              padding: '1.1rem' 
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.85rem' }}>
                <div style={{ fontWeight: 700, fontSize: '0.9rem', color: '#0f172a', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <ShieldCheck size={15} color="#16a34a" />
                  <span>HSE Result (Officer Review)</span>
                </div>
                <span className="badge-neutral" style={{ fontSize: '0.75rem', backgroundColor: '#f0fdf4', color: '#166534' }}>Governing Output</span>
              </div>
              <p style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '1rem', lineHeight: 1.4 }}>
                Authoritative determinations confirmed or corrected by certified safety professionals.
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.25rem' }}>
                    <span style={{ fontWeight: 600, color: 'var(--sif-high)' }}>HIGH Priority</span>
                    <span style={{ fontWeight: 700 }}>
                      {summary?.hse_distribution?.HIGH ?? 0}
                    </span>
                  </div>
                  <div className="bar-track">
                    <div 
                      className="bar-fill danger" 
                      style={{ width: `${((summary?.hse_distribution?.HIGH ?? 0) / Math.max(1, summary?.total_reports ?? 1)) * 100}%` }} 
                    />
                  </div>
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.25rem' }}>
                    <span style={{ fontWeight: 600, color: 'var(--sif-medium)' }}>MEDIUM Priority</span>
                    <span style={{ fontWeight: 700 }}>
                      {summary?.hse_distribution?.MEDIUM ?? 0}
                    </span>
                  </div>
                  <div className="bar-track">
                    <div 
                      className="bar-fill warning" 
                      style={{ width: `${((summary?.hse_distribution?.MEDIUM ?? 0) / Math.max(1, summary?.total_reports ?? 1)) * 100}%` }} 
                    />
                  </div>
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.25rem' }}>
                    <span style={{ fontWeight: 600, color: 'var(--sif-low)' }}>LOW Priority</span>
                    <span style={{ fontWeight: 700 }}>
                      {summary?.hse_distribution?.LOW ?? 0}
                    </span>
                  </div>
                  <div className="bar-track">
                    <div 
                      className="bar-fill success" 
                      style={{ width: `${((summary?.hse_distribution?.LOW ?? 0) / Math.max(1, summary?.total_reports ?? 1)) * 100}%` }} 
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Column 3: Review Status & AI-Human Agreement */}
            <div style={{ 
              backgroundColor: '#fafbfc', 
              border: '1px solid #e2e8f0', 
              borderRadius: '8px', 
              padding: '1.1rem',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between'
            }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.85rem' }}>
                  <div style={{ fontWeight: 700, fontSize: '0.9rem', color: '#0f172a', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <Layers size={15} color="#d97706" />
                    <span>Review Status Breakdown</span>
                  </div>
                  <span className="badge-neutral" style={{ fontSize: '0.75rem' }}>Workflow Lifecycle</span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.6rem', marginBottom: '1rem' }}>
                  <div style={{ backgroundColor: '#fff', border: '1px solid #e2e8f0', borderRadius: '6px', padding: '0.6rem' }}>
                    <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Pending Review</div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#d97706' }}>
                      {summary?.review_status?.pending ?? summary?.pending_reviews_count ?? 0}
                    </div>
                  </div>

                  <div style={{ backgroundColor: '#fff', border: '1px solid #e2e8f0', borderRadius: '6px', padding: '0.6rem' }}>
                    <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Confirmed</div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#16a34a' }}>
                      {summary?.review_status?.confirmed ?? 0}
                    </div>
                  </div>

                  <div style={{ backgroundColor: '#fff', border: '1px solid #e2e8f0', borderRadius: '6px', padding: '0.6rem' }}>
                    <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Corrected</div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#2563eb' }}>
                      {summary?.review_status?.corrected ?? 0}
                    </div>
                  </div>

                  <div style={{ backgroundColor: '#fff', border: '1px solid #e2e8f0', borderRadius: '6px', padding: '0.6rem' }}>
                    <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Rejected</div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#dc2626' }}>
                      {summary?.review_status?.rejected ?? 0}
                    </div>
                  </div>
                </div>
              </div>

              {/* Agreement Rate Gauge */}
              <div style={{ 
                backgroundColor: '#ffffff', 
                border: '1px solid #e2e8f0', 
                borderRadius: '6px', 
                padding: '0.75rem' 
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.775rem', fontWeight: 600, marginBottom: '0.35rem' }}>
                  <span>AI / Human Agreement Rate</span>
                  <span style={{ color: '#0f172a' }}>
                    {summary?.agreement_rate != null ? `${summary.agreement_rate.toFixed(1)}%` : 'N/A'}
                  </span>
                </div>
                <div className="bar-track" style={{ height: '6px' }}>
                  <div 
                    className="bar-fill info" 
                    style={{ width: `${Math.min(100, summary?.agreement_rate ?? 0)}%` }} 
                  />
                </div>
                <div style={{ fontSize: '0.7rem', color: '#64748b', marginTop: '0.35rem' }}>
                  Percentage of reviewed reports where HSE accepted initial AI priority.
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Row 2: Risk Trend & Top Hazards Breakdown */}
      <div className="grid-2col">
        {/* Risk Trend Distribution */}
        <div className="card-panel">
          <div className="card-panel-header">
            <div className="card-panel-title">
              <TrendingUp size={16} color="#2563eb" />
              <span>Risk Trend (Recent Timeline)</span>
            </div>
            <span className="badge-neutral">Live Ingestion</span>
          </div>
          <div className="card-panel-body">
            {trendData.length === 0 ? (
              <p style={{ color: '#64748b', fontSize: '0.85rem' }}>No historical trend data available yet.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {trendData.map((item, idx) => (
                  <div key={idx}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.35rem', fontWeight: 600 }}>
                      <span>{item.date}</span>
                      <span style={{ color: '#64748b' }}>
                        {item.total} reports ({item.HIGH} High, {item.MEDIUM} Med, {item.LOW} Low)
                      </span>
                    </div>
                    {/* Multi-segment stacked bar */}
                    <div style={{ height: '12px', display: 'flex', borderRadius: '4px', overflow: 'hidden', backgroundColor: '#e2e8f0' }}>
                      {item.HIGH > 0 && (
                        <div 
                          style={{ width: `${(item.HIGH / item.total) * 100}%`, backgroundColor: 'var(--sif-high)' }} 
                          title={`HIGH: ${item.HIGH}`} 
                        />
                      )}
                      {item.MEDIUM > 0 && (
                        <div 
                          style={{ width: `${(item.MEDIUM / item.total) * 100}%`, backgroundColor: 'var(--sif-medium)' }} 
                          title={`MEDIUM: ${item.MEDIUM}`} 
                        />
                      )}
                      {item.LOW > 0 && (
                        <div 
                          style={{ width: `${(item.LOW / item.total) * 100}%`, backgroundColor: 'var(--sif-low)' }} 
                          title={`LOW: ${item.LOW}`} 
                        />
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Top Hazards Distribution */}
        <div className="card-panel">
          <div className="card-panel-header">
            <div className="card-panel-title">
              <AlertCircle size={16} color="#d97706" />
              <span>Top Hazard Categories</span>
            </div>
            <span className="badge-neutral">Consequence Ranked</span>
          </div>
          <div className="card-panel-body">
            {!summary?.top_hazards || summary.top_hazards.length === 0 ? (
              <p style={{ color: '#64748b', fontSize: '0.85rem' }}>No hazards identified yet.</p>
            ) : (
              <div className="bar-list">
                {summary.top_hazards.slice(0, 5).map((h, i) => (
                  <div key={i}>
                    <div className="bar-item-header">
                      <span>{h.hazard}</span>
                      <span style={{ color: '#64748b' }}>
                        {h.count} ({(h.percentage ?? 0).toFixed(1)}%)
                      </span>
                    </div>
                    <div className="bar-track">
                      <div 
                        className={`bar-fill ${i === 0 ? 'danger' : i < 3 ? 'warning' : 'info'}`} 
                        style={{ width: `${Math.min(100, h.percentage ?? 0)}%` }} 
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Row 3: Recurring Precursor Patterns & Actionable Recommendations */}
      <div className="card-panel">
        <div className="card-panel-header">
          <div className="card-panel-title">
            <ShieldAlert size={16} color="#dc2626" />
            <span>Recurring Precursor Patterns</span>
          </div>
          <button 
            className="btn btn-outline" 
            style={{ fontSize: '0.75rem', padding: '0.25rem 0.6rem' }}
            onClick={() => onNavigateTab('patterns')}
          >
            Explore All Patterns <ArrowRight size={12} />
          </button>
        </div>
        <div className="card-panel-body">
          {!patterns?.recurring_clusters || patterns.recurring_clusters.length === 0 ? (
            <p style={{ color: '#64748b', fontSize: '0.85rem' }}>No recurring clusters detected across recent reports.</p>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
              {patterns.recurring_clusters.slice(0, 3).map((cluster, i) => (
                <div 
                  key={i} 
                  style={{ 
                    border: '1px solid #e2e8f0', 
                    borderRadius: '8px', 
                    padding: '1rem',
                    backgroundColor: '#fafbfc' 
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                    <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--sif-high-text)' }}>
                      CLUSTER #{i + 1}
                    </span>
                    <span className="badge-neutral" style={{ fontWeight: 600 }}>
                      {cluster.occurrences || cluster.report_count || 1} Reports
                    </span>
                  </div>
                  <div style={{ fontWeight: 600, fontSize: '0.9rem', color: '#0f172a', marginBottom: '0.35rem' }}>
                    {cluster.cluster_name || cluster.pattern_theme || cluster.activity || "Systemic Hazard Mode"}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: '#475569', marginBottom: '0.5rem' }}>
                    Risk Level: <strong style={{ color: cluster.risk_band === 'HIGH' ? 'var(--sif-high)' : '#d97706' }}>{cluster.risk_band || cluster.hazard || "MEDIUM"}</strong>
                  </div>
                  <div style={{ 
                    fontSize: '0.75rem', 
                    backgroundColor: '#ffffff', 
                    border: '1px solid #e2e8f0', 
                    padding: '0.5rem', 
                    borderRadius: '4px',
                    color: '#334155' 
                  }}>
                    <strong>Action:</strong> {cluster.recommendation || cluster.recommended_action || "Audit isolation and barrier verification at facility."}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Row 4: High Risk Triage Preview */}
      {recentHighRisk.length > 0 && (
        <div className="card-panel">
          <div className="card-panel-header">
            <div className="card-panel-title">
              <AlertTriangle size={16} color="#dc2626" />
              <span>Immediate Attention: High-Risk Reports</span>
            </div>
            <button 
              className="btn btn-outline" 
              style={{ fontSize: '0.75rem', padding: '0.25rem 0.6rem' }}
              onClick={() => onNavigateTab('review')}
            >
              Open HSE Review Queue ({summary?.pending_reviews_count || 0})
            </button>
          </div>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Report ID</th>
                  <th>Activity / Hazard</th>
                  <th>AI Result</th>
                  <th>HSE Result</th>
                  <th>Review Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {recentHighRisk.map((r) => (
                  <tr key={r.report_id} onClick={() => onSelectReport(r.report_id)}>
                    <td className="mono-id">{r.report_id}</td>
                    <td>
                      <div style={{ fontWeight: 600 }}>{r.activity || "Unspecified"}</div>
                      <div style={{ fontSize: '0.75rem', color: '#64748b' }}>{r.hazard || "Unspecified"}</div>
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                        <span className={`badge-priority ${r.priority}`}>{r.priority}</span>
                        <span style={{ fontSize: '0.75rem', color: '#475569', fontWeight: 600 }}>
                          {(r.sif_probability * 100).toFixed(1)}%
                        </span>
                      </div>
                    </td>
                    <td>
                      {r.hse_reviewed ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                          <span className={`badge-priority ${r.final_priority || r.priority}`}>
                            {r.final_priority || r.priority}
                          </span>
                          <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                            ({r.review_decision?.toUpperCase()})
                          </span>
                        </div>
                      ) : (
                        <span style={{ fontSize: '0.8rem', color: '#94a3b8', fontStyle: 'italic' }}>
                          Not reviewed yet
                        </span>
                      )}
                    </td>
                    <td>
                      {r.hse_reviewed ? (
                        <span className={`badge-priority badge-status-${r.review_decision}`}>
                          {r.review_decision}
                        </span>
                      ) : (
                        <span className="badge-priority badge-status-pending">
                          Pending Review
                        </span>
                      )}
                    </td>
                    <td>
                      <button 
                        className="btn btn-outline" 
                        style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectReport(r.report_id);
                        }}
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
