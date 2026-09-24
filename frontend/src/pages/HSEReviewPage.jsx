import React, { useState, useEffect } from 'react';
import { 
  CheckSquare, 
  AlertTriangle, 
  CheckCircle, 
  XCircle, 
  Edit3, 
  RefreshCw, 
  Clock, 
  MapPin,
  Calendar,
  FileText,
  ShieldCheck,
  Send,
  Sliders,
  Check
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { fetchReports, submitHSEReview } from '../services/api';
import { PriorityBadge, ExportDropdown } from '../components/ui';
import TechnicalAssessmentDrawer from '../components/TechnicalAssessmentDrawer';

export default function HSEReviewPage({ onSelectReport }) {
  const [reports, setReports] = useState([]);
  const [filterMode, setFilterMode] = useState('pending'); // 'all', 'critical', 'high', 'medium', 'pending', 'confirmed', 'corrected', 'rejected'
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Active quick review state
  const [expandedReportId, setExpandedReportId] = useState(null);
  const [correctionMode, setCorrectionMode] = useState(false);
  const [correctedPriority, setCorrectedPriority] = useState('MEDIUM');
  const [correctedActivity, setCorrectedActivity] = useState('');
  const [correctedHazard, setCorrectedHazard] = useState('');
  const [correctedBarrier, setCorrectedBarrier] = useState('');
  const [reviewerId, setReviewerId] = useState('HSE-OFFICER-01');
  const [comments, setComments] = useState('');
  const [drawerAssessment, setDrawerAssessment] = useState(null);
  
  // Animation states
  const [actionLoading, setActionLoading] = useState(false);
  const [successState, setSuccessState] = useState(null); // { reportId: string, decision: string }

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

  const handleOpenReview = (report) => {
    if (expandedReportId === report.report_id) {
      setExpandedReportId(null);
      setCorrectionMode(false);
    } else {
      setExpandedReportId(report.report_id);
      setCorrectionMode(false);
      setCorrectedPriority(report.final_priority || report.priority || 'MEDIUM');
      setCorrectedActivity(report.final_activity || report.activity || '');
      setCorrectedHazard(report.final_hazard || report.hazard || '');
      setCorrectedBarrier(report.final_barrier || report.barrier || '');
      setComments('');
    }
  };

  const handleReviewAction = async (reportId, decision, customData = {}) => {
    setActionLoading(true);
    setError(null);
    try {
      await submitHSEReview({
        reportId: reportId,
        reviewerId: reviewerId,
        decision: decision,
        correctedPriority: decision === 'corrected' ? (customData.priority || correctedPriority) : null,
        correctedActivity: decision === 'corrected' ? (customData.activity || correctedActivity || null) : null,
        correctedHazard: decision === 'corrected' ? (customData.hazard || correctedHazard || null) : null,
        correctedBarrier: decision === 'corrected' ? (customData.barrier || correctedBarrier || null) : null,
        comments: customData.comments || comments.trim() || undefined,
      });

      // Trigger success animation sequence
      setSuccessState({ reportId, decision });
      
      // Instantly notify Navbar to decrement the unread alert count
      window.dispatchEvent(new Event('refresh-alerts'));
      
      // After animation, close and reload
      setTimeout(() => {
        setSuccessState(null);
        setExpandedReportId(null);
        loadQueue();
      }, 3500);

    } catch (err) {
      setError(err.message || "Failed to submit review");
    } finally {
      setActionLoading(false);
    }
  };

  // Filter logic
  const displayReports = reports.filter(r => {
    if (filterMode === 'pending') return !r.hse_reviewed;
    if (filterMode === 'confirmed') return r.hse_reviewed && r.review_decision === 'confirmed';
    if (filterMode === 'corrected') return r.hse_reviewed && r.review_decision === 'corrected';
    if (filterMode === 'rejected') return r.hse_reviewed && r.review_decision === 'rejected';
    if (filterMode === 'critical') return (r.final_priority || r.priority) === 'CRITICAL';
    if (filterMode === 'high') return (r.final_priority || r.priority) === 'HIGH';
    if (filterMode === 'medium') return (r.final_priority || r.priority) === 'MEDIUM';
    return true; // all
  });

  const getCounts = (mode) => {
    switch (mode) {
      case 'pending': return reports.filter(r => !r.hse_reviewed).length;
      case 'confirmed': return reports.filter(r => r.hse_reviewed && r.review_decision === 'confirmed').length;
      case 'corrected': return reports.filter(r => r.hse_reviewed && r.review_decision === 'corrected').length;
      case 'rejected': return reports.filter(r => r.hse_reviewed && r.review_decision === 'rejected').length;
      case 'critical': return reports.filter(r => (r.final_priority || r.priority) === 'CRITICAL').length;
      case 'high': return reports.filter(r => (r.final_priority || r.priority) === 'HIGH').length;
      case 'medium': return reports.filter(r => (r.final_priority || r.priority) === 'MEDIUM').length;
      case 'all': return reports.length;
      default: return 0;
    }
  };

  const truncate = (text, length = 120) => {
    if (!text) return '';
    return text.length > length ? text.substring(0, length) + '...' : text;
  };

  return (
    <div className="page-container">
      {/* Page Header */}
      <div className="page-header">
        <div className="page-title">
          <h1>HSE Review</h1>
          <p>Review safety observations requiring human verification.</p>
        </div>
        <div className="page-actions">
          <ExportDropdown />
          <button className="btn btn-outline" onClick={loadQueue}>
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

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

      {/* Filter Chips */}
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1.5rem' }}>
        {['All', 'Critical', 'High', 'Medium', 'Pending', 'Confirmed', 'Corrected', 'Rejected'].map(mode => {
          const m = mode.toLowerCase();
          const isActive = filterMode === m;
          return (
            <motion.button
              key={m}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className={`btn ${isActive ? 'btn-primary' : 'btn-outline'}`}
              onClick={() => setFilterMode(m)}
              style={{ padding: '0.4rem 0.8rem', fontSize: '0.85rem' }}
            >
              {mode} ({getCounts(m)})
            </motion.button>
          )
        })}
      </div>

      {/* Review Queue Cards */}
      {loading ? (
        <div className="loading-state">
          <RefreshCw size={28} className="spin" />
          <p>Loading review queue...</p>
        </div>
      ) : displayReports.length === 0 ? (
        <div className="empty-state">
          <CheckCircle size={36} color="#16a34a" style={{ marginBottom: '0.75rem' }} />
          <h3>Queue is Clear!</h3>
          <p style={{ marginTop: '0.25rem', color: '#64748b' }}>No reports currently in the {filterMode} view.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <AnimatePresence>
            {displayReports.map((report) => {
              const isExpanded = expandedReportId === report.report_id;
              const isSuccess = successState?.reportId === report.report_id;

              return (
                <motion.div 
                  key={report.report_id} 
                  layout
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="panel"
                  style={{ 
                    overflow: 'hidden',
                    borderLeft: `4px solid ${
                      (report.final_priority || report.priority) === 'CRITICAL' ? 'var(--sif-high)' :
                      (report.final_priority || report.priority) === 'HIGH' ? 'var(--sif-high)' : 
                      (report.final_priority || report.priority) === 'MEDIUM' ? 'var(--sif-medium)' : 'var(--sif-low)'
                    }`
                  }}
                >
                  <div style={{ padding: '1.25rem' }}>
                    {/* Compact Card Header */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
                      
                      <div style={{ flex: 1, minWidth: '300px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
                          <span className="mono-id">{report.report_id}</span>
                          <PriorityBadge priority={report.final_priority || report.priority} />
                          
                          {/* Review Status */}
                          {report.hse_reviewed ? (
                            <span style={{ fontSize: '0.75rem', color: 'var(--sif-low)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
                              <CheckCircle size={12} /> {report.review_decision}
                            </span>
                          ) : (
                            <span style={{ fontSize: '0.75rem', color: 'var(--slate-500)', display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
                              <Clock size={12} /> Pending Review
                            </span>
                          )}
                        </div>

                        {!isExpanded && (
                          <div style={{ fontSize: '0.9rem', color: 'var(--slate-700)', lineHeight: 1.5 }}>
                            {truncate(report.report_text)}
                          </div>
                        )}
                        
                        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginTop: '0.5rem', fontSize: '0.75rem', color: 'var(--slate-500)' }}>
                          {report.location && (
                            <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                              <MapPin size={12} /> {report.location}
                            </span>
                          )}
                          <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                            <Calendar size={12} /> {new Date(report.created_at || Date.now()).toLocaleString()}
                          </span>
                        </div>
                      </div>

                      <div style={{ display: 'flex', gap: '0.5rem', flexShrink: 0 }}>
                        <motion.button 
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                          className="btn btn-outline" 
                          onClick={() => onSelectReport(report.report_id)}
                        >
                          Details
                        </motion.button>
                        {!report.hse_reviewed && (
                          <motion.button 
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            className="btn btn-primary" 
                            onClick={() => handleOpenReview(report)}
                          >
                            {isExpanded ? 'Close Review' : 'Review'}
                          </motion.button>
                        )}
                      </div>
                    </div>

                    {/* Split Pane Review Area */}
                    <AnimatePresence>
                      {isExpanded && !isSuccess && (
                        <motion.div
                          layout
                          initial={{ opacity: 0, height: 0, marginTop: 0 }}
                          animate={{ opacity: 1, height: 'auto', marginTop: '1.5rem' }}
                          exit={{ opacity: 0, height: 0, marginTop: 0 }}
                          style={{ overflow: 'hidden' }}
                        >
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', borderTop: '1px solid var(--border-subtle)', paddingTop: '1.5rem' }}>
                            
                            {/* LEFT: Observation Context */}
                            <div>
                              <h4 style={{ fontSize: '0.85rem', color: 'var(--slate-500)', textTransform: 'uppercase', marginBottom: '0.75rem' }}>Observation Details</h4>
                              <div style={{ 
                                backgroundColor: 'var(--slate-50)', 
                                padding: '1rem', 
                                borderRadius: '6px',
                                fontSize: '0.9rem',
                                color: 'var(--slate-800)',
                                lineHeight: 1.6,
                                marginBottom: '1rem'
                              }}>
                                {report.report_text}
                              </div>
                            </div>

                            {/* RIGHT: Assessment & Human Determination */}
                            <div>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                                <h4 style={{ fontSize: '0.85rem', color: 'var(--slate-500)', textTransform: 'uppercase' }}>Original AI Assessment</h4>
                                <button 
                                  className="btn btn-ghost btn-sm"
                                  onClick={() => setDrawerAssessment(report)}
                                  style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem', gap: '0.25rem' }}
                                >
                                  <Sliders size={12} /> Assessment details
                                </button>
                              </div>
                              
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '1.5rem' }}>
                                <div style={{ display: 'grid', gridTemplateColumns: '100px 1fr', fontSize: '0.85rem' }}>
                                  <span style={{ color: 'var(--slate-500)' }}>Activity</span>
                                  <strong style={{ color: 'var(--slate-800)' }}>{report.activity || 'None'}</strong>
                                </div>
                                <div style={{ display: 'grid', gridTemplateColumns: '100px 1fr', fontSize: '0.85rem' }}>
                                  <span style={{ color: 'var(--slate-500)' }}>Hazard</span>
                                  <strong style={{ color: 'var(--slate-800)' }}>{report.hazard || 'None'}</strong>
                                </div>
                                <div style={{ display: 'grid', gridTemplateColumns: '100px 1fr', fontSize: '0.85rem' }}>
                                  <span style={{ color: 'var(--slate-500)' }}>Barrier</span>
                                  <strong style={{ color: 'var(--slate-800)' }}>{report.barrier || 'None'}</strong>
                                </div>
                              </div>

                              <h4 style={{ fontSize: '0.85rem', color: 'var(--slate-500)', textTransform: 'uppercase', marginBottom: '0.75rem' }}>Human Determination</h4>
                              
                              {!correctionMode ? (
                                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                                  <motion.button 
                                    whileHover={{ scale: 1.02 }}
                                    whileTap={{ scale: 0.98 }}
                                    className="btn btn-confirm" 
                                    onClick={() => handleReviewAction(report.report_id, 'confirmed')}
                                    disabled={actionLoading}
                                  >
                                    Confirm Assessment
                                  </motion.button>
                                  <motion.button 
                                    whileHover={{ scale: 1.02 }}
                                    whileTap={{ scale: 0.98 }}
                                    className="btn btn-correct" 
                                    onClick={() => setCorrectionMode(true)}
                                    disabled={actionLoading}
                                  >
                                    Correct Assessment
                                  </motion.button>
                                  <motion.button 
                                    whileHover={{ scale: 1.02 }}
                                    whileTap={{ scale: 0.98 }}
                                    className="btn btn-reject" 
                                    onClick={() => handleReviewAction(report.report_id, 'rejected')}
                                    disabled={actionLoading}
                                  >
                                    Reject Assessment
                                  </motion.button>
                                </div>
                              ) : (
                                <motion.div 
                                  initial={{ opacity: 0 }} 
                                  animate={{ opacity: 1 }}
                                  style={{ backgroundColor: 'var(--slate-50)', padding: '1rem', borderRadius: '6px' }}
                                >
                                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1rem' }}>
                                    <div>
                                      <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--slate-600)', display: 'block', marginBottom: '0.25rem' }}>Priority</label>
                                      <select className="filter-select" style={{ width: '100%' }} value={correctedPriority} onChange={e => setCorrectedPriority(e.target.value)}>
                                        <option value="CRITICAL">Critical</option>
                                        <option value="HIGH">High</option>
                                        <option value="MEDIUM">Medium</option>
                                        <option value="LOW">Low</option>
                                      </select>
                                    </div>
                                    <div>
                                      <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--slate-600)', display: 'block', marginBottom: '0.25rem' }}>Activity</label>
                                      <input type="text" className="search-input" style={{ width: '100%', fontSize: '0.8rem' }} value={correctedActivity} onChange={e => setCorrectedActivity(e.target.value)} />
                                    </div>
                                    <div>
                                      <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--slate-600)', display: 'block', marginBottom: '0.25rem' }}>Hazard</label>
                                      <input type="text" className="search-input" style={{ width: '100%', fontSize: '0.8rem' }} value={correctedHazard} onChange={e => setCorrectedHazard(e.target.value)} />
                                    </div>
                                    <div>
                                      <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--slate-600)', display: 'block', marginBottom: '0.25rem' }}>Barrier</label>
                                      <input type="text" className="search-input" style={{ width: '100%', fontSize: '0.8rem' }} value={correctedBarrier} onChange={e => setCorrectedBarrier(e.target.value)} />
                                    </div>
                                  </div>
                                  
                                  <div style={{ marginBottom: '1rem' }}>
                                    <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--slate-600)', display: 'block', marginBottom: '0.25rem' }}>Reason for Correction</label>
                                    <input type="text" className="search-input" style={{ width: '100%', fontSize: '0.8rem' }} placeholder="Mandatory for audit trail..." value={comments} onChange={e => setComments(e.target.value)} />
                                  </div>

                                  <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                                    <button className="btn btn-ghost btn-sm" onClick={() => setCorrectionMode(false)} disabled={actionLoading}>Cancel</button>
                                    <button className="btn btn-primary btn-sm" onClick={() => handleReviewAction(report.report_id, 'corrected')} disabled={actionLoading}>
                                      Save Determination
                                    </button>
                                  </div>
                                </motion.div>
                              )}
                            </div>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>

                    {/* Animated Success State */}
                    <AnimatePresence>
                      {isSuccess && (
                        <motion.div
                          layout
                          initial={{ opacity: 0, height: 0, marginTop: 0 }}
                          animate={{ opacity: 1, height: 'auto', marginTop: '1.5rem' }}
                          exit={{ opacity: 0, height: 0, marginTop: 0 }}
                          style={{ overflow: 'hidden' }}
                        >
                          <div style={{ 
                            backgroundColor: '#f0fdf4', 
                            padding: '1.5rem', 
                            borderRadius: '8px', 
                            display: 'flex', 
                            flexDirection: 'column', 
                            gap: '0.75rem',
                            color: '#166534'
                          }}>
                            <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600 }}>
                              <Check size={18} /> Assessment {successState.decision}
                            </motion.div>
                            <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.3 }} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.9rem' }}>
                              <Check size={14} /> Review recorded
                            </motion.div>
                            <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.6 }} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.9rem' }}>
                              <Check size={14} /> Workflow updated
                            </motion.div>
                            <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.9 }} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.9rem' }}>
                              <Check size={14} /> Audit trail updated
                            </motion.div>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>

                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      )}
      
      {/* Technical Drawer */}
      <TechnicalAssessmentDrawer 
        isOpen={!!drawerAssessment} 
        onClose={() => setDrawerAssessment(null)} 
        assessment={drawerAssessment} 
      />
    </div>
  );
}
