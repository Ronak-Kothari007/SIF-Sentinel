import React, { useState, useEffect } from 'react';
import { 
  GitBranch, 
  AlertTriangle, 
  ShieldAlert, 
  ShieldX, 
  RefreshCw, 
  ArrowRight, 
  FileText,
  CheckCircle2,
  TrendingDown,
  Layers
} from 'lucide-react';
import { fetchPatterns } from '../services/api';

export default function RiskPatternsPage({ onSelectReport }) {
  const [patterns, setPatterns] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedClusterIndex, setSelectedClusterIndex] = useState(0);

  const loadPatterns = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchPatterns();
      setPatterns(data);
    } catch (err) {
      console.error("Error loading patterns:", err);
      setError(err.message || "Failed to load risk pattern intelligence");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPatterns();
  }, []);

  if (loading) {
    return (
      <div className="loading-state">
        <RefreshCw size={28} className="spin" />
        <p>Analyzing cross-report recurring precursors and barrier vulnerabilities...</p>
      </div>
    );
  }

  if (error && !patterns) {
    return (
      <div className="empty-state">
        <AlertTriangle size={36} color="#dc2626" style={{ marginBottom: '0.75rem' }} />
        <h3>Failed to load risk patterns</h3>
        <p style={{ marginTop: '0.25rem', color: '#64748b' }}>{error}</p>
        <button className="btn btn-outline" style={{ marginTop: '1rem' }} onClick={loadPatterns}>
          Retry Pattern Analysis
        </button>
      </div>
    );
  }

  const clusters = patterns?.recurring_clusters || [];
  const activeCluster = clusters[selectedClusterIndex] || null;

  return (
    <div className="risk-patterns-page">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h2>Cross-Site Risk Patterns & Systemic Precursors</h2>
          <p>Automated clustering of recurring hazards, barrier failures, and correlated incident precursors</p>
        </div>
        <button className="btn btn-outline" onClick={loadPatterns}>
          <RefreshCw size={14} /> Refresh Patterns
        </button>
      </div>

      {/* Executive Synthesis Summary */}
      {patterns?.summary && (
        <div style={{ 
          backgroundColor: '#eff6ff', 
          border: '1px solid #bfdbfe', 
          borderRadius: '8px', 
          padding: '1rem 1.25rem', 
          marginBottom: '1.5rem',
          display: 'flex',
          gap: '0.75rem',
          alignItems: 'flex-start'
        }}>
          <ShieldAlert size={20} color="#2563eb" style={{ flexShrink: 0, marginTop: '2px' }} />
          <div>
            <div style={{ fontWeight: 700, fontSize: '0.9rem', color: '#1e40af', marginBottom: '0.25rem' }}>
              Pattern Intelligence Overview ({patterns.total_analyzed} reports synthesized)
            </div>
            <p style={{ fontSize: '0.85rem', color: '#1e3a8a', lineHeight: 1.5 }}>
              {patterns.summary}
            </p>
          </div>
        </div>
      )}

      {/* Top 2 Panels: Recurring Hazards & Recurring Barrier Failures */}
      <div className="grid-2col">
        {/* Recurring Hazards */}
        <div className="card-panel">
          <div className="card-panel-header">
            <div className="card-panel-title">
              <AlertTriangle size={16} color="#dc2626" />
              <span>Recurring Hazard Modes</span>
            </div>
            <span className="badge-neutral">Frequency Ranked</span>
          </div>
          <div className="card-panel-body">
            {!patterns?.top_hazards || patterns.top_hazards.length === 0 ? (
              <p style={{ color: '#64748b', fontSize: '0.85rem' }}>No hazard recurrence detected.</p>
            ) : (
              <div className="bar-list">
                {patterns.top_hazards.map((h, i) => (
                  <div key={i}>
                    <div className="bar-item-header">
                      <span>{h.hazard}</span>
                      <span style={{ color: '#64748b' }}>
                        {h.count} occurrences ({h.percentage.toFixed(1)}%)
                      </span>
                    </div>
                    <div className="bar-track">
                      <div 
                        className={`bar-fill ${i === 0 ? 'danger' : i < 3 ? 'warning' : 'info'}`} 
                        style={{ width: `${Math.min(100, h.percentage)}%` }} 
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Recurring Barrier Failures */}
        <div className="card-panel">
          <div className="card-panel-header">
            <div className="card-panel-title">
              <ShieldX size={16} color="#d97706" />
              <span>Recurring Barrier Failures & Gaps</span>
            </div>
            <span className="badge-neutral">Critical Defenses</span>
          </div>
          <div className="card-panel-body">
            {!patterns?.top_barrier_gaps || patterns.top_barrier_gaps.length === 0 ? (
              <p style={{ color: '#64748b', fontSize: '0.85rem' }}>No systemic barrier failures logged.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {patterns.top_barrier_gaps.map((b, i) => (
                  <div 
                    key={i} 
                    style={{ 
                      padding: '0.75rem', 
                      backgroundColor: '#fafbfc', 
                      border: '1px solid #e2e8f0', 
                      borderRadius: '6px',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '0.85rem', color: '#0f172a' }}>
                        {b.barrier}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: '#dc2626', fontWeight: 500 }}>
                        Condition: {b.barrier_status}
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <span className="badge-priority HIGH" style={{ fontSize: '0.7rem' }}>
                        {b.count} Reports
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Semantic Recurring Patterns via Sentence Transformers (all-MiniLM-L6-v2) */}
      <div className="card-panel" style={{ border: '2px solid #94a3b8' }}>
        <div className="card-panel-header" style={{ backgroundColor: '#f1f5f9' }}>
          <div className="card-panel-title">
            <GitBranch size={16} color="#0284c7" />
            <span>Semantic Recurring Precursor Patterns (all-MiniLM-L6-v2)</span>
          </div>
          <span className="badge-neutral" style={{ backgroundColor: '#eff6ff', color: '#1e40af', fontWeight: 700 }}>
            {patterns?.semantic_patterns?.length || 0} Systemic Patterns Identified
          </span>
        </div>
        <div className="card-panel-body">
          {!patterns?.semantic_patterns || patterns.semantic_patterns.length === 0 ? (
            <p style={{ color: '#64748b', fontSize: '0.85rem' }}>No multi-report semantic clusters meeting the similarity threshold yet.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              {patterns.semantic_patterns.map((pat) => (
                <div 
                  key={pat.pattern_id}
                  style={{ 
                    border: '1px solid #cbd5e1', 
                    borderRadius: '8px', 
                    padding: '1.25rem',
                    backgroundColor: '#ffffff',
                    boxShadow: 'var(--shadow-sm)'
                  }}
                >
                  {/* Header Row: Pattern ID, Report Count, Similarity, Trend Badge */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.85rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                      <span className="mono-id" style={{ fontSize: '0.95rem', fontWeight: 800, backgroundColor: '#0f172a', color: '#ffffff', padding: '0.2rem 0.6rem', borderRadius: '4px' }}>
                        {pat.pattern_id}
                      </span>
                      <span className="badge-priority HIGH" style={{ fontSize: '0.8rem' }}>
                        {pat.number_of_reports} Reports Correlated
                      </span>
                      <span className="badge-neutral" style={{ fontWeight: 600, color: '#1e40af', backgroundColor: '#dbeafe' }}>
                        {(pat.average_similarity * 100).toFixed(1)}% Mean Similarity
                      </span>
                    </div>

                    {/* Trend Badge */}
                    {pat.trend && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', padding: '0.25rem 0.65rem', borderRadius: '9999px', backgroundColor: pat.trend.trend_direction === 'increasing' ? '#fef2f2' : '#f0fdf4', color: pat.trend.trend_direction === 'increasing' ? '#991b1b' : '#166534', border: `1px solid ${pat.trend.trend_direction === 'increasing' ? '#fecaca' : '#bbf7d0'}` }}>
                        <span style={{ fontWeight: 700, textTransform: 'uppercase' }}>
                          Trend: {pat.trend.trend_direction}
                        </span>
                        <span>({pat.trend.span_days} days span)</span>
                      </div>
                    )}
                  </div>

                  {/* Context Grid: Common Activity, Common Hazard, Common Barrier Failure */}
                  <div className="context-key-value-grid" style={{ marginBottom: '0.85rem' }}>
                    <div className="context-card" style={{ padding: '0.65rem 0.85rem' }}>
                      <div className="context-label">Common Activity</div>
                      <div className="context-value" style={{ fontSize: '0.85rem' }}>{pat.common_activity}</div>
                    </div>
                    <div className="context-card" style={{ padding: '0.65rem 0.85rem' }}>
                      <div className="context-label">Common Hazard</div>
                      <div className="context-value" style={{ fontSize: '0.85rem', color: 'var(--sif-high)' }}>{pat.common_hazard}</div>
                    </div>
                    <div className="context-card" style={{ padding: '0.65rem 0.85rem' }}>
                      <div className="context-label">Common Barrier Failure</div>
                      <div className="context-value" style={{ fontSize: '0.85rem', color: '#b45309' }}>{pat.common_barrier_failure}</div>
                    </div>
                  </div>

                  {/* Representative Medoid Narrative */}
                  <div style={{ 
                    backgroundColor: '#f8fafc', 
                    border: '1px solid #e2e8f0', 
                    borderRadius: '6px', 
                    padding: '0.75rem 1rem', 
                    marginBottom: '0.85rem',
                    fontSize: '0.825rem',
                    lineHeight: 1.5,
                    color: '#1e293b' 
                  }}>
                    <span style={{ fontWeight: 700, color: '#475569', display: 'block', marginBottom: '0.2rem', fontSize: '0.75rem', textTransform: 'uppercase' }}>
                      Representative Incident Narrative (Medoid):
                    </span>
                    "{pat.representative_text}"
                  </div>

                  {/* Action Recommendation */}
                  <div style={{ 
                    backgroundColor: '#fffbeb', 
                    border: '1px solid #fde68a', 
                    borderRadius: '6px', 
                    padding: '0.65rem 0.85rem', 
                    fontSize: '0.8rem',
                    color: '#92400e',
                    marginBottom: '0.85rem'
                  }}>
                    <strong>Prescriptive Mitigation:</strong> {pat.recommended_action}
                  </div>

                  {/* Member Reports Links */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                    <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#64748b' }}>
                      Correlated Reports:
                    </span>
                    {pat.report_ids.map((id) => (
                      <button
                        key={id}
                        className="btn btn-outline"
                        style={{ fontSize: '0.725rem', padding: '0.2rem 0.5rem' }}
                        onClick={() => onSelectReport(id)}
                      >
                        <FileText size={11} style={{ marginRight: '3px' }} />
                        {id}
                        <ArrowRight size={10} style={{ marginLeft: '3px' }} />
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
