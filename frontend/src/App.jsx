import React, { useState, useEffect } from 'react';
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import Navbar from './components/Navbar';
import AnalyzeModal from './components/AnalyzeModal';
import JudgeDemoGuide from './components/JudgeDemoGuide';
import DashboardPage from './pages/DashboardPage';
import ReportsPage from './pages/ReportsPage';
import ReportDetailsPage from './pages/ReportDetailsPage';
import RiskPatternsPage from './pages/RiskPatternsPage';
import HSEReviewPage from './pages/HSEReviewPage';
import ImportReportsPage from './pages/ImportReportsPage';
import ActionsPage from './pages/ActionsPage';
import AnalyticsPage from './pages/AnalyticsPage';
import { PageTransition, useToast, EmptyState } from './components/ui';
import { BarChart2, FileText } from 'lucide-react';
import { fetchDashboardSummary, fetchDemoStatus, loadDemoDataset } from './services/api';

export default function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const toast = useToast();

  const [selectedReportId, setSelectedReportId] = useState(null);
  const [pendingReviewCount, setPendingReviewCount] = useState(0);
  const [unreadAlertsCount, setUnreadAlertsCount] = useState(0);
  const [backendOnline, setBackendOnline] = useState(true);
  const [isAnalyzeModalOpen, setIsAnalyzeModalOpen] = useState(false);
  const [demoLoading, setDemoLoading] = useState(false);
  const [isDemoLoaded, setIsDemoLoaded] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  // Hidden Presentation Mode State (activated via Ctrl+Shift+P or profile dropdown)
  const [isJudgeDemoActive, setIsJudgeDemoActive] = useState(false);
  const [judgeDemoStep, setJudgeDemoStep] = useState(1);

  // Ctrl+Shift+P keyboard shortcut to toggle Presentation Mode
  useEffect(() => {
    const handleKeyboard = (e) => {
      if (e.ctrlKey && e.shiftKey && (e.key === 'p' || e.key === 'P')) {
        e.preventDefault();
        setIsJudgeDemoActive((prev) => {
          if (!prev) {
            setJudgeDemoStep(1);
            navigate('/');
          }
          return !prev;
        });
      }
    };
    window.addEventListener('keydown', handleKeyboard);
    return () => window.removeEventListener('keydown', handleKeyboard);
  }, [navigate]);

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
    
    // Listen for manual triggers from other components
    const handleRefreshAlerts = () => {
      checkHealthAndCounts();
      setRefreshKey((k) => k + 1);
    };
    window.addEventListener('refresh-alerts', handleRefreshAlerts);
    
    return () => {
      clearInterval(timer);
      window.removeEventListener('refresh-alerts', handleRefreshAlerts);
    };
  }, []);

  const showToast = (msg, type = 'success') => {
    toast[type](msg);
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
    navigate(`/reports/details`);
    if (isJudgeDemoActive && (judgeDemoStep < 7 || judgeDemoStep > 9)) {
      setJudgeDemoStep(7);
    }
  };

  const handleBackToReports = () => {
    navigate('/reports');
    setSelectedReportId(null);
    if (isJudgeDemoActive) {
      setJudgeDemoStep(1);
    }
  };

  const handleAnalysisComplete = (result) => {
    showToast(`New Report Analyzed: ${result.report_id} (${result.priority})`);
    checkHealthAndCounts();
    setRefreshKey((k) => k + 1);
    if (isJudgeDemoActive) {
      setJudgeDemoStep(4);
    }
  };

  const handleProceedToReview = (reportId) => {
    setSelectedReportId(reportId);
    navigate('/reports/details');
    if (isJudgeDemoActive) {
      setJudgeDemoStep(8);
    }
  };

  const handleReviewSubmitted = (result) => {
    showToast(`HSE Review recorded: ${result.decision.toUpperCase()}`);
    checkHealthAndCounts();
    setRefreshKey((k) => k + 1);
    if (isJudgeDemoActive) {
      setJudgeDemoStep(9); // Advance to HSE confirms step
    }
  };

  const handleStartJudgeDemo = () => {
    setIsJudgeDemoActive((prev) => !prev);
    setJudgeDemoStep(1);
    navigate('/');
  };

  const handleNavigateTab = (tab) => {
    if (tab === 'dashboard') navigate('/');
    else if (tab === 'reports') navigate('/reports');
    else if (tab === 'patterns') navigate('/patterns');
    else if (tab === 'review') navigate('/review');
    else if (tab === 'details') navigate('/reports/details');
    else if (tab === 'actions') navigate('/actions');
    
    if (tab !== 'details') setSelectedReportId(null);
    
    if (isJudgeDemoActive) {
      if (tab === 'dashboard') setJudgeDemoStep(1);
      else if (tab === 'reports') setJudgeDemoStep(2);
      else if (tab === 'patterns') setJudgeDemoStep(11);
      else if (tab === 'actions') setJudgeDemoStep(10);
      else if (tab === 'review') setJudgeDemoStep(8);
    }
  };

  return (
    <div className="app-container">
      {/* Navigation Header */}
      <Navbar
        pendingReviewCount={pendingReviewCount}
        unreadAlertsCount={unreadAlertsCount}
        backendOnline={backendOnline}
        onOpenAnalyze={() => {
          setIsAnalyzeModalOpen(true);
          if (isJudgeDemoActive) setJudgeDemoStep(3); // Import or enter report step
        }}
        onLoadDemo={handleLoadDemo}
        demoLoading={demoLoading}
        isDemoLoaded={isDemoLoaded}
        onStartJudgeDemo={handleStartJudgeDemo}
        isJudgeDemoActive={isJudgeDemoActive}
      />

      {/* Hidden Presentation Mode — floating overlay (activated via Ctrl+Shift+P or profile dropdown) */}
      {isJudgeDemoActive && (
        <JudgeDemoGuide
          currentStep={judgeDemoStep}
          onStepChange={(step) => setJudgeDemoStep(step)}
          currentTab={location.pathname}
          onNavigateTab={handleNavigateTab}
          onOpenAnalyzeModal={() => setIsAnalyzeModalOpen(true)}
          selectedReportId={selectedReportId}
          onSelectReport={(id) => {
            setSelectedReportId(id);
            navigate('/reports/details');
          }}
          onClose={() => setIsJudgeDemoActive(false)}
        />
      )}

      {/* Main Content Area */}
      <main className="main-content">
        <AnimatePresence mode="wait">
          <Routes location={location} key={location.pathname}>
            <Route path="/" element={
              <PageTransition key={`dashboard-${refreshKey}`}>
                <DashboardPage
                  onNavigateTab={handleNavigateTab}
                  onSelectReport={handleSelectReport}
                />
              </PageTransition>
            } />
            <Route path="/reports" element={
              <PageTransition key={`reports-${refreshKey}`}>
                <ReportsPage onSelectReport={handleSelectReport} />
              </PageTransition>
            } />
            <Route path="/reports/details" element={
              selectedReportId ? (
                <PageTransition key={`details-${selectedReportId}`}>
                  <ReportDetailsPage
                    reportId={selectedReportId}
                    onBack={handleBackToReports}
                    onReviewSubmitted={handleReviewSubmitted}
                    onSelectReport={handleSelectReport}
                    onNavigateTab={handleNavigateTab}
                  />
                </PageTransition>
              ) : (
                <div style={{ padding: '4rem 2rem' }}>
                  <EmptyState 
                    icon={FileText}
                    title="No Report Selected"
                    message="Please select a report from the Reports or Review tab to view its details."
                  />
                </div>
              )
            } />
            <Route path="/import" element={
              <PageTransition key={`import-${refreshKey}`}>
                <ImportReportsPage />
              </PageTransition>
            } />
            <Route path="/patterns" element={
              <PageTransition key={`patterns-${refreshKey}`}>
                <RiskPatternsPage onSelectReport={handleSelectReport} />
              </PageTransition>
            } />
            <Route path="/review" element={
              <PageTransition key={`review-${refreshKey}`}>
                <HSEReviewPage onSelectReport={handleSelectReport} />
              </PageTransition>
            } />
            <Route path="/actions" element={<PageTransition key="actions"><ActionsPage onSelectReport={handleSelectReport} /></PageTransition>} />
            <Route path="/analytics" element={<PageTransition key="analytics"><AnalyticsPage /></PageTransition>} />
          </Routes>
        </AnimatePresence>
      </main>

      {/* Quick Analyze Dialog */}
      <AnalyzeModal
        isOpen={isAnalyzeModalOpen}
        onClose={() => setIsAnalyzeModalOpen(false)}
        onAnalysisComplete={handleAnalysisComplete}
        onProceedToReview={handleProceedToReview}
      />
    </div>
  );
}
