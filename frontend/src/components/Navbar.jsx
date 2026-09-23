import React from 'react';
import { 
  ShieldAlert, 
  LayoutDashboard, 
  FileText, 
  GitBranch, 
  CheckSquare, 
  PlusCircle, 
  Activity,
  CheckCircle2,
  AlertTriangle,
  BellRing,
  Sparkles
} from 'lucide-react';

export default function Navbar({ 
  currentTab, 
  setCurrentTab, 
  pendingReviewCount, 
  unreadAlertsCount = 0,
  backendOnline, 
  onOpenAnalyze,
  onLoadDemo,
  demoLoading = false,
  isDemoLoaded = false,
  onStartJudgeDemo,
  isJudgeDemoActive = false,
}) {
  return (
    <header className="navbar">
      <div className="navbar-inner">
        {/* Brand */}
        <div 
          className="brand-section" 
          style={{ cursor: 'pointer' }}
          onClick={() => setCurrentTab('dashboard')}
        >
          <div className="brand-icon-wrapper">
            <ShieldAlert size={22} color="#0f172a" />
          </div>
          <div className="brand-text">
            <h1>SIF SENTINEL</h1>
            <p>Industrial Precursor Risk Triage System</p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="nav-links">
          <button
            id="nav-dashboard"
            className={`nav-link ${currentTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setCurrentTab('dashboard')}
          >
            <LayoutDashboard size={16} />
            Dashboard
          </button>

          <button
            id="nav-reports"
            className={`nav-link ${currentTab === 'reports' ? 'active' : ''}`}
            onClick={() => setCurrentTab('reports')}
          >
            <FileText size={16} />
            Reports
          </button>

          <button
            id="nav-patterns"
            className={`nav-link ${currentTab === 'patterns' ? 'active' : ''}`}
            onClick={() => setCurrentTab('patterns')}
          >
            <GitBranch size={16} />
            Risk Patterns
          </button>

          <button
            id="nav-review"
            className={`nav-link ${currentTab === 'review' ? 'active' : ''}`}
            onClick={() => setCurrentTab('review')}
          >
            <CheckSquare size={16} />
            HSE Review
            {pendingReviewCount > 0 && (
              <span className="nav-link-badge">{pendingReviewCount}</span>
            )}
          </button>
        </nav>

        {/* Right Section Actions & Status */}
        <div className="nav-actions">
          {unreadAlertsCount > 0 && (
            <button
              className="btn btn-outline"
              style={{
                borderColor: 'var(--sif-high)',
                color: 'var(--sif-high)',
                backgroundColor: '#fef2f2',
                padding: '0.35rem 0.65rem',
                fontSize: '0.75rem',
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                gap: '0.35rem',
              }}
              onClick={() => setCurrentTab('dashboard')}
              title={`${unreadAlertsCount} active precursor alerts`}
            >
              <BellRing size={14} color="var(--sif-high)" />
              <span>{unreadAlertsCount} Alerts</span>
            </button>
          )}

          <div 
            className="system-status-indicator" 
            title={backendOnline ? "FastAPI Backend is connected" : "Connecting to backend..."}
          >
            <span className={`status-dot ${backendOnline ? '' : 'error'}`} />
            <span>{backendOnline ? "API Live" : "API Offline"}</span>
          </div>

          {/* 5-Minute SIH Judge Demonstration Flow Button */}
          {onStartJudgeDemo && (
            <button
              id="btn-start-judge-demo"
              className="btn btn-outline"
              onClick={onStartJudgeDemo}
              style={{
                borderColor: isJudgeDemoActive ? '#2563eb' : '#f59e0b',
                color: isJudgeDemoActive ? '#1d4ed8' : '#b45309',
                backgroundColor: isJudgeDemoActive ? '#eff6ff' : '#fffbeb',
                padding: '0.45rem 0.85rem',
                fontWeight: 700,
                fontSize: '0.8rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
              }}
              title="Start or toggle interactive 5-minute SIH judge demonstration (13 exact steps)"
            >
              <Sparkles size={15} color={isJudgeDemoActive ? '#2563eb' : '#d97706'} />
              <span>{isJudgeDemoActive ? 'Demo Flow Active' : '5-Min Judge Demo'}</span>
            </button>
          )}

          {/* One-Click Controlled Demo Dataset */}
          <button
            id="btn-demo-mode"
            className="btn btn-outline"
            onClick={onLoadDemo}
            disabled={demoLoading}
            style={{
              borderColor: '#3b82f6',
              color: '#1d4ed8',
              backgroundColor: '#eff6ff',
              padding: '0.45rem 0.85rem',
              fontWeight: 600,
              fontSize: '0.8rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
            }}
            title="One-click load 10 curated synthetic demo reports through the live AI pipeline"
          >
            <Sparkles size={15} color="#2563eb" className={demoLoading ? 'spin' : ''} />
            <span>{demoLoading ? 'Evaluating 10 Scenarios...' : isDemoLoaded ? 'Reload Demo Mode' : 'Load Demo Mode'}</span>
          </button>

          <button 
            id="btn-quick-analyze" 
            className="btn btn-primary" 
            onClick={onOpenAnalyze}
            style={{ padding: '0.45rem 0.85rem' }}
          >
            <PlusCircle size={15} />
            <span>Quick Analyze</span>
          </button>
        </div>
      </div>
    </header>
  );
}
