import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import AnalyzeModal from './components/AnalyzeModal';
import JudgeDemoGuide from './components/JudgeDemoGuide';
import DashboardPage from './pages/DashboardPage';
import ReportsPage from './pages/ReportsPage';
import ReportDetailsPage from './pages/ReportDetailsPage';
import RiskPatternsPage from './pages/RiskPatternsPage';
import HSEReviewPage from './pages/HSEReviewPage';
import { fetchDashboardSummary, fetchDemoStatus, loadDemoDataset, resetDemoDataset } from './services/api';
import { CheckCircle2, AlertTriangle, Info } from 'lucide-react';

export default function App() {
  const [currentTab, setCurrentTab] = useState('dashboard');
  const [selectedReportId, setSelectedReportId] = useState(null);
  const [pendingReviewCount, setPendingReviewCount] = useState(0);
  const [unreadAlertsCount, setUnreadAlertsCount] = useState(0);
  const [backendOnline, setBackendOnline] = useState(true);
  const [isAnalyzeModalOpen, setIsAnalyzeModalOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);
  const [demoLoading, setDemoLoading] = useState(false);
  const [isDemoLoaded, setIsDemoLoaded] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  // 5-Minute SIH Judge Demonstration Flow State
  const [isJudgeDemoActive, setIsJudgeDemoActive] = useState(false);
  const [judgeDemoStep, setJudgeDemoStep] = useState(1);

  // Check health and pending counts
  const checkHealthAndCounts = async () => {
    try {
      const summary = await fetchDashboardSummary();
      setPendingReviewCount(summary.pending_reviews_count || 0);
      setUnreadAlertsCount(summary.unread_alerts_count || 0);
      setBackendOnline(true);
    } catch (err) {
      console.warn("FastAPI backend connection check:", err.message);
      setBackendOnline(false);
    }
  };

  const checkDemoStatus = async () => {
    try {
      const status = await fetchDemoStatus();
      setIsDemoLoaded(status.is_demo_loaded);
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    checkHealthAndCounts();
    checkDemoStatus();
    const timer = setInterval(checkHealthAndCounts, 15000); // Check every 15s
    return () => clearInterval(timer);
  }, []);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 4500);
  };

  const handleLoadDemo = async () => {
    setDemoLoading(true);
    try {
      const res = await loadDemoDataset(true);
      setIsDemoLoaded(true);
      showToast(`Controlled Demo Loaded: ${res.total_loaded} synthetic observations evaluated through live AI pipeline!`);
      await checkHealthAndCounts();
      setRefreshKey((k) => k + 1);
    } catch (err) {
      showToast(`Failed to load demo: ${err.message}`);
    } finally {
      setDemoLoading(false);
    }
  };

  const handleSelectReport = (reportId) => {
    setSelectedReportId(reportId);
    setCurrentTab('details');
    if (isJudgeDemoActive && (judgeDemoStep < 10 || judgeDemoStep > 12)) {
      setJudgeDemoStep(10);
    }
  };

  const handleBackToReports = () => {
    setCurrentTab('reports');
    setSelectedReportId(null);
    if (isJudgeDemoActive) {
      setJudgeDemoStep(2);
    }
  };

  const handleAnalysisComplete = (result) => {
    showToast(`New Report Analyzed: ${result.report_id} (${result.priority})`);
    checkHealthAndCounts();
    setRefreshKey((k) => k + 1);
    if (isJudgeDemoActive) {
      setJudgeDemoStep(5);
    }
  };

  const handleProceedToReview = (reportId) => {
    setSelectedReportId(reportId);
    setCurrentTab('details');
    if (isJudgeDemoActive) {
      setJudgeDemoStep(10);
    }
  };

  const handleReviewSubmitted = (result) => {
    showToast(`HSE Review recorded: ${result.decision.toUpperCase()}`);
    checkHealthAndCounts();
    setRefreshKey((k) => k + 1);
    if (isJudgeDemoActive) {
      setJudgeDemoStep(12); // Advance to Audit Trail step
    }
  };

  const handleStartJudgeDemo = () => {
    setIsJudgeDemoActive((prev) => !prev);
    setJudgeDemoStep(1);
    setCurrentTab('dashboard');
  };

  const handleNavigateTab = (tab) => {
    setCurrentTab(tab);
    if (tab !== 'details') setSelectedReportId(null);
    if (isJudgeDemoActive) {
      if (tab === 'dashboard') setJudgeDemoStep(1);
      else if (tab === 'reports') setJudgeDemoStep(2);
      else if (tab === 'patterns') setJudgeDemoStep(13);
      else if (tab === 'review') setJudgeDemoStep(10);
    }
  };

  return (
    <div className="app-container">
      {/* Navigation Header */}
      <Navbar
        currentTab={currentTab}
        setCurrentTab={handleNavigateTab}
        pendingReviewCount={pendingReviewCount}
        unreadAlertsCount={unreadAlertsCount}
        backendOnline={backendOnline}
        onOpenAnalyze={() => {
          setIsAnalyzeModalOpen(true);
          if (isJudgeDemoActive) setJudgeDemoStep(3);
        }}
        onLoadDemo={handleLoadDemo}
        demoLoading={demoLoading}
        isDemoLoaded={isDemoLoaded}
        onStartJudgeDemo={handleStartJudgeDemo}
        isJudgeDemoActive={isJudgeDemoActive}
      />

      {/* 5-Minute SIH Judge Demonstration Stepper Guide */}
      {isJudgeDemoActive && (
        <JudgeDemoGuide
          currentStep={judgeDemoStep}
          onStepChange={(step) => setJudgeDemoStep(step)}
          currentTab={currentTab}
          onNavigateTab={handleNavigateTab}
          onOpenAnalyzeModal={() => setIsAnalyzeModalOpen(true)}
          selectedReportId={selectedReportId}
          onSelectReport={(id) => {
            setSelectedReportId(id);
            setCurrentTab('details');
          }}
          onClose={() => setIsJudgeDemoActive(false)}
        />
      )}

      {/* Main Content Area */}
      <main className="main-content">
        {currentTab === 'dashboard' && (
          <DashboardPage
            key={refreshKey}
            onNavigateTab={handleNavigateTab}
            onSelectReport={handleSelectReport}
          />
        )}

        {currentTab === 'reports' && (
          <ReportsPage key={refreshKey} onSelectReport={handleSelectReport} />
        )}

        {currentTab === 'details' && selectedReportId && (
          <ReportDetailsPage
            reportId={selectedReportId}
            onBack={handleBackToReports}
            onReviewSubmitted={handleReviewSubmitted}
            onSelectReport={handleSelectReport}
            onNavigateTab={handleNavigateTab}
          />
        )}

        {currentTab === 'patterns' && (
          <RiskPatternsPage key={refreshKey} onSelectReport={handleSelectReport} />
        )}

        {currentTab === 'review' && (
          <HSEReviewPage key={refreshKey} onSelectReport={handleSelectReport} />
        )}
      </main>

      {/* Quick Analyze Dialog */}
      <AnalyzeModal
        isOpen={isAnalyzeModalOpen}
        onClose={() => setIsAnalyzeModalOpen(false)}
        onAnalysisComplete={handleAnalysisComplete}
        onProceedToReview={handleProceedToReview}
      />

      {/* Toast Notification */}
      {toastMessage && (
        <div className="toast-container">
          <div className="toast">
            <CheckCircle2 size={16} color="#4ade80" />
            <span>{toastMessage}</span>
          </div>
        </div>
      )}
    </div>
  );
}
