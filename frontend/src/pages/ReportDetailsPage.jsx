import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { 
  ArrowLeft, 
  CheckCircle, 
  XCircle, 
  Edit3, 
  AlertTriangle, 
  FileText, 
  Clock,
  MapPin,
  ChevronRight,
  Download,
  CheckSquare,
  ShieldCheck,
  Activity,
  Layers,
  ChevronDown,
  ChevronUp,
  Sliders
} from 'lucide-react';
import { 
  fetchReportById, 
  fetchSimilarReports, 
  submitHSEReview, 
  fetchAuditTrail
} from '../services/api';
import { PriorityBadge, StatusBadge, Skeleton, ErrorState } from '../components/ui';
import TechnicalAssessmentDrawer from '../components/TechnicalAssessmentDrawer';

export default function ReportDetailsPage({ reportId, onBack, onReviewSubmitted }) {
  const location = useLocation();
  const effectiveReportId = reportId || (location.state && location.state.reportId);
  const [report, setReport] = useState(null);
  const [similarReports, setSimilarReports] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [drawerAssessment, setDrawerAssessment] = useState(null);

  // HSE Decision State
  const [actionInProgress, setActionInProgress] = useState(false);
  const [showHSEReview, setShowHSEReview] = useState(false);
  const [decision, setDecision] = useState('confirmed');
  const [comments, setComments] = useState('');
  
  // Correction State
  const [correctedPriority, setCorrectedPriority] = useState('');
  const [correctedActivity, setCorrectedActivity] = useState('');
  const [correctedHazard, setCorrectedHazard] = useState('');
  const [correctedBarrier, setCorrectedBarrier] = useState('');

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [data, simRes, auditRes] = await Promise.all([
        fetchReportById(effectiveReportId),
        fetchSimilarReports(effectiveReportId, 3, 0.40).catch(() => ({ similar_reports: [] })),
        fetchAuditTrail(effectiveReportId).catch(() => ({ logs: [] })),
      ]);
      setReport(data);
      setSimilarReports(simRes?.similar_reports || []);
      setAuditLogs(auditRes?.logs || data.audit_trail || []);
      
      // Init corrections to current AI outputs
      setCorrectedPriority(data.final_priority || data.analysis?.priority || 'MEDIUM');
      setCorrectedActivity(data.final_activity || data.analysis?.activity || '');
      setCorrectedHazard(data.final_hazard || data.analysis?.hazard || '');
      setCorrectedBarrier(data.final_barrier || data.analysis?.barrier || '');
      
    } catch (err) {
      setError(err.message || "Failed to load report details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (effectiveReportId) loadData();
  }, [effectiveReportId]);

  const handleReviewSubmit = async () => {
    setActionInProgress(true);
    try {
      const payload = {
        reportId: report.report_id,
        reviewerId: 'HSE-OFFICER-01',
        decision: decision,
        comments: comments.trim() || undefined,
      };
      if (decision === 'corrected') {
        payload.correctedPriority = correctedPriority;
        payload.correctedActivity = correctedActivity.trim() || undefined;
        payload.correctedHazard = correctedHazard.trim() || undefined;
        payload.correctedBarrier = correctedBarrier.trim() || undefined;
      }
      
      const res = await submitHSEReview(payload);
      setShowHSEReview(false);
      await loadData();
      if (onReviewSubmitted) onReviewSubmitted(res);
    } catch (err) {
      alert("Failed to submit review: " + err.message);
    } finally {
      setActionInProgress(false);
    }
  };

  const handleDownloadOriginal = () => {
    window.open(`/api/v1/reports/${report.report_id}/download/original`, '_blank');
  };

  const handleDownloadAssessment = () => {
    window.open(`/api/v1/reports/${report.report_id}/download/assessment`, '_blank');
  };

  if (loading) return <div className="page-container"><Skeleton height="400px" /></div>;
  if (error || !report) return <div className="page-container"><ErrorState message={error} onRetry={loadData} /></div>;

  const analysis = report.analysis || report;
  const isReviewed = report.hse_reviewed;

  return (
    <div className="page-container">
      {/* HEADER */}
      <div className="report-header">
        <button className="btn btn-ghost" onClick={onBack} style={{ paddingLeft: 0, marginBottom: '1rem' }}>
          <ArrowLeft size={16} /> Back to Reports
        </button>
        
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '0.5rem' }}>
              <h1 style={{ margin: 0, fontSize: '1.75rem', color: 'var(--slate-800)' }}>
                {report.report_id}
              </h1>
              <PriorityBadge priority={report.final_priority || analysis.priority} />
              <StatusBadge status={isReviewed ? (report.review_decision === 'confirmed' ? 'Confirmed' : report.review_decision === 'corrected' ? 'Corrected' : 'Rejected') : 'Pending'} />
              <button 
                className="btn btn-ghost btn-sm"
                onClick={() => setDrawerAssessment(report)}
                style={{ padding: '0.25rem 0.5rem', fontSize: '0.8rem', gap: '0.25rem' }}
              >
                <Sliders size={14} /> Assessment details
              </button>
            </div>
            <p style={{ color: 'var(--text-muted)', margin: 0, fontSize: 'var(--text-sm)' }}>{report.report_type || 'Safety Observation'} · {new Date(report.created_at).toLocaleDateString()}</p>
          </div>
          
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button className="btn btn-outline" onClick={handleDownloadOriginal}><Download size={14} /> Original</button>
            <button className="btn btn-outline" onClick={handleDownloadAssessment}><Download size={14} /> Assessment</button>
            {!isReviewed && (
              <button className="btn btn-primary" onClick={() => {
                setShowHSEReview(true);
                setTimeout(() => {
                  document.getElementById('hse-review-section')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }, 100);
              }}>
                <CheckSquare size={14} /> HSE Review
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="dashboard-grid" style={{ marginTop: '2rem' }}>
        
        {/* MAIN COLUMN */}
        <div className="dashboard-main-column">
          
          {/* SECTION 1: Observation */}
          <div className="panel">
            <div className="panel-header"><h2>Observation</h2></div>
            <div className="panel-content">
              <div className="report-narrative" style={{ fontSize: '1.1rem', lineHeight: 1.6, color: 'var(--slate-800)', marginBottom: '1.5rem', padding: '1rem', backgroundColor: 'var(--slate-50)', borderRadius: '8px' }}>
                "{report.report_text}"
              </div>
              
              <div className="meta-grid" style={{ marginTop: '1.5rem' }}>
                <div className="meta-item">
                  <span className="meta-label">Location</span>
                  <span className="meta-value"><MapPin size={14}/> {report.location || 'Not specified'}</span>
                </div>
                <div className="meta-item">
                  <span className="meta-label">Report Type</span>
                  <span className="meta-value"><FileText size={14}/> {report.report_type || 'Observation'}</span>
                </div>
                <div className="meta-item">
                  <span className="meta-label">Submitted</span>
                  <span className="meta-value"><Clock size={14}/> {new Date(report.created_at).toLocaleString()}</span>
                </div>
                <div className="meta-item">
                  <span className="meta-label">Source</span>
                  <span className="meta-value">{report.source || 'Manual Entry'}</span>
                </div>
              </div>
            </div>
          </div>

          {/* SECTION 2: Safety Assessment */}
          <div className="panel">
            <div className="panel-header"><h2>Safety Assessment</h2></div>
            <div className="panel-content">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="assessment-card">
                  <span className="card-label">Activity</span>
                  <strong>{report.final_activity || analysis.activity || 'Unknown'}</strong>
                </div>
                <div className="assessment-card">
                  <span className="card-label">Hazard</span>
                  <strong>{report.final_hazard || analysis.hazard || 'None detected'}</strong>
                </div>
                <div className="assessment-card">
                  <span className="card-label">Critical Barrier</span>
                  <strong>{report.final_barrier || analysis.barrier || 'None mentioned'}</strong>
                </div>
                <div className="assessment-card">
                  <span className="card-label">Barrier Status</span>
                  <strong>{analysis.barrier_status || 'Not Verified'}</strong>
                </div>
              </div>
            </div>
          </div>

          {/* SECTION 3: Why this needs attention */}
          <div className="panel">
            <div className="panel-header"><h2>Why This Needs Attention</h2></div>
            <div className="panel-content">
              <p style={{ fontSize: '1.05rem', color: 'var(--slate-700)', lineHeight: 1.6 }}>
                {analysis.explanation || "No explanation provided by the decision engine."}
              </p>
            </div>
          </div>

          {/* SECTION 4: Critical Controls */}
          <div className="panel">
            <div className="panel-header"><h2>Critical Controls</h2></div>
            <div className="panel-content">
              {analysis.triggered_rules && analysis.triggered_rules.length > 0 ? (
                <div className="rules-list" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  {analysis.triggered_rules.map((rule, idx) => (
                    <div key={idx} className="rule-card" style={{ padding: '1rem', border: '1px solid var(--slate-200)', borderRadius: '8px', borderLeft: '4px solid var(--sif-high)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                        <strong>{rule.rule_name}</strong>
                        <PriorityBadge priority={rule.severity_label} />
                      </div>
                      <p style={{ fontSize: '0.9rem', color: 'var(--slate-600)', margin: '0 0 0.5rem 0' }}>{rule.explanation}</p>
                      {rule.reference && <span style={{ fontSize: '0.8rem', color: 'var(--primary)' }}>Ref: {rule.reference}</span>}
                    </div>
                  ))}
                </div>
              ) : (
                <p style={{ color: 'var(--slate-500)' }}>No specific critical control rules triggered.</p>
              )}
            </div>
          </div>

          {/* SECTION 7: HSE Decision (If reviewed) */}
          {isReviewed && (
            <div className="panel" style={{ border: '1px solid var(--accent-blue)' }}>
              <div className="panel-header" style={{ backgroundColor: 'var(--slate-50)' }}>
                <h2>HSE Decision: {report.review_decision.toUpperCase()}</h2>
              </div>
              <div className="panel-content">
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
                  <div>
                    <h4 style={{ color: 'var(--slate-500)', fontSize: '0.8rem', textTransform: 'uppercase', marginBottom: '0.5rem' }}>Original AI Assessment</h4>
                    <p>Priority: <strong>{analysis.priority}</strong></p>
                    <p>Activity: {analysis.activity}</p>
                    <p>Hazard: {analysis.hazard}</p>
                  </div>
                  <div>
                    <h4 style={{ color: 'var(--slate-500)', fontSize: '0.8rem', textTransform: 'uppercase', marginBottom: '0.5rem' }}>Final HSE Determination</h4>
                    <p>Priority: <strong>{report.final_priority}</strong></p>
                    <p>Activity: {report.final_activity}</p>
                    <p>Hazard: {report.final_hazard}</p>
                  </div>
                </div>
                <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--slate-100)' }}>
                  <p><strong>Reviewer:</strong> {report.reviewer_id} at {new Date(report.reviewed_at).toLocaleString()}</p>
                  {report.review_comments && <p><strong>Comments:</strong> {report.review_comments}</p>}
                </div>
              </div>
            </div>
          )}

          {/* HSE REVIEW MODAL INLINE (If active) */}
          {showHSEReview && !isReviewed && (
            <div id="hse-review-section" className="panel" style={{ border: '2px solid var(--accent-blue)' }}>
              <div className="panel-header"><h2>Submit HSE Decision</h2></div>
              <div className="panel-content">
                <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', cursor: 'pointer' }}><input type="radio" name="decision" checked={decision === 'confirmed'} onChange={() => setDecision('confirmed')} /> Confirm</label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', cursor: 'pointer' }}><input type="radio" name="decision" checked={decision === 'corrected'} onChange={() => setDecision('corrected')} /> Correct</label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', cursor: 'pointer' }}><input type="radio" name="decision" checked={decision === 'rejected'} onChange={() => setDecision('rejected')} /> Reject</label>
                </div>
                
                {decision === 'corrected' && (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
                      <div className="form-group">
                        <label className="form-label">Priority</label>
                        <select className="filter-select" value={correctedPriority} onChange={e => setCorrectedPriority(e.target.value)} style={{ width: '100%' }}>
                        <option value="LOW">LOW</option>
                        <option value="MEDIUM">MEDIUM</option>
                        <option value="HIGH">HIGH</option>
                      </select>
                      </div>
                      <div className="form-group">
                        <label className="form-label">Activity</label>
                        <input type="text" className="form-input" value={correctedActivity} onChange={e => setCorrectedActivity(e.target.value)} />
                      </div>
                      <div className="form-group">
                        <label className="form-label">Hazard</label>
                        <input type="text" className="form-input" value={correctedHazard} onChange={e => setCorrectedHazard(e.target.value)} />
                      </div>
                    </div>
                )}
                
                <div className="form-group">
                  <label className="form-label">Comments</label>
                  <textarea className="form-textarea" value={comments} onChange={e => setComments(e.target.value)} rows={3} placeholder="Provide justification..." />
                </div>
                
                <div style={{ display: 'flex', gap: '1rem' }}>
                  <button className="btn btn-primary" onClick={handleReviewSubmit} disabled={actionInProgress}>
                    {actionInProgress ? 'Saving...' : 'Submit Decision'}
                  </button>
                  <button className="btn btn-outline" onClick={() => setShowHSEReview(false)}>Cancel</button>
                </div>
              </div>
            </div>
          )}


        </div>

        {/* SIDEBAR COLUMN */}
        <div className="dashboard-side-column">
          
          {/* SECTION 8: Activity Timeline */}
          <div className="panel">
            <div className="panel-header"><h2>Activity Timeline</h2></div>
            <div className="panel-content">
               <div className="timeline">
                  {auditLogs.map((log) => (
                    <div key={log.id} className="timeline-item">
                      <div className="timeline-indicator" />
                      <div className="timeline-content">
                        <div className="timeline-time">
                          {new Date(log.created_at).toLocaleString([], {month:'short', day:'numeric', hour: '2-digit', minute:'2-digit'})}
                        </div>
                        <div className="timeline-action">
                          <strong>{log.actor_id}</strong> {log.action.toLowerCase().replace('_', ' ')}
                        </div>
                        {log.details && Object.keys(log.details).length > 0 && (
                          <div className="timeline-details">
                            {typeof log.details === 'object' ? Object.entries(log.details).map(([k,v]) => `${k}: ${v}`).join(' | ') : log.details}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
            </div>
          </div>

          {/* SECTION 6: Similar Reports */}
          <div className="panel">
            <div className="panel-header"><h2>Similar Reports</h2></div>
            <div className="panel-content">
              {similarReports.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  {similarReports.map(sim => (
                    <div key={sim.report_id} style={{ padding: '0.75rem', border: '1px solid var(--slate-200)', borderRadius: '6px', fontSize: '0.9rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                        <strong style={{ color: 'var(--primary)' }}>{sim.report_id}</strong>
                        <span style={{ fontSize: '0.8rem', color: 'var(--slate-500)' }}>{(sim.similarity_score * 100).toFixed(0)}% Match</span>
                      </div>
                      <p style={{ margin: 0, color: 'var(--slate-700)', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                        {sim.report_text}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <p style={{ color: 'var(--slate-500)', fontSize: '0.9rem' }}>No highly similar reports found in the operational database.</p>
              )}
            </div>
          </div>
          
        </div>
      </div>
      
      {/* Technical Drawer */}
      <TechnicalAssessmentDrawer 
        isOpen={!!drawerAssessment} 
        onClose={() => setDrawerAssessment(null)} 
        assessment={drawerAssessment?.analysis || drawerAssessment} 
      />
    </div>
  );
}
