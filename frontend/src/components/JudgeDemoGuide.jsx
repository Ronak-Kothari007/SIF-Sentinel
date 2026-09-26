import React, { useState, useEffect, useRef } from 'react';
import {
  ChevronRight,
  ChevronLeft,
  SkipForward,
  X,
  Play,
  LayoutDashboard,
  FileText,
  Upload,
  Search,
  ShieldAlert,
  AlertTriangle,
  ArrowUpCircle,
  UserCheck,
  CheckCircle,
  Zap,
  GitBranch,
  Download
} from 'lucide-react';

export const PRESENTATION_STEPS = [
  {
    step: 1,
    title: 'Overview',
    narrative: 'Welcome to SIF Sentinel — an AI-powered industrial precursor risk triage system. The dashboard shows live executive KPIs: total observations, real-time SIF precursor rates, hazard distribution, and active alerts.',
    icon: LayoutDashboard,
    targetTab: 'dashboard',
    accent: '#60a5fa',
  },
  {
    step: 2,
    title: 'New report arrives',
    narrative: 'Field observers submit safety observations continuously. The reports list shows each observation with its AI-assigned priority, NLP-extracted entities, and triage status.',
    icon: FileText,
    targetTab: 'reports',
    accent: '#818cf8',
  },
  {
    step: 3,
    title: 'Import or enter report',
    narrative: 'Open the analysis modal to enter a new safety observation. You can type a narrative directly or import from external systems. Let\'s submit a live observation now.',
    icon: Upload,
    actionType: 'open_modal',
    accent: '#a78bfa',
  },
  {
    step: 4,
    title: 'Extracted information',
    narrative: 'The NLP pipeline extracts structured entities: Activity type, Hazard category, Barrier status, and Equipment involved — all from unstructured field narrative text.',
    icon: Search,
    actionType: 'run_analyze',
    accent: '#c084fc',
  },
  {
    step: 5,
    title: 'Safety assessment',
    narrative: 'A fine-tuned DistilBERT transformer computes the SIF Precursor Probability in real time. This is live neural inference — zero hardcoded numbers.',
    icon: ShieldAlert,
    accent: '#f472b6',
  },
  {
    step: 6,
    title: 'Critical barrier identified',
    narrative: 'Deterministic safety rules cross-check the AI prediction. When a critical energy isolation barrier is absent, the rule engine flags it — preventing black-box hallucinations.',
    icon: AlertTriangle,
    accent: '#fb923c',
  },
  {
    step: 7,
    title: 'Priority raised',
    narrative: 'The system assigns HIGH priority based on the combined AI assessment and rule triggers. The report is automatically escalated into the mandatory HSE verification queue.',
    icon: ArrowUpCircle,
    targetTab: 'details',
    accent: '#f87171',
  },
  {
    step: 8,
    title: 'HSE review required',
    narrative: 'The dual-panel review interface preserves the original AI prediction alongside the HSE officer\'s determination. Human-in-the-loop ensures accountability.',
    icon: UserCheck,
    targetTab: 'details',
    accent: '#fb7185',
  },
  {
    step: 9,
    title: 'HSE confirms / corrects',
    narrative: 'The safety officer validates or corrects the AI assessment. The decision is recorded non-destructively — the original prediction is never overwritten.',
    icon: CheckCircle,
    actionType: 'click_confirm',
    accent: '#34d399',
  },
  {
    step: 10,
    title: 'Action created',
    narrative: 'Corrective actions are tracked with assignees, deadlines, and status. Each action links back to the originating safety observation for full traceability.',
    icon: Zap,
    targetTab: 'actions',
    accent: '#fbbf24',
  },
  {
    step: 11,
    title: 'Emerging pattern',
    narrative: 'Sentence Transformers automatically cluster similar incidents, revealing recurring risk patterns across the site. This observation matches other electrical isolation precursors.',
    icon: GitBranch,
    targetTab: 'patterns',
    accent: '#2dd4bf',
  },
  {
    step: 12,
    title: 'Download assessment',
    narrative: 'Export the full safety assessment as CSV or PDF. All data — AI predictions, HSE reviews, audit trails, and pattern analysis — is available for regulatory reporting.',
    icon: Download,
    targetTab: 'dashboard',
    accent: '#60a5fa',
  },
];

