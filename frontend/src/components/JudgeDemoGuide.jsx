import React, { useState } from 'react';
import { 
  Sparkles, 
  ChevronRight, 
  ChevronLeft, 
  CheckCircle2, 
  AlertTriangle, 
  Maximize2, 
  Minimize2, 
  RotateCcw,
  Play,
  ArrowRight,
  ShieldAlert,
  GitBranch,
  Layers,
  History,
  FileText
} from 'lucide-react';

export const JUDGE_STEPS = [
  {
    step: 1,
    title: "Open Dashboard",
    badge: "Executive KPIs",
    talkingPoint: "Inspect executive safety KPIs: total observations, real-time SIF precursor rate (30-40%), distribution, top hazards, and active alerts.",
    targetTab: 'dashboard',
  },
  {
    step: 2,
    title: "Show Existing Reports",
    badge: "Historical Triage",
    talkingPoint: "Show historical baseline industrial reports. Notice priority badges, NLP entity extractions, and synthetic demo indicators.",
    targetTab: 'reports',
  },
  {
    step: 3,
    title: "Submit a New Safety Report",
    badge: "Field Narrative",
    talkingPoint: "Open live analysis modal with the canonical 4160V motor control center electrical isolation observation without LOTO.",
    actionType: 'open_modal',
  },
  {
    step: 4,
    title: "Click Analyze",
    badge: "Real-Time Pipeline",
    talkingPoint: "Execute real-time pipeline combining fine-tuned DistilBERT transformer classification and deterministic OSHA/IOGP safety rules.",
    actionType: 'run_analyze',
  },
  {
    step: 5,
    title: "Show AI Result",
    badge: "Transformer Inference",
    talkingPoint: "SIF Precursor Probability computed live (~88-92%). Real PyTorch neural model evaluation, zero hardcoded numbers.",
  },
  {
    step: 6,
    title: "Show Extracted Context",
    badge: "NLP Domain Extraction",
    talkingPoint: "NLP extraction identifies Activity (Maintenance), Hazard (Electrical Energy), and Barrier Status (Lockout Tagout - Absent/Not Verified).",
  },
  {
    step: 7,
    title: "Show Triggered Safety Rule",
    badge: "Deterministic Rules",
    talkingPoint: "Deterministic rule RULE_001 (Energy Isolation Failure - Severity 4 Critical) triggers, preventing black-box hallucinations.",
  },
  {
    step: 8,
    title: "Show Explanation",
    badge: "Explainability",
    talkingPoint: "Structured HSE explanation items directly grounded in physical signals: Maintenance detected, Electrical hazard, and LOTO omission.",
  },
  {
    step: 9,
    title: "Show HIGH Priority",
    badge: "Automated Escalation",
    talkingPoint: "System assigns HIGH priority and automatically places the report into the mandatory HSE officer verification queue.",
    targetTab: 'details',
  },
  {
    step: 10,
    title: "Show HSE Review",
    badge: "Human-in-the-Loop",
    talkingPoint: "Review the dual panel: Original AI model prediction preserved in full alongside HSE officer determination interface.",
    targetTab: 'details',
  },
  {
    step: 11,
    title: "Click CONFIRM",
    badge: "Officer Validation",
    talkingPoint: "Safety officer clicks CONFIRM. Validation is registered non-destructively without overwriting the original AI prediction.",
    actionType: 'click_confirm',
  },
  {
    step: 12,
    title: "Show Audit Trail",
    badge: "Regulatory Compliance",
    talkingPoint: "Immutable audit log records exact timestamp, officer ID (HSE-OFFICER-01), action (HSE_REVIEW), and validation state.",
    actionType: 'scroll_audit',
  },
  {
    step: 13,
    title: "Show Recurring Risk Pattern",
    badge: "Sentence Transformers",
    talkingPoint: "Sentence Transformers (all-MiniLM-L6-v2) automatically cluster this incident with matching electrical isolation precursors across the site!",
    targetTab: 'patterns',
  },
];

