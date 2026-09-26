import React, { useState } from 'react';
import { 
  X, 
  Play, 
  Sparkles, 
  CheckCircle, 
  AlertTriangle, 
  ShieldCheck, 
  ArrowRight,
  Clock,
  Layers,
  FileText
} from 'lucide-react';
import { analyzeReport } from '../services/api';

export const PRESET_EXAMPLES = [
  {
    title: "⚡ SIH Demo: 4160V Energy Isolation Precursor",
    text: "Contractor electrician accessed energized equipment without isolation during 4160V motor control center cubicle MCC-04 maintenance. LOTO not applied and isolation not verified prior to opening switchgear cabinet.",
    location: "MCC Building 4 - Unit 12",
    customId: "SIH-DEMO-LIVE-01",
  },
  {
    title: "Confined Space Entry",
    text: "Contractor entered separator vessel without continuous atmospheric gas monitoring or standby observer.",
    location: "Vessel V-102 Separator",
    customId: "DEMO-CONF-01",
  },
  {
    title: "Work at Height",
    text: "Scaffolding dismantled without personal fall arrest system 8 meters above ground level.",
    location: "Crude Distillation Column",
    customId: "DEMO-HGHT-01",
  },
  {
    title: "Routine Housekeeping (Low Risk)",
    text: "Minor water spill in administrative corridor wiped and clean sign placed immediately.",
    location: "Admin Building Corridor B",
    customId: "DEMO-ROUT-01",
  },
];