// Keep backward compat for any external references
export const JUDGE_STEPS = PRESENTATION_STEPS;

const TOTAL_STEPS = PRESENTATION_STEPS.length;
const APPROX_SECONDS_PER_STEP = 25;

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
  const [isExiting, setIsExiting] = useState(false);
  const [slideDirection, setSlideDirection] = useState('next');
  const [isAnimating, setIsAnimating] = useState(false);
  const overlayRef = useRef(null);

  const stepInfo = PRESENTATION_STEPS[currentStep - 1] || PRESENTATION_STEPS[0];
  const StepIcon = stepInfo.icon;
  const progressPercent = (currentStep / TOTAL_STEPS) * 100;
  const remainingSteps = TOTAL_STEPS - currentStep;
  const remainingTime = remainingSteps * APPROX_SECONDS_PER_STEP;

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return m > 0 ? `${m}m ${s}s` : `${s}s`;
  };

  const animateTransition = (direction, callback) => {
    if (isAnimating) return;
    setSlideDirection(direction);
    setIsAnimating(true);
    setTimeout(() => {
      callback();
      setTimeout(() => setIsAnimating(false), 50);
    }, 180);
  };

  const executeStepTransition = (stepNum) => {
    onStepChange(stepNum);
    const target = PRESENTATION_STEPS[stepNum - 1];
    if (!target) return;

    if (target.targetTab && onNavigateTab) {
      onNavigateTab(target.targetTab);
    }

    if (target.actionType === 'open_modal' && onOpenAnalyzeModal) {
      onOpenAnalyzeModal();
    }

    if (stepNum === 7 || stepNum === 8 || stepNum === 9) {
      if (onSelectReport && (!selectedReportId || selectedReportId === '')) {
        onSelectReport('SIH-DEMO-LIVE-01');
      }
      if (onNavigateTab) {
        onNavigateTab('details');
      }
      
      // Auto-scroll to HSE Review section for steps 8 and 9
      if (stepNum === 8 || stepNum === 9) {
        setTimeout(() => {
          document.getElementById('hse-review-section')?.scrollIntoView({ behavior: 'smooth' });
        }, 400); // Give React Router time to render
      } else if (stepNum === 7) {
        setTimeout(() => {
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }, 400);
      }
    }
  };

  const handleNext = () => {
    if (currentStep >= TOTAL_STEPS) return;
    animateTransition('next', () => executeStepTransition(currentStep + 1));
  };

  const handlePrev = () => {
    if (currentStep <= 1) return;
    animateTransition('prev', () => executeStepTransition(currentStep - 1));
  };

  const handleSkip = () => {
    const skipTo = Math.min(currentStep + 2, TOTAL_STEPS);
    if (skipTo === currentStep) return;
    animateTransition('next', () => executeStepTransition(skipTo));
  };

  const handleClose = () => {
    setIsExiting(true);
    setTimeout(() => {
      if (onClose) onClose();
    }, 280);
  };

  // Keyboard navigation
  useEffect(() => {
    const handler = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) return;
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        e.preventDefault();
        handleNext();
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        e.preventDefault();
        handlePrev();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        handleClose();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [currentStep, isAnimating]);

  // SVG progress ring parameters
  const ringSize = 36;
  const ringStroke = 3;
  const ringRadius = (ringSize - ringStroke) / 2;
  const ringCircumference = 2 * Math.PI * ringRadius;
  const ringOffset = ringCircumference - (progressPercent / 100) * ringCircumference;

  return (
    <div
      ref={overlayRef}
      className={`presentation-overlay ${isExiting ? 'presentation-overlay--exiting' : ''}`}
      role="complementary"
      aria-label="Presentation Mode"
    >
      {/* Header row */}
      <div className="presentation-header">
        <div className="presentation-header-left">
          {/* Progress ring */}
          <div className="presentation-progress-ring-wrapper">
            <svg width={ringSize} height={ringSize} className="presentation-progress-ring">
              <circle
                cx={ringSize / 2}
                cy={ringSize / 2}
                r={ringRadius}
                fill="none"
                stroke="rgba(255,255,255,0.08)"
                strokeWidth={ringStroke}
              />
              <circle
                cx={ringSize / 2}
                cy={ringSize / 2}
                r={ringRadius}
                fill="none"
                stroke={stepInfo.accent}
                strokeWidth={ringStroke}
                strokeDasharray={ringCircumference}
                strokeDashoffset={ringOffset}
                strokeLinecap="round"
                className="presentation-progress-ring-fill"
              />
            </svg>
            <span className="presentation-step-number">{currentStep}</span>
          </div>

          <div className="presentation-title-block">
            <div className="presentation-label">
              <Play size={10} />
              <span>Presentation Mode</span>
              <span className="presentation-time-remaining">{formatTime(remainingTime)} left</span>
            </div>
            <div className="presentation-step-title" style={{ color: stepInfo.accent }}>
              {stepInfo.title}
            </div>
          </div>
        </div>

        <button
          className="presentation-close-btn"
          onClick={handleClose}
          title="Close Presentation Mode (Esc)"
          aria-label="Close Presentation Mode"
        >
          <X size={14} />
        </button>
      </div>

      {/* Step dots timeline */}
      <div className="presentation-dots">
        {PRESENTATION_STEPS.map((s) => (
          <button
            key={s.step}
            className={`presentation-dot ${
              s.step === currentStep ? 'presentation-dot--active' : ''
            } ${s.step < currentStep ? 'presentation-dot--completed' : ''}`}
            style={s.step === currentStep ? { backgroundColor: stepInfo.accent, boxShadow: `0 0 6px ${stepInfo.accent}55` } : {}}
            onClick={() => {
              const dir = s.step > currentStep ? 'next' : 'prev';
              animateTransition(dir, () => executeStepTransition(s.step));
            }}
            title={`Step ${s.step}: ${s.title}`}
            aria-label={`Go to step ${s.step}: ${s.title}`}
          />
        ))}
      </div>

      {/* Narrative card */}
      <div className={`presentation-narrative ${isAnimating ? `presentation-narrative--${slideDirection}` : ''}`}>
        <div className="presentation-narrative-icon" style={{ color: stepInfo.accent }}>
          <StepIcon size={16} />
        </div>
        <p className="presentation-narrative-text">{stepInfo.narrative}</p>
      </div>

      {/* Controls */}
      <div className="presentation-controls">
        <button
          className="presentation-btn presentation-btn--secondary"
          onClick={handlePrev}
          disabled={currentStep <= 1}
          title="Previous step"
        >
          <ChevronLeft size={14} />
          <span>Prev</span>
        </button>

        <button
          className="presentation-btn presentation-btn--ghost"
          onClick={handleSkip}
          disabled={currentStep >= TOTAL_STEPS}
          title="Skip ahead (+2 steps)"
        >
          <SkipForward size={13} />
          <span>Skip</span>
        </button>

        {currentStep < TOTAL_STEPS ? (
          <button
            className="presentation-btn presentation-btn--primary"
            onClick={handleNext}
            title="Next step"
            style={{ '--btn-accent': stepInfo.accent }}
          >
            <span>Next</span>
            <ChevronRight size={14} />
          </button>
        ) : (
          <button
            className="presentation-btn presentation-btn--finish"
            onClick={handleClose}
            title="End presentation"
          >
            <CheckCircle size={14} />
            <span>Finish</span>
          </button>
        )}
      </div>
    </div>
  );
}