export default function JudgeDemoGuide({
  currentStep = 1,
  onStepChange,
  currentTab,
  onNavigateTab,
  onOpenAnalyzeModal,
  selectedReportId,
  onSelectReport,
  onConfirmReport,
  isModalOpen = false,
  isAnalyzed = false,
  onClose,
}) {
  const [isMinimized, setIsMinimized] = useState(false);

  const stepInfo = JUDGE_STEPS[currentStep - 1] || JUDGE_STEPS[0];
  const progressPercent = Math.round((currentStep / 13) * 100);

  const handleNext = () => {
    const next = currentStep < 13 ? currentStep + 1 : 1;
    executeStepTransition(next);
  };

  const handlePrev = () => {
    const prev = currentStep > 1 ? currentStep - 1 : 13;
    executeStepTransition(prev);
  };

  const executeStepTransition = (stepNum) => {
    onStepChange(stepNum);
    const target = JUDGE_STEPS[stepNum - 1];
    if (!target) return;

    if (target.targetTab && onNavigateTab) {
      onNavigateTab(target.targetTab);
    }

    if (stepNum === 3 && onOpenAnalyzeModal) {
      onOpenAnalyzeModal();
    }

    if (stepNum === 10 || stepNum === 11 || stepNum === 12) {
      if (onSelectReport && (!selectedReportId || selectedReportId === '')) {
        onSelectReport('SIH-DEMO-LIVE-01');
      }
      if (onNavigateTab) {
        onNavigateTab('details');
      }
    }

    if (stepNum === 12) {
      setTimeout(() => {
        const auditEl = document.getElementById('audit-trail-section');
        if (auditEl) {
          auditEl.scrollIntoView({ behavior: 'smooth' });
        }
      }, 150);
    }
  };

  if (isMinimized) {
    return (
      <div 
        style={{
          position: 'fixed',
          bottom: '1.25rem',
          right: '1.25rem',
          zIndex: 9999,
          backgroundColor: '#0f172a',
          color: '#ffffff',
          borderRadius: '9999px',
          padding: '0.5rem 1rem',
          boxShadow: '0 10px 25px -5px rgba(0,0,0,0.4)',
          display: 'flex',
          alignItems: 'center',
          gap: '0.65rem',
          cursor: 'pointer',
          border: '1px solid #3b82f6',
        }}
        onClick={() => setIsMinimized(false)}
        title="Click to expand SIH Judge Demonstration Guide"
      >
        <Sparkles size={16} color="#60a5fa" />
        <span style={{ fontSize: '0.8rem', fontWeight: 700 }}>
          SIH Demo Flow: Step {currentStep}/13
        </span>
        <span style={{ fontSize: '0.75rem', color: '#93c5fd' }}>
          ({stepInfo.title})
        </span>
        <Maximize2 size={14} color="#94a3b8" />
      </div>
    );
  }

  return (
    <aside 
      className="judge-demo-guide"
      aria-label="SIH Judge Demonstration Guide"
      style={{
        backgroundColor: '#0f172a',
        color: '#f8fafc',
        borderBottom: '2px solid #2563eb',
        padding: '0.75rem 1.5rem',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.25)',
        position: 'relative',
        zIndex: 40,
      }}
    >
      <div style={{ maxWidth: '1360px', margin: '0 auto' }}>
        {/* Top bar with Step Counter, Badges & Minimizer */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
              backgroundColor: '#1e3a8a',
              color: '#93c5fd',
              padding: '0.2rem 0.6rem',
              borderRadius: '9999px',
              fontSize: '0.75rem',
              fontWeight: 700,
              letterSpacing: '0.04em',
              border: '1px solid #3b82f6',
            }}>
              <Sparkles size={13} color="#60a5fa" />
              <span>SIH JUDGE 5-MIN FLOW</span>
            </div>

            <span style={{ 
              fontWeight: 800, 
              fontSize: '0.9rem', 
              color: '#ffffff',
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem'
            }}>
              <span>Step {currentStep} of 13:</span>
              <span style={{ color: '#60a5fa' }}>{stepInfo.title}</span>
            </span>

            <span style={{
              fontSize: '0.7rem',
              padding: '0.15rem 0.5rem',
              borderRadius: '4px',
              backgroundColor: '#1e293b',
              color: '#cbd5e1',
              border: '1px solid #334155',
            }}>
              {stepInfo.badge}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <button
              type="button"
              className="btn btn-outline"
              style={{
                fontSize: '0.75rem',
                padding: '0.25rem 0.5rem',
                color: '#94a3b8',
                borderColor: '#334155',
                backgroundColor: '#1e293b',
              }}
              onClick={() => executeStepTransition(1)}
              title="Reset flow to Step 1"
            >
              <RotateCcw size={12} style={{ marginRight: '3px' }} /> Restart
            </button>

            <button
              type="button"
              className="btn btn-outline"
              style={{
                fontSize: '0.75rem',
                padding: '0.25rem 0.45rem',
                color: '#94a3b8',
                borderColor: '#334155',
                backgroundColor: '#1e293b',
              }}
              onClick={() => setIsMinimized(true)}
              title="Minimize guide to corner badge"
            >
              <Minimize2 size={13} />
            </button>
          </div>
        </div>

        {/* Step Indicator Pills (1 to 13) */}
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '0.25rem', 
          overflowX: 'auto', 
          paddingBottom: '0.4rem',
          marginBottom: '0.5rem',
          scrollbarWidth: 'none',
        }}>
          {JUDGE_STEPS.map((s) => {
            const isActive = s.step === currentStep;
            const isCompleted = s.step < currentStep;
            return (
              <button
                key={s.step}
                type="button"
                onClick={() => executeStepTransition(s.step)}
                style={{
                  background: isActive ? '#2563eb' : isCompleted ? '#1e293b' : '#090d16',
                  color: isActive ? '#ffffff' : isCompleted ? '#93c5fd' : '#64748b',
                  border: `1px solid ${isActive ? '#60a5fa' : isCompleted ? '#3b82f6' : '#1e293b'}`,
                  borderRadius: '4px',
                  padding: '0.2rem 0.5rem',
                  fontSize: '0.7rem',
                  fontWeight: isActive ? 800 : 500,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.25rem',
                  whiteSpace: 'nowrap',
                  transition: 'all 0.15s ease',
                }}
                title={`Jump to Step ${s.step}: ${s.title}`}
              >
                <span>{s.step}.</span>
                <span>{s.title}</span>
                {isCompleted && <CheckCircle2 size={10} color="#60a5fa" />}
              </button>
            );
          })}
        </div>

        {/* Cues & Action Row */}
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center', 
          flexWrap: 'wrap', 
          gap: '0.75rem',
          backgroundColor: '#1e293b',
          padding: '0.6rem 0.85rem',
          borderRadius: '6px',
          border: '1px solid #334155',
        }}>
          <div style={{ flex: 1, minWidth: '280px' }}>
            <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.15rem' }}>
              Judge Speaking Cue / Live Pipeline Point:
            </div>
            <div style={{ fontSize: '0.825rem', color: '#f1f5f9', lineHeight: 1.4 }}>
              "{stepInfo.talkingPoint}"
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexShrink: 0 }}>
            <button
              type="button"
              className="btn btn-outline"
              style={{
                fontSize: '0.75rem',
                padding: '0.35rem 0.65rem',
                color: '#cbd5e1',
                borderColor: '#475569',
                backgroundColor: '#0f172a',
              }}
              onClick={handlePrev}
              disabled={currentStep === 1}
            >
              <ChevronLeft size={14} /> Back
            </button>

            {currentStep < 13 ? (
              <button
                type="button"
                id="btn-guide-next"
                className="btn btn-accent"
                style={{
                  fontSize: '0.8rem',
                  padding: '0.4rem 0.95rem',
                  fontWeight: 700,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.35rem',
                }}
                onClick={handleNext}
              >
                <span>Proceed to Step {currentStep + 1}</span>
                <ChevronRight size={14} />
              </button>
            ) : (
              <button
                type="button"
                id="btn-guide-restart"
                className="btn btn-primary"
                style={{
                  fontSize: '0.8rem',
                  padding: '0.4rem 0.95rem',
                  fontWeight: 700,
                  backgroundColor: '#16a34a',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.35rem',
                }}
                onClick={() => executeStepTransition(1)}
              >
                <CheckCircle2 size={14} />
                <span>Demo Complete! (Restart)</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </aside>
  );
}
