import React, { useState, useEffect } from 'react';
import { 
  CheckSquare, 
  AlertTriangle, 
  CheckCircle, 
  XCircle, 
  Edit3, 
  RefreshCw, 
  Clock, 
  UserCheck, 
  FileText,
  ShieldCheck,
  Send,
  Sliders,
  History,
  Info
} from 'lucide-react';
import { fetchReports, submitHSEReview } from '../services/api';

export default function HSEReviewPage({ onSelectReport }) {
  const [reports, setReports] = useState([]);
  const [filterMode, setFilterMode] = useState('pending'); // 'pending' | 'confirmed' | 'corrected' | 'rejected' | 'all'
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Active quick review state
  const [reviewingReportId, setReviewingReportId] = useState(null);
  const [correctedPriority, setCorrectedPriority] = useState('MEDIUM');
  const [correctedActivity, setCorrectedActivity] = useState('');
  const [correctedHazard, setCorrectedHazard] = useState('');
  const [correctedBarrier, setCorrectedBarrier] = useState('');
  const [reviewerId, setReviewerId] = useState('HSE-OFFICER-01');
  const [comments, setComments] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [actionSuccess, setActionSuccess] = useState(null);

  const loadQueue = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchReports({ limit: 100 });
      setReports(data.items || []);
    } catch (err) {
      console.error("Error loading HSE review queue:", err);
      setError(err.message || "Failed to load review queue from API");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQueue();
  }, []);

  const openCorrectionForm = (report) => {
    if (reviewingReportId === report.report_id) {
      setReviewingReportId(null);
      return;
    }
    setReviewingReportId(report.report_id);
    setCorrectedPriority(report.final_priority || report.priority || 'MEDIUM');
    setCorrectedActivity(report.final_activity || report.activity || '');
    setCorrectedHazard(report.final_hazard || report.hazard || '');
    setCorrectedBarrier(report.final_barrier || report.barrier || '');
    setComments('');
  };

  const handleReviewAction = async (reportId, decision, customData = {}) => {
    setActionLoading(true);
    setActionSuccess(null);
    setError(null);
    try {
      await submitHSEReview({
        reportId: reportId,
        reviewer_id: reviewerId,
        decision: decision,
        correctedPriority: decision === 'corrected' ? (customData.priority || correctedPriority) : null,
        correctedActivity: decision === 'corrected' ? (customData.activity || correctedActivity || null) : null,
        correctedHazard: decision === 'corrected' ? (customData.hazard || correctedHazard || null) : null,
        correctedBarrier: decision === 'corrected' ? (customData.barrier || correctedBarrier || null) : null,
        comments: customData.comments || comments.trim() || undefined,
      });

      setActionSuccess(`HSE Determination recorded for ${reportId}: ${decision.toUpperCase()}`);
      setReviewingReportId(null);
      setComments('');
      await loadQueue();
    } catch (err) {
      setError(err.message || "Failed to submit review");
    } finally {
      setActionLoading(false);
    }
  };

  // Filter queue
  const displayReports = reports.filter(r => {
    if (filterMode === 'pending') return !r.hse_reviewed;
    if (filterMode === 'confirmed') return r.hse_reviewed && r.review_decision === 'CONFIRM';
    if (filterMode === 'corrected') return r.hse_reviewed && r.review_decision === 'CORRECT';
    if (filterMode === 'rejected') return r.hse_reviewed && r.review_decision === 'REJECT';
    if (filterMode === 'all') return true;
    return true;
  });

  const counts = {
    pending: reports.filter(r => !r.hse_reviewed).length,
    confirmed: reports.filter(r => r.hse_reviewed && r.review_decision === 'CONFIRM').length,
    corrected: reports.filter(r => r.hse_reviewed && r.review_decision === 'CORRECT').length,
    rejected: reports.filter(r => r.hse_reviewed && r.review_decision === 'REJECT').length,
    all: reports.length,
  };

  return (
    <div className="hse-review-page">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h2>HSE Officer Review & Verification Queue</h2>
          <p>Human-in-the-loop oversight: validate AI precursor triage, accept or adjust risk ratings (non-destructive)</p>
        </div>
        <button className="btn btn-outline" onClick={loadQueue}>
          <RefreshCw size={14} /> Refresh Queue
        </button>
      </div>

      {/* Success banner */}
      {actionSuccess && (
        <div style={{ 
          backgroundColor: '#f0fdf4', 
          border: '1px solid #bbf7d0', 
          color: '#166534', 
          padding: '0.85rem 1rem', 
          borderRadius: '6px', 
          marginBottom: '1.25rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          fontSize: '0.875rem' 
        }}>
          <CheckCircle size={16} />
          <span>{actionSuccess}</span>
        </div>
      )}

      {error && (
        <div style={{ 
          backgroundColor: '#fef2f2', 
          border: '1px solid #fecaca', 
          color: '#991b1b', 
          padding: '0.85rem', 
          borderRadius: '6px', 
          marginBottom: '1.25rem',
          fontSize: '0.85rem' 
        }}>
          {error}
        </div>
      )}

      {/* Filter Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1.25rem' }}>
        <button
          className={`btn ${filterMode === 'pending' ? 'btn-primary' : 'btn-outline'}`}
          onClick={() => setFilterMode('pending')}
        >
          <Clock size={14} />
          Pending Review ({counts.pending})
        </button>
        <button
          className={`btn ${filterMode === 'confirmed' ? 'btn-primary' : 'btn-outline'}`}
          onClick={() => setFilterMode('confirmed')}
        >
          <CheckCircle size={14} />
          Confirmed ({counts.confirmed})
        </button>
        <button
          className={`btn ${filterMode === 'corrected' ? 'btn-primary' : 'btn-outline'}`}
          onClick={() => setFilterMode('corrected')}
        >
          <Edit3 size={14} />
          Corrected ({counts.corrected})
        </button>
        <button
          className={`btn ${filterMode === 'rejected' ? 'btn-primary' : 'btn-outline'}`}
          onClick={() => setFilterMode('rejected')}
        >
          <XCircle size={14} />
          Rejected ({counts.rejected})
        </button>
        <button
          className={`btn ${filterMode === 'all' ? 'btn-primary' : 'btn-outline'}`}
          onClick={() => setFilterMode('all')}
        >
          All Reports ({counts.all})
        </button>
      </div>

      {/* Review Queue Cards */}
      {loading ? (
        <div className="loading-state">
          <RefreshCw size={24} className="spin" />
          <p>Loading review queue...</p>
        </div>
      ) : displayReports.length === 0 ? (
        <div className="card-panel">
          <div className="card-panel-body" style={{ textAlign: 'center', padding: '3rem 1rem' }}>
            <CheckCircle size={36} color="#16a34a" style={{ marginBottom: '0.75rem' }} />
            <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>Queue is Clear!</h3>
            <p style={{ color: '#64748b', fontSize: '0.85rem', marginTop: '0.35rem' }}>
              No reports currently in the {filterMode} view.
            </p>
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {displayReports.map((report) => (
            <div 
              key={report.report_id} 
              className="card-panel" 
              style={{ 
                borderLeft: `5px solid ${
                  (report.final_priority || report.priority) === 'HIGH' ? 'var(--sif-high)' : 
                  (report.final_priority || report.priority) === 'MEDIUM' ? 'var(--sif-medium)' : 'var(--sif-low)'
                }` 
              }}
            >
              <div className="card-panel-body">
                {/* Header row: ID, Badges, Prob, Details button */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.75rem', marginBottom: '0.75rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
                    <span className="mono-id" style={{ fontSize: '0.95rem' }}>{report.report_id}</span>
                    
                    {/* Status Badge */}
                    {report.hse_reviewed ? (
                      <span className={`badge-priority badge-status-${report.review_decision}`}>
                        <CheckCircle size={12} style={{ marginRight: '3px' }} />
                        {report.review_decision} BY {report.reviewer_id || "OFFICER"}
                      </span>
                    ) : (
                      <span className="badge-priority badge-status-pending">
                        <Clock size={12} style={{ marginRight: '3px' }} />
                        Awaiting Verification
                      </span>
                    )}

                    <span style={{ fontSize: '0.8rem', color: '#64748b' }}>
                      Model SIF Prob: <strong>{(report.sif_probability * 100).toFixed(1)}%</strong>
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <button 
                      className="btn btn-outline" 
                      style={{ padding: '0.25rem 0.6rem', fontSize: '0.75rem' }}
                      onClick={() => onSelectReport(report.report_id)}
                    >
                      <FileText size={12} style={{ marginRight: '4px' }} />
                      Full Details & Audit Trail
                    </button>
                  </div>
                </div>

                {/* Narrative text */}
                <div style={{ 
                  backgroundColor: '#f8fafc', 
                  border: '1px solid #e2e8f0', 
                  borderRadius: '6px', 
                  padding: '0.75rem 1rem', 
                  fontSize: '0.875rem',
                  lineHeight: 1.5,
                  color: '#1e293b',
                  marginBottom: '0.75rem'
                }}>
                  {report.report_text}
                </div>

                {/* Side-by-Side: AI Result vs HSE Result */}
                <div style={{ 
                  display: 'grid', 
                  gridTemplateColumns: '1fr 1fr', 
                  gap: '1rem', 
                  backgroundColor: '#fafbfc', 
                  border: '1px solid #e2e8f0', 
                  borderRadius: '6px', 
                  padding: '0.75rem', 
                  marginBottom: '0.85rem' 
                }}>
                  {/* AI Result */}
                  <div style={{ borderRight: '1px solid #e2e8f0', paddingRight: '0.75rem' }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#2563eb', marginBottom: '0.35rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                      <Info size={13} />
                      <span>Original AI Prediction (Immutable)</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
                      <span className={`badge-priority ${report.priority}`}>{report.priority}</span>
                      <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                        ({(report.sif_probability * 100).toFixed(1)}%)
                      </span>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#475569', lineHeight: 1.4 }}>
                      <div>Activity: <strong>{report.activity || "None"}</strong></div>
                      <div>Hazard: <strong>{report.hazard || "None"}</strong></div>
                      <div>Barrier: <strong>{report.barrier || "None"}</strong></div>
                    </div>
                  </div>

                  {/* HSE Result */}
                  <div style={{ paddingLeft: '0.25rem' }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#16a34a', marginBottom: '0.35rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                      <ShieldCheck size={13} />
                      <span>HSE Officer Determination</span>
                    </div>
                    {report.hse_reviewed ? (
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
                          <span className={`badge-priority ${report.final_priority || report.priority}`}>
                            {report.final_priority || report.priority}
                          </span>
                          <span style={{ fontSize: '0.75rem', color: '#166534', fontWeight: 600 }}>
                            {report.review_decision}
                          </span>
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#475569', lineHeight: 1.4 }}>
                          <div>Activity: <strong>{report.final_activity || report.activity || "None"}</strong></div>
                          <div>Hazard: <strong>{report.final_hazard || report.hazard || "None"}</strong></div>
                          <div>Barrier: <strong>{report.final_barrier || report.barrier || "None"}</strong></div>
                        </div>
                        {report.review_comments && (
                          <div style={{ fontSize: '0.725rem', color: '#64748b', fontStyle: 'italic', marginTop: '0.25rem' }}>
                            "{report.review_comments}"
                          </div>
                        )}
                      </div>
                    ) : (
                      <div style={{ fontSize: '0.8rem', color: '#94a3b8', fontStyle: 'italic', paddingTop: '0.5rem' }}>
                        Pending review. AI triage is operating as provisional guidance.
                      </div>
                    )}
                  </div>
                </div>

                {/* Quick Action Buttons: CONFIRM, REJECT, CORRECT */}
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', paddingTop: '0.5rem', borderTop: '1px solid #e2e8f0' }}>
                  <button
                    className="btn btn-confirm"
                    style={{ fontSize: '0.775rem', padding: '0.35rem 0.75rem' }}
                    disabled={actionLoading}
                    onClick={() => handleReviewAction(report.report_id, 'confirmed')}
                  >
                    <CheckCircle size={13} />
                    CONFIRM
                  </button>

                  <button
                    className="btn btn-reject"
                    style={{ fontSize: '0.775rem', padding: '0.35rem 0.75rem' }}
                    disabled={actionLoading}
                    onClick={() => handleReviewAction(report.report_id, 'rejected')}
                  >
                    <XCircle size={13} />
                    REJECT
                  </button>

                  <button
                    className="btn btn-correct"
                    style={{ fontSize: '0.775rem', padding: '0.35rem 0.75rem' }}
                    disabled={actionLoading}
                    onClick={() => openCorrectionForm(report)}
                  >
                    <Edit3 size={13} />
                    {reviewingReportId === report.report_id ? "Cancel Correction" : "CORRECT"}
                  </button>
                </div>

                {/* Multi-Dimensional Inline Correction Form */}
                {reviewingReportId === report.report_id && (
                  <div style={{ 
                    marginTop: '1rem', 
                    padding: '1rem', 
                    backgroundColor: '#fffbeb', 
                    border: '1px solid #fde68a', 
                    borderRadius: '8px' 
                  }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#92400e', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      <Sliders size={15} />
                      <span>HSE Officer Multi-Dimensional Correction (Priority, Activity, Hazard, Barrier):</span>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem', marginBottom: '0.75rem' }}>
                      {/* Priority */}
                      <div>
                        <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#78350f', marginBottom: '0.25rem' }}>
                          Priority:
                        </label>
                        <select
                          className="filter-select"
                          style={{ width: '100%' }}
                          value={correctedPriority}
                          onChange={(e) => setCorrectedPriority(e.target.value)}
                        >
                          <option value="HIGH">HIGH (SIF Precursor)</option>
                          <option value="MEDIUM">MEDIUM (Elevated Risk)</option>
                          <option value="LOW">LOW (Controlled)</option>
                        </select>
                      </div>

                      {/* Activity */}
                      <div>
                        <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#78350f', marginBottom: '0.25rem' }}>
                          Activity:
                        </label>
                        <input
                          type="text"
                          className="search-input"
                          style={{ width: '100%', fontSize: '0.8rem' }}
                          value={correctedActivity}
                          onChange={(e) => setCorrectedActivity(e.target.value)}
                          placeholder="e.g. Electrical Maintenance"
                        />
                      </div>

                      {/* Hazard */}
                      <div>
                        <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#78350f', marginBottom: '0.25rem' }}>
                          Hazard:
                        </label>
                        <input
                          type="text"
                          className="search-input"
                          style={{ width: '100%', fontSize: '0.8rem' }}
                          value={correctedHazard}
                          onChange={(e) => setCorrectedHazard(e.target.value)}
                          placeholder="e.g. Arc Flash / Stored Energy"
                        />
                      </div>

                      {/* Barrier */}
                      <div>
                        <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#78350f', marginBottom: '0.25rem' }}>
                          Barrier / Control:
                        </label>
                        <input
                          type="text"
                          className="search-input"
                          style={{ width: '100%', fontSize: '0.8rem' }}
                          value={correctedBarrier}
                          onChange={(e) => setCorrectedBarrier(e.target.value)}
                          placeholder="e.g. LOTO Verification / Interlock"
                        />
                      </div>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '160px 1fr auto', gap: '0.65rem', alignItems: 'center' }}>
                      <input
                        type="text"
                        className="search-input"
                        placeholder="Officer ID"
                        value={reviewerId}
                        onChange={(e) => setReviewerId(e.target.value)}
                        style={{ fontSize: '0.8rem' }}
                      />

                      <input
                        type="text"
                        className="search-input"
                        placeholder="Reason / justification for correction (mandatory for audit trail)..."
                        value={comments}
                        onChange={(e) => setComments(e.target.value)}
                        style={{ fontSize: '0.8rem' }}
                      />

                      <button
                        className="btn btn-primary"
                        style={{ padding: '0.45rem 1rem', fontSize: '0.8rem' }}
                        disabled={actionLoading}
                        onClick={() => handleReviewAction(report.report_id, 'corrected', {
                          priority: correctedPriority,
                          activity: correctedActivity,
                          hazard: correctedHazard,
                          barrier: correctedBarrier,
                          comments: comments,
                        })}
                      >
                        <Send size={13} /> Save Determination
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
