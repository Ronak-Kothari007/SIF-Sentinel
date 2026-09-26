import React, { useState, useEffect } from 'react';
import { 
  GitBranch, 
  AlertTriangle, 
  ShieldAlert, 
  ShieldX, 
  RefreshCw, 
  ArrowRight, 
  FileText,
  TrendingDown,
  TrendingUp,
  Minus,
  Activity,
  ChevronDown,
  ChevronUp,
  Settings2,
  CheckCircle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { fetchPatterns } from '../services/api';
import { ExportDropdown } from '../components/ui';

export default function RiskPatternsPage({ onSelectReport }) {
  const [patterns, setPatterns] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedPattern, setExpandedPattern] = useState(null);

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

  return (
    <div className="page-container">
      {/* Page Header */}
      <div className="page-header">
        <div className="page-title">
          <h1>Emerging Safety Patterns</h1>
          <p>Repeated observations and critical-control gaps identified across reports.</p>
        </div>
        <div className="page-actions">
          <ExportDropdown />
          <button className="btn btn-outline" onClick={loadPatterns}>
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      {/* Executive Synthesis Summary */}
      {patterns?.summary && (
        <div style={{ 
          backgroundColor: '#f8fafc', 
          border: '1px solid #e2e8f0', 
          borderRadius: '8px', 
          padding: '1.25rem', 
          marginBottom: '1.5rem',
          display: 'flex',
          gap: '1rem',
          alignItems: 'flex-start'
        }}>
          <ShieldAlert size={24} color="var(--sif-medium)" style={{ flexShrink: 0, marginTop: '2px' }} />
          <div>
            <div style={{ fontWeight: 600, fontSize: '0.95rem', color: 'var(--slate-800)', marginBottom: '0.35rem' }}>
              Pattern Overview ({patterns.total_analyzed} reports synthesized)
            </div>
            <p style={{ fontSize: '0.85rem', color: 'var(--slate-600)', lineHeight: 1.6 }}>
              {patterns.summary}
            </p>
          </div>
        </div>
      )}

      {/* Semantic Recurring Patterns */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        {!patterns?.semantic_patterns || patterns.semantic_patterns.length === 0 ? (
          <div className="empty-state">
            <CheckCircle size={36} color="#16a34a" style={{ marginBottom: '0.75rem' }} />
            <h3>No Emerging Patterns</h3>
            <p style={{ color: '#64748b' }}>No multi-report systemic clusters detected at this time.</p>
          </div>
        ) : (
          patterns.semantic_patterns.map((pat) => {
            const isExpanded = expandedPattern === pat.pattern_id;

            return (
              <motion.div 
                layout
                key={pat.pattern_id}
                className="panel"
                style={{ overflow: 'hidden' }}
              >
                <div style={{ padding: '1.25rem' }}>
                  
                  {/* Card Header */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.25rem' }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
                        <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--slate-800)', margin: 0 }}>
                          {pat.recommended_action.split('.')[0]} {/* Use first sentence of recommendation as title */}
                        </h3>
                        {pat.trend && (
                          <span style={{ 
                            display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.75rem', fontWeight: 600,
                            padding: '0.2rem 0.6rem', borderRadius: '1rem',
                            backgroundColor: pat.trend.trend_direction === 'increasing' ? '#fef2f2' : pat.trend.trend_direction === 'decreasing' ? '#f0fdf4' : '#f8fafc',
                            color: pat.trend.trend_direction === 'increasing' ? '#991b1b' : pat.trend.trend_direction === 'decreasing' ? '#166534' : '#475569',
                            border: `1px solid ${pat.trend.trend_direction === 'increasing' ? '#fecaca' : pat.trend.trend_direction === 'decreasing' ? '#bbf7d0' : '#e2e8f0'}`
                          }}>
                            {pat.trend.trend_direction === 'increasing' && <TrendingUp size={12} />}
                            {pat.trend.trend_direction === 'decreasing' && <TrendingDown size={12} />}
                            {pat.trend.trend_direction === 'stable' && <Minus size={12} />}
                            {pat.trend.trend_direction.toUpperCase()}
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: '0.85rem', color: 'var(--sif-high)', fontWeight: 600 }}>
                        {pat.number_of_reports} Repeated Observations
                      </div>
                    </div>
                    
                    <motion.button 
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      className="btn btn-primary" 
                      onClick={() => setExpandedPattern(isExpanded ? null : pat.pattern_id)}
                    >
                      {isExpanded ? 'Close Details' : 'View Reports'}
                    </motion.button>
                  </div>

                  {/* Visual Flow Diagram */}
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    flexWrap: 'wrap', 
                    gap: '0.75rem', 
                    backgroundColor: 'var(--slate-50)', 
                    padding: '1rem', 
                    borderRadius: '8px',
                    border: '1px solid var(--border-color)'
                  }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', flex: 1, minWidth: '150px' }}>
                      <span style={{ fontSize: '0.7rem', color: 'var(--slate-500)', textTransform: 'uppercase', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.25rem' }}><Activity size={12} /> ACTIVITY</span>
                      <span style={{ fontSize: '0.85rem', fontWeight: 500, color: 'var(--slate-800)' }}>{pat.common_activity}</span>
                    </div>
                    <ArrowRight size={16} color="var(--slate-400)" className="hide-on-mobile" />
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', flex: 1, minWidth: '150px' }}>
                      <span style={{ fontSize: '0.7rem', color: 'var(--slate-500)', textTransform: 'uppercase', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.25rem' }}><AlertTriangle size={12} /> HAZARD</span>
                      <span style={{ fontSize: '0.85rem', fontWeight: 500, color: 'var(--sif-medium)' }}>{pat.common_hazard}</span>
                    </div>
                    <ArrowRight size={16} color="var(--slate-400)" className="hide-on-mobile" />
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', flex: 1, minWidth: '150px' }}>
                      <span style={{ fontSize: '0.7rem', color: 'var(--slate-500)', textTransform: 'uppercase', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.25rem' }}><ShieldX size={12} /> BARRIER GAP</span>
                      <span style={{ fontSize: '0.85rem', fontWeight: 500, color: 'var(--sif-high)' }}>{pat.common_barrier_failure}</span>
                    </div>
                  </div>

                  {/* Expanded Content */}
                  <AnimatePresence>
                    {isExpanded && (
                      <motion.div
                        layout
                        initial={{ opacity: 0, height: 0, marginTop: 0 }}
                        animate={{ opacity: 1, height: 'auto', marginTop: '1.5rem' }}
                        exit={{ opacity: 0, height: 0, marginTop: 0 }}
                        style={{ overflow: 'hidden' }}
                      >
                        <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '1.5rem' }}>
                          
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '1.5rem' }}>
                            {/* Member Reports Links */}
                            <div>
                              <h4 style={{ fontSize: '0.85rem', color: 'var(--slate-500)', textTransform: 'uppercase', marginBottom: '0.75rem' }}>Related Reports</h4>
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                {pat.report_ids.map((id) => (
                                  <motion.div
                                    key={id}
                                    whileHover={{ x: 5 }}
                                    style={{ 
                                      display: 'flex', alignItems: 'center', justifyContent: 'space-between', 
                                      padding: '0.75rem 1rem', backgroundColor: 'white', border: '1px solid var(--border-color)', borderRadius: '6px', cursor: 'pointer'
                                    }}
                                    onClick={() => onSelectReport(id)}
                                  >
                                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', fontWeight: 500, color: 'var(--primary)' }}>
                                      <FileText size={14} /> {id}
                                    </span>
                                    <ArrowRight size={14} color="var(--slate-400)" />
                                  </motion.div>
                                ))}
                              </div>
                            </div>

                            {/* Representative Narrative */}
                            <div>
                               <h4 style={{ fontSize: '0.85rem', color: 'var(--slate-500)', textTransform: 'uppercase', marginBottom: '0.75rem' }}>Representative Observation</h4>
                               <div style={{ 
                                backgroundColor: 'var(--slate-50)', 
                                padding: '1rem', 
                                borderRadius: '6px',
                                fontSize: '0.9rem',
                                color: 'var(--slate-700)',
                                lineHeight: 1.6,
                                fontStyle: 'italic'
                              }}>
                                "{pat.representative_text}"
                              </div>
                            </div>
                            
                            {/* Technical Assessment Details (Collapsible) */}
                            <details style={{ marginTop: '0.5rem' }}>
                              <summary style={{ 
                                display: 'inline-flex', alignItems: 'center', gap: '0.5rem', 
                                fontSize: '0.85rem', fontWeight: 600, color: 'var(--slate-500)', 
                                cursor: 'pointer', userSelect: 'none', padding: '0.5rem 0'
                              }}>
                                <Settings2 size={14} /> Technical Assessment Details
                              </summary>
                              <div style={{ 
                                marginTop: '0.75rem', padding: '1rem', backgroundColor: '#f1f5f9', 
                                border: '1px solid #e2e8f0', borderRadius: '6px', fontSize: '0.8rem', color: 'var(--slate-600)'
                              }}>
                                <div style={{ display: 'grid', gridTemplateColumns: '150px 1fr', gap: '0.5rem', marginBottom: '0.5rem' }}>
                                  <strong>Pattern ID:</strong> <span className="mono-id">{pat.pattern_id}</span>
                                </div>
                                <div style={{ display: 'grid', gridTemplateColumns: '150px 1fr', gap: '0.5rem', marginBottom: '0.5rem' }}>
                                  <strong>Similarity Engine:</strong> <span>Dense embeddings (all-MiniLM-L6-v2)</span>
                                </div>
                                <div style={{ display: 'grid', gridTemplateColumns: '150px 1fr', gap: '0.5rem', marginBottom: '0.5rem' }}>
                                  <strong>Mean Similarity:</strong> <span>{(pat.average_similarity * 100).toFixed(1)}%</span>
                                </div>
                                <div style={{ display: 'grid', gridTemplateColumns: '150px 1fr', gap: '0.5rem' }}>
                                  <strong>Full Mitigation:</strong> <span>{pat.recommended_action}</span>
                                </div>
                              </div>
                            </details>

                          </div>

                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>

                </div>
              </motion.div>
            );
          })
        )}
      </div>

      {/* Top Hazards & Barriers (Secondary Details) */}
      {patterns?.top_hazards && patterns.top_hazards.length > 0 && (
        <div style={{ marginTop: '3rem' }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--slate-800)', marginBottom: '1rem' }}>Overall Recurrence Metrics</h3>
          <div className="grid-2col">
            
            {/* Recurring Hazards */}
            <div className="card-panel">
              <div className="card-panel-header">
                <div className="card-panel-title">
                  <AlertTriangle size={16} color="var(--sif-medium)" />
                  <span>Highest Frequency Hazards</span>
                </div>
              </div>
              <div className="card-panel-body">
                <div className="bar-list">
                  {patterns.top_hazards.slice(0, 4).map((h, i) => (
                    <div key={i}>
                      <div className="bar-item-header">
                        <span>{h.hazard}</span>
                        <span style={{ color: 'var(--slate-500)' }}>
                          {h.count} observations
                        </span>
                      </div>
                      <div className="bar-track">
                        <div 
                          className={`bar-fill ${i === 0 ? 'danger' : i < 2 ? 'warning' : 'info'}`} 
                          style={{ width: `${Math.min(100, h.percentage)}%` }} 
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Recurring Barrier Failures */}
            <div className="card-panel">
              <div className="card-panel-header">
                <div className="card-panel-title">
                  <ShieldX size={16} color="var(--sif-high)" />
                  <span>Primary Barrier Deficiencies</span>
                </div>
              </div>
              <div className="card-panel-body">
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {patterns.top_barrier_gaps.slice(0, 4).map((b, i) => (
                    <div 
                      key={i} 
                      style={{ 
                        padding: '0.75rem', 
                        backgroundColor: 'var(--slate-50)', 
                        border: '1px solid var(--border-color)', 
                        borderRadius: '6px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: 600, fontSize: '0.85rem', color: 'var(--slate-800)' }}>
                          {b.barrier}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--sif-high)' }}>
                          {b.barrier_status}
                        </div>
                      </div>
                      <div style={{ textAlign: 'right', fontWeight: 600, fontSize: '0.85rem', color: 'var(--slate-700)' }}>
                        {b.count}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}