export default function AnalyzeModal({ 
  isOpen, 
  onClose, 
  onAnalysisComplete,
  onProceedToReview 
}) {
  const [reportText, setReportText] = useState(PRESET_EXAMPLES[0].text);
  const [location, setLocation] = useState(PRESET_EXAMPLES[0].location);
  const [customId, setCustomId] = useState(PRESET_EXAMPLES[0].customId);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!reportText.trim() || reportText.length < 10) {
      setError("Report narrative must be at least 10 characters.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const res = await analyzeReport({
        reportText: reportText.trim(),
        location: location.trim() || null,
        reportId: customId.trim() || null,
      });
      setResult(res);
      if (onAnalysisComplete) {
        onAnalysisComplete(res);
      }
    } catch (err) {
      setError(err.message || "Failed to analyze report");
    } finally {
      setLoading(false);
    }
  };

  const handleApplyPreset = (preset) => {
    setReportText(preset.text);
    setLocation(preset.location);
    setCustomId(preset.customId || '');
    setError(null);
    setResult(null);
  };

  const handleReset = () => {
    setResult(null);
    setError(null);
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div 
        className="modal-content" 
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: '720px' }}
      >
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Sparkles size={18} color="#2563eb" />
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>
              Live SIF Sentinel Precursor Analysis (Step 3 & 4)
            </h3>
          </div>
          <button 
            onClick={onClose}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b' }}
          >
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          {error && (
            <div style={{ 
              backgroundColor: '#fef2f2', 
              color: '#991b1b', 
              border: '1px solid #fecaca', 
              padding: '0.75rem', 
              borderRadius: '6px', 
              marginBottom: '1rem',
              fontSize: '0.85rem' 
            }}>
              <strong>Error:</strong> {error}
            </div>
          )}

          {/* Loading State Animation */}
          {loading && (
            <div style={{
              backgroundColor: '#eff6ff',
              border: '1px solid #bfdbfe',
              borderRadius: '8px',
              padding: '1.5rem',
              textAlign: 'center',
              marginBottom: '1rem',
            }}>
              <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.65rem', marginBottom: '0.5rem' }}>
                <Clock size={24} className="spin" color="#2563eb" />
                <span style={{ fontWeight: 700, color: '#1e40af', fontSize: '0.95rem' }}>
                  Executing Real-Time Pipeline...
                </span>
              </div>
              <p style={{ fontSize: '0.825rem', color: '#1e3a8a', lineHeight: 1.5 }}>
                Evaluating narrative through DistilBERT neural classification, domain NLP entity extraction, and deterministic OSHA/IOGP Life Saving Rules.
              </p>
            </div>
          )}

          {!result ? (
            <form id="analyze-form" onSubmit={handleSubmit}>
              {/* Presets */}
              <div style={{ marginBottom: '1rem' }}>
                <span className="context-label" style={{ display: 'block', marginBottom: '0.4rem' }}>
                  Quick Demonstration Presets:
                </span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                  {PRESET_EXAMPLES.map((ex, i) => (
                    <button
                      key={i}
                      type="button"
                      className="btn btn-outline"
                      style={{ 
                        fontSize: '0.75rem', 
                        padding: '0.3rem 0.65rem',
                        borderColor: i === 0 ? '#3b82f6' : '#cbd5e1',
                        backgroundColor: i === 0 ? '#eff6ff' : '#ffffff',
                        color: i === 0 ? '#1d4ed8' : '#334155',
                        fontWeight: i === 0 ? 700 : 500,
                      }}
                      onClick={() => handleApplyPreset(ex)}
                    >
                      {ex.title}
                    </button>
                  ))}
                </div>
              </div>

              {/* Narrative Text */}
              <div className="form-group">
                <label className="form-label" htmlFor="narrative-input">
                  Safety Observation / Incident Narrative *
                </label>
                <textarea
                  id="narrative-input"
                  className="form-textarea"
                  rows={4}
                  value={reportText}
                  onChange={(e) => setReportText(e.target.value)}
                  placeholder="Describe the safety observation, hazard, equipment, and barrier status..."
                  required
                  disabled={loading}
                />
              </div>

              {/* Location & Custom ID row */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.85rem' }}>
                <div className="form-group">
                  <label className="form-label" htmlFor="location-input">Facility Location / Zone</label>
                  <input
                    id="location-input"
                    type="text"
                    className="search-input"
                    style={{ paddingLeft: '0.85rem' }}
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    placeholder="e.g. Unit 3 Hydrocracker"
                    disabled={loading}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor="custom-id-input">Report ID (Optional)</label>
                  <input
                    id="custom-id-input"
                    type="text"
                    className="search-input"
                    style={{ paddingLeft: '0.85rem' }}
                    value={customId}
                    onChange={(e) => setCustomId(e.target.value)}
                    placeholder="Auto-generated if empty"
                    disabled={loading}
                  />
                </div>
              </div>
            </form>
          ) : (
            /* Analysis Result Preview — Showing Steps 5 to 9 */
            <div>
              {/* Step 5 & Step 9: AI Result + High Priority Banner */}
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'space-between', 
                padding: '0.85rem 1rem',
                backgroundColor: result.priority === 'HIGH' ? '#fef2f2' : result.priority === 'MEDIUM' ? '#fffbeb' : '#f0fdf4',
                border: `1px solid ${result.priority === 'HIGH' ? '#fecaca' : result.priority === 'MEDIUM' ? '#fde68a' : '#bbf7d0'}`,
                borderRadius: '8px',
                marginBottom: '1rem'
              }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.35rem' }}>
                    <span className="badge-neutral" style={{ fontSize: '0.65rem', fontWeight: 700 }}>
                      Step 9: Priority
                    </span>
                    <span className={`badge-priority ${result.priority}`}>
                      {result.priority} PRIORITY
                    </span>
                  </div>
                  <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>
                    Report ID: <span className="mono-id">{result.report_id}</span>
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', justifyContent: 'flex-end', marginBottom: '0.2rem' }}>
                    <span className="badge-neutral" style={{ fontSize: '0.65rem', fontWeight: 700 }}>
                      Step 5: AI Result
                    </span>
                    <span style={{ fontSize: '0.75rem', color: '#64748b' }}>SIF Precursor Prob</span>
                  </div>
                  <div style={{ fontSize: '1.6rem', fontWeight: 800, color: result.priority === 'HIGH' ? '#dc2626' : '#0f172a' }}>
                    {(result.sif_probability * 100).toFixed(1)}%
                  </div>
                </div>
              </div>

              {/* Step 6: Extracted Context (Activity / Hazard / Barrier) */}
              <div style={{ marginBottom: '1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.4rem' }}>
                  <span className="badge-neutral" style={{ fontSize: '0.65rem', fontWeight: 700 }}>
                    Step 6: Extracted Context
                  </span>
                  <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#334155' }}>
                    NLP Domain Extraction & Barrier Status
                  </span>
                </div>
                <div className="context-key-value-grid">
                  <div className="context-card">
                    <div className="context-label">Activity</div>
                    <div className="context-value">{result.activity || "None specified"}</div>
                  </div>
                  <div className="context-card">
                    <div className="context-label">Hazard</div>
                    <div className="context-value" style={{ color: result.priority === 'HIGH' ? '#dc2626' : '#0f172a' }}>
                      {result.hazard || "None specified"}
                    </div>
                  </div>
                  <div className="context-card">
                    <div className="context-label">Barrier & Status</div>
                    <div className="context-value">
                      {result.barrier ? `${result.barrier} (${result.barrier_status || 'Unknown'})` : "None"}
                    </div>
                  </div>
                </div>
              </div>

              {/* Step 7: Triggered Safety Rules */}
              {result.triggered_rules && result.triggered_rules.length > 0 && (
                <div style={{ marginBottom: '1rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.4rem' }}>
                    <span className="badge-neutral" style={{ fontSize: '0.65rem', fontWeight: 700 }}>
                      Step 7: Safety Rules
                    </span>
                    <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#334155' }}>
                      Triggered Deterministic Safety Rules ({result.triggered_rules.length})
                    </span>
                  </div>
                  {result.triggered_rules.map((rule, idx) => (
                    <div key={idx} className="rule-card" style={{ padding: '0.65rem 0.85rem' }}>
                      <div className="rule-header">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                          <span className="mono-id" style={{ fontSize: '0.75rem' }}>{rule.rule_id}</span>
                          <span className="rule-name">{rule.rule_name}</span>
                        </div>
                        <span className="badge-priority HIGH" style={{ fontSize: '0.65rem' }}>
                          {rule.severity_label || `Severity ${rule.severity}`}
                        </span>
                      </div>
                      <div className="rule-explanation">{rule.explanation}</div>
                    </div>
                  ))}
                </div>
              )}

              {/* Step 8: Transparent Explanation */}
              <div style={{ 
                backgroundColor: '#f8fafc', 
                border: '1px solid #e2e8f0', 
                borderRadius: '6px', 
                padding: '0.85rem 1rem',
                fontSize: '0.85rem',
                marginBottom: '1rem'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.4rem' }}>
                  <span className="badge-neutral" style={{ fontSize: '0.65rem', fontWeight: 700 }}>
                    Step 8: Explanation
                  </span>
                  <span style={{ fontWeight: 700, color: '#0f172a' }}>
                    Structured HSE Decision Rationale
                  </span>
                </div>
                <p style={{ color: '#334155', lineHeight: 1.5, whiteSpace: 'pre-line' }}>
                  {result.explanation}
                </p>
              </div>
            </div>
          )}
        </div>

        <div className="modal-footer">
          {!result ? (
            <>
              <button 
                type="button" 
                className="btn btn-outline" 
                onClick={onClose}
                disabled={loading}
              >
                Cancel
              </button>
              <button 
                type="submit" 
                form="analyze-form"
                id="btn-modal-analyze-submit"
                className="btn btn-accent" 
                disabled={loading}
              >
                {loading ? (
                  <>
                    <Clock size={14} className="spin" /> Analyzing Pipeline...
                  </>
                ) : (
                  <>
                    <Play size={14} /> Run SIF Analysis (Step 4)
                  </>
                )}
              </button>
            </>
          ) : (
            <>
              <button 
                type="button" 
                className="btn btn-outline" 
                onClick={handleReset}
              >
                Analyze Another
              </button>

              <button 
                type="button" 
                id="btn-proceed-to-review"
                className="btn btn-accent"
                style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '0.45rem', 
                  fontWeight: 700,
                  backgroundColor: '#2563eb',
                  color: '#ffffff'
                }}
                onClick={() => {
                  onClose();
                  if (onProceedToReview) {
                    onProceedToReview(result.report_id);
                  }
                }}
              >
                <span>Proceed to HSE Review (Step 10-12)</span>
                <ArrowRight size={15} />
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
