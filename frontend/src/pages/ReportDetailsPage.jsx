import React, { useState, useEffect } from 'react';
import { 
  ArrowLeft, 
  CheckCircle, 
  XCircle, 
  Edit3, 
  AlertTriangle, 
  ShieldCheck, 
  FileText, 
  Info, 
  Tag, 
  CheckCircle2,
  Clock,
  Sparkles,
  MapPin,
  Wrench,
  ChevronRight,
  Send,
  GitBranch,
  History,
  MessageSquare,
  UserCheck
} from 'lucide-react';
import { 
  fetchReportById, 
  fetchSimilarReports, 
  submitHSEReview, 
  fetchAuditTrail, 
  submitFeedback 
} from '../services/api';

export default function ReportDetailsPage({ reportId, onBack, onReviewSubmitted, onSelectReport, onNavigateTab }) {
  const [report, setReport] = useState(null);
  const [similarReports, setSimilarReports] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Review interaction state
  const [actionInProgress, setActionInProgress] = useState(false);
  const [showCorrectModal, setShowCorrectModal] = useState(false);
  const [correctedPriority, setCorrectedPriority] = useState('MEDIUM');
  const [correctedActivity, setCorrectedActivity] = useState('');
  const [correctedHazard, setCorrectedHazard] = useState('');
  const [correctedBarrier, setCorrectedBarrier] = useState('');
  const [reviewerId, setReviewerId] = useState('HSE-OFFICER-01');
  const [officerComments, setOfficerComments] = useState('');
  const [reviewMessage, setReviewMessage] = useState(null);

  // Feedback state
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);
  const [feedbackType, setFeedbackType] = useState('label_correction');
  const [feedbackNotes, setFeedbackNotes] = useState('');
  const [feedbackSuccess, setFeedbackSuccess] = useState(null);

  const loadReportDetails = async () => {
    setLoading(true);
    setError(null);
    try {
      const [data, simRes, auditRes] = await Promise.all([
        fetchReportById(reportId),
        fetchSimilarReports(reportId, 4, 0.35).catch(() => ({ similar_reports: [] })),
        fetchAuditTrail(reportId).catch(() => ({ logs: [] })),
      ]);
      setReport(data);
      setSimilarReports(simRes?.similar_reports || []);
      setAuditLogs(auditRes?.logs || data.audit_trail || []);
      setCorrectedPriority(data.final_priority || data.priority || 'MEDIUM');
      setCorrectedActivity(data.final_activity || data.activity || '');
      setCorrectedHazard(data.final_hazard || data.hazard || '');
      setCorrectedBarrier(data.final_barrier || data.barrier || '');
    } catch (err) {
      console.error("Error fetching report details:", err);
      setError(err.message || `Failed to retrieve details for report ${reportId}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (reportId) {
      loadReportDetails();
    }
  }, [reportId]);

  const handleAction = async (decision) => {
    setActionInProgress(true);
    setError(null);
    try {
      const payload = {
        reportId: report.report_id,
        reviewerId: reviewerId.trim() || 'HSE-OFFICER-01',
        decision: decision,
        comments: officerComments.trim() || undefined,
      };
      if (decision === 'corrected') {
        payload.correctedPriority = correctedPriority;
        payload.correctedActivity = correctedActivity.trim() || undefined;
        payload.correctedHazard = correctedHazard.trim() || undefined;
        payload.correctedBarrier = correctedBarrier.trim() || undefined;
      }
      const res = await submitHSEReview(payload);

      setReviewMessage({
        type: decision,
        text: `HSE Review recorded: Decision ${decision.toUpperCase()} applied. Both original AI output and HSE determination are preserved.`,
      });

      setShowCorrectModal(false);
      await loadReportDetails();

      if (onReviewSubmitted) {
        onReviewSubmitted(res);
      }
    } catch (err) {
      setError(err.message || "Failed to submit HSE review determination");
    } finally {
      setActionInProgress(false);
    }
  };

  const handleFeedbackSubmit = async (e) => {
    e.preventDefault();
    if (!feedbackNotes.trim()) return;
    try {
      await submitFeedback({
        reportId: report.report_id,
        feedbackType: feedbackType,
        notes: feedbackNotes.trim(),
        userId: reviewerId.trim() || 'HSE-OFFICER-01',
      });
      setFeedbackSuccess("Officer feedback annotation saved and logged in audit trail.");
      setFeedbackNotes('');
      setShowFeedbackModal(false);
      await loadReportDetails();
    } catch (err) {
      setError(err.message || "Failed to submit feedback");
    }
  };

  if (loading) {
    return (
      <div className="loading-state">
        <Clock size={28} className="spin" />
        <p>Retrieving full decision engine analysis for {reportId}...</p>
      </div>
    );
  }

  if (error && !report) {
    return (
      <div className="empty-state">
        <AlertTriangle size={36} color="#dc2626" style={{ marginBottom: '0.75rem' }} />
        <h3>Report Not Found</h3>
        <p style={{ marginTop: '0.25rem', color: '#64748b' }}>{error}</p>
        <button className="btn btn-outline" style={{ marginTop: '1rem' }} onClick={onBack}>
          <ArrowLeft size={14} /> Back to Reports
        </button>
      </div>
    );
  }

  return (
    <div className="report-details-page">
      {/* Navigation & Action Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <button className="btn btn-outline" onClick={onBack}>
          <ArrowLeft size={14} /> Back to Reports List
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.8rem', color: '#64748b' }}>Report ID:</span>
          <span className="mono-id" style={{ fontSize: '0.9rem' }}>{report?.report_id}</span>
          {report?.report_id && report.report_id.startsWith('DEMO-SYN-') && (
            <span 
              style={{
                fontSize: '0.65rem',
                fontWeight: 700,
                padding: '0.15rem 0.45rem',
                borderRadius: '3px',
                backgroundColor: '#e0e7ff',
                color: '#3730a3',
                border: '1px solid #c7d2fe',
                letterSpacing: '0.03em',
              }}
              title="Synthetic Controlled Demo Record"
            >
              DEMO SYNTHETIC
            </span>
          )}
        </div>
      </div>

      {/* Confirmation feedback banner */}
      {reviewMessage && (
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
          <CheckCircle2 size={16} />
          <span>{reviewMessage.text}</span>
        </div>
      )}

      {feedbackSuccess && (
        <div style={{ 
          backgroundColor: '#eff6ff', 
          border: '1px solid #bfdbfe', 
          color: '#1e40af', 
          padding: '0.85rem 1rem', 
          borderRadius: '6px', 
          marginBottom: '1.25rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          fontSize: '0.875rem'
        }}>
          <MessageSquare size={16} />
          <span>{feedbackSuccess}</span>
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

      {/* Dual Review Panel: AI Original vs HSE Determination */}
      <div className="card-panel" style={{ marginBottom: '1.25rem', border: '1px solid #cbd5e1' }}>
        <div className="card-panel-header" style={{ background: '#f8fafc', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div className="card-panel-title">
            <ShieldCheck size={16} color="#0f172a" />
            <span>Human-in-the-Loop Determination: AI Model vs. HSE Officer Review</span>
            <span className="badge-neutral" style={{ fontSize: '0.65rem', fontWeight: 700, backgroundColor: '#eff6ff', color: '#1d4ed8' }}>
              Step 10: HSE Review
            </span>
          </div>
          <div>
            {report?.hse_reviewed ? (
              <span className={`badge badge-${report.review_decision === 'rejected' ? 'low' : report.final_priority ? report.final_priority.toLowerCase() : 'high'}`} style={{ fontWeight: 700, padding: '0.35rem 0.65rem' }}>
                HSE {report.review_decision?.toUpperCase()}
              </span>
            ) : report?.priority === 'HIGH' ? (
              <span className="badge-priority HIGH" style={{ fontWeight: 800, padding: '0.35rem 0.75rem', fontSize: '0.8rem' }}>
                HIGH PRIORITY → HSE REVIEW REQUIRED
              </span>
            ) : (
              <span className="badge badge-medium" style={{ background: '#fef3c7', color: '#92400e', fontWeight: 600, padding: '0.35rem 0.65rem' }}>
                ROUTINE MONITORING
              </span>
            )}
          </div>
        </div>
        <div className="card-panel-body" style={{ padding: '1rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
            {/* AI Original Output */}
            <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: '6px', padding: '0.9rem' }}>
              <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#2563eb', fontWeight: 700, marginBottom: '0.65rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <Sparkles size={14} /> Original AI Prediction (Preserved)
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', fontSize: '0.825rem' }}>
                <div>AI Priority: <strong style={{ color: report?.priority === 'HIGH' ? '#dc2626' : report?.priority === 'MEDIUM' ? '#d97706' : '#16a34a' }}>{report?.priority}</strong></div>
                <div>SIF Probability: <strong>{Math.round((report?.sif_probability || 0) * 100)}%</strong></div>
                <div>Activity: <strong>{report?.activity || 'Unspecified'}</strong></div>
                <div>Hazard: <strong>{report?.hazard || 'Unspecified'}</strong></div>
                <div>Barrier: <strong>{report?.barrier || 'Unspecified'}</strong> <span style={{ color: '#64748b' }}>({report?.barrier_status || 'Unknown'})</span></div>
              </div>
            </div>

            {/* HSE Final Determination */}
            <div style={{ background: '#fff', border: '1px solid #cbd5e1', borderRadius: '6px', padding: '0.9rem' }}>
              <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#0f172a', fontWeight: 700, marginBottom: '0.65rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <UserCheck size={14} color="#16a34a" /> HSE Officer Determination
              </div>
              {report?.hse_reviewed ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', fontSize: '0.825rem' }}>
                  <div>Final Priority: <strong style={{ color: report?.final_priority === 'HIGH' ? '#dc2626' : report?.final_priority === 'MEDIUM' ? '#d97706' : '#16a34a' }}>{report?.final_priority}</strong></div>
                  <div>Decision: <strong>{report?.review_decision?.toUpperCase()}</strong></div>
                  <div>Activity: <strong>{report?.final_activity || report?.activity || 'Unspecified'}</strong></div>
                  <div>Hazard: <strong>{report?.final_hazard || report?.hazard || 'Unspecified'}</strong></div>
                  <div>Barrier: <strong>{report?.final_barrier || report?.barrier || 'Unspecified'}</strong></div>
                  <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.2rem' }}>
                    Reviewed by <strong>{report?.reviewer_id}</strong> on {report?.reviewed_at ? new Date(report.reviewed_at).toLocaleString() : 'N/A'}
                  </div>
                  {report?.review_comments && (
                    <div style={{ fontSize: '0.75rem', color: '#334155', fontStyle: 'italic', marginTop: '0.25rem', background: '#f8fafc', padding: '0.35rem 0.5rem', borderRadius: '4px', border: '1px solid #e2e8f0' }}>
                      "{report.review_comments}"
                    </div>
                  )}
                </div>
              ) : (
                <div style={{ fontSize: '0.8rem', color: '#64748b', paddingTop: '0.5rem' }}>
                  Report is awaiting officer verification. Use the panel on the right to confirm, reject, or correct.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Main Grid: Left narrative & evidence, Right priority & HSE controls */}
      <div className="detail-grid">
        {/* Left Column: Narrative, Context, Rules, Evidence */}
        <div>
          {/* Original Report Narrative */}
          <div className="card-panel">
            <div className="card-panel-header">
              <div className="card-panel-title">
                <FileText size={16} color="#2563eb" />
                <span>Original Field Safety Observation Report</span>
              </div>
            </div>
            <div className="card-panel-body">
              <div className="narrative-box" id="detail-original-report">
                {report?.report_text || "Original text not stored."}
              </div>

              {/* Location & Equipment Footnotes */}
              <div style={{ display: 'flex', gap: '1.5rem', fontSize: '0.8rem', color: '#64748b' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <MapPin size={14} />
                  <span>Location: <strong>{report?.location || "Unspecified Zone"}</strong></span>
                </div>
                {report?.equipment && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                    <Wrench size={14} />
                    <span>Equipment: <strong>{report.equipment}</strong></span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Extracted Safety Context */}
          <div className="card-panel">
            <div className="card-panel-header">
              <div className="card-panel-title">
                <Sparkles size={16} color="#d97706" />
                <span>Extracted Safety Context & Barrier Status</span>
              </div>
              <span className="badge-neutral">Domain Rules & NLP</span>
            </div>
            <div className="card-panel-body">
              <div className="context-key-value-grid">
                {/* Activity */}
                <div className="context-card" id="detail-activity">
                  <div className="context-label">Activity</div>
                  <div className="context-value">{report?.activity || "None Identified"}</div>
                </div>

                {/* Hazard */}
                <div className="context-card" id="detail-hazard">
                  <div className="context-label">Hazard</div>
                  <div className="context-value">{report?.hazard || "None Identified"}</div>
                </div>

                {/* Barrier */}
                <div className="context-card" id="detail-barrier">
                  <div className="context-label">Barrier / Control</div>
                  <div className="context-value">{report?.barrier || "None Identified"}</div>
                </div>

                {/* Barrier Status */}
                <div className="context-card" id="detail-barrier-status">
                  <div className="context-label">Barrier Status</div>
                  <div className="context-value">
                    <span style={{ 
                      color: report?.barrier_status?.toLowerCase().includes('fail') || 
                             report?.barrier_status?.toLowerCase().includes('not') || 
                             report?.barrier_status?.toLowerCase().includes('absent') || 
                             report?.barrier_status?.toLowerCase().includes('compromised')
                        ? 'var(--sif-high)' 
                        : '#0f172a'
                    }}>
                      {report?.barrier_status || "Unknown"}
                    </span>
                  </div>
                </div>
              </div>

              {/* Physical Evidence Snippets */}
              <div style={{ marginTop: '1rem' }}>
                <span className="context-label" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <Tag size={12} /> Physical Evidence Identified in Narrative:
                </span>
                <div className="evidence-tags" id="detail-evidence">
                  {!report?.evidence || report.evidence.length === 0 ? (
                    <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>No explicit evidence fragments flagged.</span>
                  ) : (
                    report.evidence.map((ev, i) => (
                      <span key={i} className="evidence-tag">"{ev}"</span>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Triggered Deterministic Safety Rules */}
          <div className="card-panel">
            <div className="card-panel-header">
              <div className="card-panel-title">
                <AlertTriangle size={16} color="#dc2626" />
                <span>Triggered Deterministic Safety Rules ({report?.triggered_rules?.length || 0})</span>
              </div>
              <span className="badge-neutral">OSHA / IOGP Life Saving Rules</span>
            </div>
            <div className="card-panel-body" id="detail-triggered-rules">
              {!report?.triggered_rules || report.triggered_rules.length === 0 ? (
                <div style={{ padding: '0.5rem', color: '#64748b', fontSize: '0.85rem' }}>
                  No deterministic safety rule conditions were triggered by this report.
                </div>
              ) : (
                report.triggered_rules.map((rule, idx) => (
                  <div key={idx} className="rule-card">
                    <div className="rule-header">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span className="mono-id" style={{ fontSize: '0.75rem', backgroundColor: '#f1f5f9', padding: '0.1rem 0.35rem', borderRadius: '4px' }}>
                          {rule.rule_id}
                        </span>
                        <span className="rule-name">{rule.rule_name}</span>
                      </div>
                      <span className={`badge-priority ${rule.severity >= 3 ? 'HIGH' : rule.severity === 2 ? 'MEDIUM' : 'LOW'}`} style={{ fontSize: '0.65rem' }}>
                        {rule.severity_label || `Severity ${rule.severity}`}
                      </span>
                    </div>
                    <div className="rule-explanation">
                      {rule.explanation || "Mandatory safety verification failure."}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Semantically Similar Reports (Sentence Transformers all-MiniLM-L6-v2) */}
          <div className="card-panel">
            <div className="card-panel-header">
              <div className="card-panel-title">
                <GitBranch size={16} color="#0284c7" />
                <span>Semantically Similar Reports ({similarReports.length})</span>
              </div>
              <span className="badge-neutral">all-MiniLM-L6-v2 Cosine Similarity</span>
            </div>
            <div className="card-panel-body" id="detail-similar-reports">
              {similarReports.length === 0 ? (
                <div style={{ padding: '0.5rem', color: '#64748b', fontSize: '0.85rem' }}>
                  No prior reports exceeded the semantic similarity threshold (40%).
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {similarReports.map((sim) => (
                    <div 
                      key={sim.report_id} 
                      style={{ 
                        border: '1px solid #e2e8f0', 
                        borderRadius: '6px', 
                        padding: '0.75rem',
                        backgroundColor: '#fafbfc' 
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span className="mono-id" style={{ fontSize: '0.8rem' }}>{sim.report_id}</span>
                          <span className={`badge-priority ${sim.priority}`} style={{ fontSize: '0.65rem' }}>
                            {sim.priority}
                          </span>
                        </div>
                        <span 
                          className="badge-neutral" 
                          style={{ 
                            backgroundColor: '#eff6ff', 
                            color: '#1d4ed8', 
                            fontWeight: 700, 
                            fontSize: '0.75rem' 
                          }}
                        >
                          {(sim.similarity_score * 100).toFixed(1)}% Match
                        </span>
                      </div>
                      <p style={{ fontSize: '0.8rem', color: '#334155', lineHeight: 1.4, marginBottom: '0.4rem' }}>
                        "{sim.report_text}"
                      </p>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', color: '#64748b' }}>
                        <span>Hazard: <strong>{sim.hazard || "Unspecified"}</strong></span>
                        {onSelectReport && (
                          <button
                            className="btn btn-outline"
                            style={{ fontSize: '0.7rem', padding: '0.2rem 0.5rem' }}
                            onClick={() => onSelectReport(sim.report_id)}
                          >
                            Inspect Report <ChevronRight size={12} />
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Score, HSE Explanation, Action Buttons */}
        <div>
          {/* Priority & SIF Probability Scorecard */}
          <div className="card-panel">
            <div className="card-panel-header">
              <div className="card-panel-title">
                <ShieldCheck size={16} color="#0f172a" />
                <span>SIF Sentinel Triage Evaluation</span>
              </div>
            </div>
            <div className="card-panel-body" style={{ textAlign: 'center', padding: '1.5rem 1rem' }}>
              <div style={{ marginBottom: '0.75rem' }}>
                <span className="context-label" style={{ display: 'block', marginBottom: '0.25rem' }}>
                  HSE Prioritization Category
                </span>
                <span className={`badge-priority ${report?.priority}`} id="detail-priority" style={{ fontSize: '1.05rem', padding: '0.4rem 1.25rem' }}>
                  {report?.priority} PRIORITY
                </span>
              </div>

              {/* SIF Probability Radial / Meter */}
              <div style={{ margin: '1.5rem 0' }}>
                <div className="context-label" style={{ marginBottom: '0.35rem' }}>
                  SIF Precursor Probability (DistilBERT)
                </div>
                <div id="detail-sif-prob" style={{ fontSize: '2.5rem', fontWeight: 800, color: report?.priority === 'HIGH' ? 'var(--sif-high)' : '#0f172a' }}>
                  {report ? `${(report.sif_probability * 100).toFixed(1)}%` : '0.0%'}
                </div>
                <div className="bar-track" style={{ height: '8px', marginTop: '0.5rem' }}>
                  <div 
                    className={`bar-fill ${report?.priority === 'HIGH' ? 'danger' : report?.priority === 'MEDIUM' ? 'warning' : 'success'}`} 
                    style={{ width: `${Math.min(100, (report?.sif_probability || 0) * 100)}%` }} 
                  />
                </div>
              </div>

              {/* Composite Prioritization Score */}
              <div style={{ 
                backgroundColor: '#f8fafc', 
                border: '1px solid #e2e8f0', 
                borderRadius: '6px', 
                padding: '0.75rem', 
                fontSize: '0.8rem',
                textAlign: 'left'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                  <span style={{ color: '#64748b' }}>Composite Triage Score:</span>
                  <span style={{ fontWeight: 700 }}>{report?.priority_score?.toFixed(3)}</span>
                </div>
                {report?.escalated && (
                  <div style={{ color: '#dc2626', fontWeight: 600, fontSize: '0.75rem', marginTop: '0.35rem' }}>
                    * Priority elevated by safety policy override
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* HSE Explanation Rationale */}
          {/* HSE Explanation Rationale (Phase 14 Structured Breakdown) */}
          <div className="card-panel">
            <div className="card-panel-header">
              <div className="card-panel-title">
                <Info size={16} color="#0f172a" />
                <span>Transparent HSE Explanation</span>
              </div>
              {report?.structured_explanation && (
                <span className="badge-neutral" style={{ fontSize: '0.7rem' }}>
                  Deterministic Synthesis
                </span>
              )}
            </div>
            <div className="card-panel-body">
              {report?.structured_explanation ? (
                <div id="detail-explanation">
                  {/* Template header: Priority & Why */}
                  <div style={{
                    backgroundColor: report.priority === 'HIGH' ? '#fef2f2' : report.priority === 'MEDIUM' ? '#fffbeb' : '#f0fdf4',
                    border: `1px solid ${report.priority === 'HIGH' ? '#fecaca' : report.priority === 'MEDIUM' ? '#fde68a' : '#bbf7d0'}`,
                    borderRadius: '6px',
                    padding: '0.85rem 1rem',
                    marginBottom: '1rem'
                  }}>
                    <div style={{ fontWeight: 800, fontSize: '0.95rem', color: report.priority === 'HIGH' ? '#991b1b' : report.priority === 'MEDIUM' ? '#92400e' : '#166534', marginBottom: '0.5rem' }}>
                      Priority: {report.structured_explanation.priority}
                    </div>
                    <div style={{ fontWeight: 700, fontSize: '0.85rem', color: '#0f172a', marginBottom: '0.35rem' }}>
                      Why:
                    </div>
                    <ul style={{ margin: '0 0 0 1.25rem', padding: 0, display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                      {report.structured_explanation.why?.map((item, idx) => (
                        <li key={idx} style={{ fontSize: '0.85rem', color: '#1e293b', fontWeight: 500 }}>
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Reason for final priority */}
                  <div style={{
                    backgroundColor: '#f8fafc',
                    border: '1px solid #e2e8f0',
                    borderRadius: '6px',
                    padding: '0.75rem',
                    marginBottom: '0.75rem',
                    fontSize: '0.8rem'
                  }}>
                    <div style={{ fontWeight: 600, color: '#475569', marginBottom: '0.2rem' }}>
                      Operational Justification:
                    </div>
                    <div style={{ color: '#0f172a', lineHeight: 1.4 }}>
                      {report.structured_explanation.reason_for_final_priority}
                    </div>
                  </div>

                  {/* Important Detected Signals */}
                  {report.structured_explanation.important_detected_signals?.length > 0 && (
                    <div style={{ marginBottom: '0.75rem' }}>
                      <div className="context-label" style={{ marginBottom: '0.35rem' }}>
                        Important Detected Signals:
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
                        {report.structured_explanation.important_detected_signals.map((sig, i) => (
                          <span key={i} className="evidence-tag" style={{ fontSize: '0.75rem' }}>
                            {sig}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Narrative details */}
                  <div style={{
                    fontSize: '0.78rem',
                    lineHeight: 1.5,
                    color: '#475569',
                    backgroundColor: '#fafbfc',
                    padding: '0.75rem',
                    borderRadius: '6px',
                    border: '1px solid #e2e8f0',
                    whiteSpace: 'pre-line'
                  }}>
                    {report?.explanation}
                  </div>
                </div>
              ) : (
                <div 
                  id="detail-explanation"
                  style={{ 
                    fontSize: '0.85rem', 
                    lineHeight: 1.6, 
                    color: '#334155',
                    backgroundColor: '#fafbfc',
                    padding: '1rem',
                    borderRadius: '6px',
                    border: '1px solid #e2e8f0',
                    whiteSpace: 'pre-line'
                  }}
                >
                  {report?.explanation || "No explanation computed."}
                </div>
              )}

              <div style={{ fontSize: '0.7rem', color: '#94a3b8', marginTop: '0.75rem', fontStyle: 'italic' }}>
                Governance: SIF Sentinel prioritizes reports for HSE verification and does not predict future accidents.
              </div>
            </div>
          </div>

          {/* Human-in-the-Loop Review Controls: CONFIRM, REJECT, CORRECT */}
          <div className="card-panel" style={{ border: '2px solid #cbd5e1' }}>
            <div className="card-panel-header" style={{ backgroundColor: '#f1f5f9' }}>
              <div className="card-panel-title">
                <CheckCircle2 size={16} color="#0f172a" />
                <span>HSE Officer Verification</span>
              </div>
            </div>
            <div className="card-panel-body">
              <p style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '1rem' }}>
                Record your determination to validate the AI triage or apply an officer correction across priority, activity, hazard, and barrier:
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                {/* CONFIRM BUTTON */}
                <button
                  id="btn-confirm"
                  className="btn btn-confirm"
                  style={{ width: '100%', padding: '0.65rem', fontWeight: 700 }}
                  disabled={actionInProgress}
                  onClick={() => handleAction('confirmed')}
                >
                  <CheckCircle size={16} />
                  CONFIRM AI CLASSIFICATION (Step 11)
                </button>

                {/* REJECT BUTTON */}
                <button
                  id="btn-reject"
                  className="btn btn-reject"
                  style={{ width: '100%', padding: '0.65rem' }}
                  disabled={actionInProgress}
                  onClick={() => handleAction('rejected')}
                >
                  <XCircle size={16} />
                  REJECT PRECURSOR (DE-ESCALATE)
                </button>

                {/* CORRECT BUTTON */}
                <button
                  id="btn-correct"
                  className="btn btn-correct"
                  style={{ width: '100%', padding: '0.65rem' }}
                  disabled={actionInProgress}
                  onClick={() => setShowCorrectModal(!showCorrectModal)}
                >
                  <Edit3 size={16} />
                  {showCorrectModal ? 'HIDE CORRECTION FORM' : 'CORRECT CLASSIFICATION'}
                </button>

                {/* Direct shortcut to Step 13 when verified */}
                {report?.hse_reviewed && onNavigateTab && (
                  <button
                    id="btn-goto-step-13"
                    type="button"
                    className="btn btn-accent"
                    style={{ 
                      width: '100%', 
                      padding: '0.65rem',
                      fontWeight: 700,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '0.4rem',
                      backgroundColor: '#2563eb',
                      color: '#ffffff'
                    }}
                    onClick={() => onNavigateTab('patterns')}
                  >
                    <span>View Recurring Risk Patterns (Step 13)</span>
                    <ChevronRight size={15} />
                  </button>
                )}
              </div>

              {/* Inline Multi-Dimensional Correction Form */}
              {showCorrectModal && (
                <div style={{ 
                  marginTop: '1.25rem', 
                  padding: '1rem', 
                  backgroundColor: '#fffbeb', 
                  border: '1px solid #fde68a', 
                  borderRadius: '6px' 
                }}>
                  <div style={{ fontSize: '0.825rem', fontWeight: 700, color: '#92400e', marginBottom: '0.75rem' }}>
                    Adjust Safety Parameters (Non-Destructive):
                  </div>

                  {/* 1. Priority */}
                  <div className="form-group" style={{ marginBottom: '0.6rem' }}>
                    <label className="form-label" style={{ fontSize: '0.75rem' }}>1. Corrected Priority</label>
                    <select
                      id="correct-priority-select"
                      className="filter-select"
                      style={{ width: '100%' }}
                      value={correctedPriority}
                      onChange={(e) => setCorrectedPriority(e.target.value)}
                    >
                      <option value="HIGH">HIGH (SIF Precursor)</option>
                      <option value="MEDIUM">MEDIUM (Potential Precursor)</option>
                      <option value="LOW">LOW (Controlled Condition)</option>
                    </select>
                  </div>

                  {/* 2. Activity */}
                  <div className="form-group" style={{ marginBottom: '0.6rem' }}>
                    <label className="form-label" style={{ fontSize: '0.75rem' }}>2. Corrected Activity</label>
                    <input
                      id="correct-activity-input"
                      type="text"
                      className="form-input"
                      style={{ width: '100%', fontSize: '0.8rem' }}
                      placeholder="e.g. Maintenance, Hot Work, Lifting Operations"
                      value={correctedActivity}
                      onChange={(e) => setCorrectedActivity(e.target.value)}
                    />
                  </div>

                  {/* 3. Hazard */}
                  <div className="form-group" style={{ marginBottom: '0.6rem' }}>
                    <label className="form-label" style={{ fontSize: '0.75rem' }}>3. Corrected Hazard</label>
                    <input
                      id="correct-hazard-input"
                      type="text"
                      className="form-input"
                      style={{ width: '100%', fontSize: '0.8rem' }}
                      placeholder="e.g. Electrical Energy, Struck-By, Toxic Gas"
                      value={correctedHazard}
                      onChange={(e) => setCorrectedHazard(e.target.value)}
                    />
                  </div>

                  {/* 4. Barrier */}
                  <div className="form-group" style={{ marginBottom: '0.6rem' }}>
                    <label className="form-label" style={{ fontSize: '0.75rem' }}>4. Corrected Barrier</label>
                    <input
                      id="correct-barrier-input"
                      type="text"
                      className="form-input"
                      style={{ width: '100%', fontSize: '0.8rem' }}
                      placeholder="e.g. Isolation, Gas Testing, Permit to Work"
                      value={correctedBarrier}
                      onChange={(e) => setCorrectedBarrier(e.target.value)}
                    />
                  </div>

                  {/* Reviewer ID */}
                  <div className="form-group" style={{ marginBottom: '0.6rem' }}>
                    <label className="form-label" style={{ fontSize: '0.75rem' }}>Officer ID</label>
                    <input
                      type="text"
                      className="form-input"
                      style={{ width: '100%', fontSize: '0.8rem' }}
                      value={reviewerId}
                      onChange={(e) => setReviewerId(e.target.value)}
                    />
                  </div>

                  {/* Reason / Comments */}
                  <div className="form-group" style={{ marginBottom: '0.75rem' }}>
                    <label className="form-label" style={{ fontSize: '0.75rem' }}>Reason / Correction Rationale</label>
                    <textarea
                      id="officer-notes-input"
                      className="form-textarea"
                      style={{ minHeight: '60px', fontSize: '0.8rem' }}
                      placeholder="Mandatory rationale for changing classification..."
                      value={officerComments}
                      onChange={(e) => setOfficerComments(e.target.value)}
                    />
                  </div>

                  <button
                    id="btn-submit-correction"
                    className="btn btn-primary"
                    style={{ width: '100%', fontSize: '0.8rem', padding: '0.5rem' }}
                    disabled={actionInProgress}
                    onClick={() => handleAction('corrected')}
                  >
                    <Send size={13} /> Submit Officer Correction
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Quick Feedback Form */}
          <div className="card-panel">
            <div className="card-panel-header">
              <div className="card-panel-title">
                <MessageSquare size={16} color="#6366f1" />
                <span>Submit Model Feedback</span>
              </div>
            </div>
            <div className="card-panel-body">
              <p style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '0.75rem' }}>
                Annotate this report for model retraining or flag false positives:
              </p>
              <form onSubmit={handleFeedbackSubmit}>
                <div className="form-group" style={{ marginBottom: '0.5rem' }}>
                  <label className="form-label" style={{ fontSize: '0.75rem' }}>Feedback Category</label>
                  <select
                    className="filter-select"
                    style={{ width: '100%', fontSize: '0.8rem' }}
                    value={feedbackType}
                    onChange={(e) => setFeedbackType(e.target.value)}
                  >
                    <option value="label_correction">Label / Entity Correction</option>
                    <option value="false_positive">False Positive (Not a Precursor)</option>
                    <option value="false_negative">False Negative (Missed Precursor)</option>
                    <option value="general_feedback">General HSE Comment</option>
                  </select>
                </div>
                <div className="form-group" style={{ marginBottom: '0.75rem' }}>
                  <textarea
                    className="form-textarea"
                    style={{ minHeight: '50px', fontSize: '0.8rem' }}
                    placeholder="Provide critique or annotation notes..."
                    value={feedbackNotes}
                    onChange={(e) => setFeedbackNotes(e.target.value)}
                  />
                </div>
                <button
                  type="submit"
                  className="btn btn-outline"
                  style={{ width: '100%', fontSize: '0.8rem' }}
                  disabled={!feedbackNotes.trim()}
                >
                  <Send size={12} /> Log Model Feedback
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>

      {/* Audit Trail Timeline (Step 12) */}
      <div className="card-panel" id="audit-trail-section" style={{ marginTop: '1.25rem' }}>
        <div className="card-panel-header" style={{ background: '#f8fafc', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div className="card-panel-title">
            <History size={16} color="#475569" />
            <span>Immutable Report Audit Trail ({auditLogs.length} Records)</span>
          </div>
          <span className="badge-neutral" style={{ fontSize: '0.65rem', fontWeight: 700, backgroundColor: '#eff6ff', color: '#1d4ed8' }}>
            Step 12: Audit Trail
          </span>
        </div>
        <div className="card-panel-body">
          {auditLogs.length === 0 ? (
            <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>No audit history recorded yet.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {auditLogs.map((log, idx) => (
                <div 
                  key={idx} 
                  style={{ 
                    borderLeft: `4px solid ${log.action === 'HSE_REVIEW' ? '#16a34a' : log.action === 'FEEDBACK_SUBMITTED' ? '#6366f1' : '#2563eb'}`,
                    paddingLeft: '0.75rem',
                    paddingTop: '0.4rem',
                    paddingBottom: '0.4rem',
                    fontSize: '0.8rem',
                    backgroundColor: log.action === 'HSE_REVIEW' ? '#f0fdf4' : 'transparent',
                    borderRadius: '0 4px 4px 0'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      <span style={{ fontWeight: 700, color: '#0f172a' }}>
                        {log.action}
                      </span>
                      {log.action === 'HSE_REVIEW' && (
                        <span style={{ fontSize: '0.65rem', fontWeight: 700, padding: '0.1rem 0.4rem', borderRadius: '3px', backgroundColor: '#bbf7d0', color: '#166534' }}>
                          OFFICER DETERMINATION CONFIRMED
                        </span>
                      )}
                    </div>
                    <span style={{ color: '#94a3b8', fontSize: '0.75rem' }}>
                      {log.created_at ? new Date(log.created_at).toLocaleString() : 'N/A'}
                    </span>
                  </div>
                  <div style={{ color: '#64748b', fontSize: '0.75rem', marginTop: '0.15rem' }}>
                    Actor: <strong>{log.actor_id}</strong>
                  </div>
                  {log.details && (
                    <div style={{ marginTop: '0.25rem', background: '#f8fafc', padding: '0.35rem 0.5rem', borderRadius: '4px', border: '1px solid #e2e8f0', fontSize: '0.75rem', fontFamily: 'monospace' }}>
                      {typeof log.details === 'string' ? log.details : JSON.stringify(log.details)}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {onNavigateTab && (
            <div style={{ marginTop: '1.25rem', display: 'flex', justifyContent: 'flex-end' }}>
              <button
                id="btn-audit-goto-patterns"
                type="button"
                className="btn btn-accent"
                style={{ 
                  fontSize: '0.8rem', 
                  padding: '0.45rem 1rem', 
                  fontWeight: 700, 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '0.4rem',
                  backgroundColor: '#2563eb',
                  color: '#ffffff'
                }}
                onClick={() => onNavigateTab('patterns')}
              >
                <span>Proceed to Step 13: View Recurring Risk Patterns</span>
                <ChevronRight size={15} />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
