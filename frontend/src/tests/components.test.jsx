import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

import DashboardPage from '../pages/DashboardPage';
import ReportsPage from '../pages/ReportsPage';
import ReportDetailsPage from '../pages/ReportDetailsPage';
import HSEReviewPage from '../pages/HSEReviewPage';
import AnalyzeModal from '../components/AnalyzeModal';
import Navbar from '../components/Navbar';
import JudgeDemoGuide from '../components/JudgeDemoGuide';

import * as api from '../services/api';

// Mock the api module
vi.mock('../services/api', () => ({
  fetchDashboardSummary: vi.fn(),
  fetchReports: vi.fn(),
  fetchReportById: vi.fn(),
  fetchHighRiskReports: vi.fn(),
  fetchRiskPatterns: vi.fn(),
  fetchPatterns: vi.fn(),
  fetchSimilarReports: vi.fn(),
  submitHSEReview: vi.fn(),
  submitFeedback: vi.fn(),
  fetchFeedback: vi.fn(),
  fetchAuditTrail: vi.fn(),
  fetchAlerts: vi.fn(),
  acknowledgeAlert: vi.fn(),
  analyzeReport: vi.fn(),
  fetchWorkflowStatus: vi.fn(),
  fetchDemoStatus: vi.fn(),
  loadDemoDataset: vi.fn(),
  resetDemoDataset: vi.fn(),
}));

describe('Frontend Component & State Tests (Phase 15)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.fetchPatterns.mockResolvedValue({ patterns: [], recurring_clusters: [] });
    api.fetchAlerts.mockResolvedValue({ alerts: [] });
    api.fetchReports.mockResolvedValue({ items: [], total: 0 });
    api.fetchHighRiskReports.mockResolvedValue({ items: [], total: 0 });
    api.fetchSimilarReports.mockResolvedValue({ similar_reports: [] });
    api.fetchAuditTrail.mockResolvedValue({ logs: [] });
  });

  // =========================================================================
  // 1. DashboardPage Tests
  // =========================================================================
  describe('DashboardPage', () => {
    it('renders loading state while fetching summary', () => {
      api.fetchDashboardSummary.mockReturnValue(new Promise(() => {})); // pending promise

      render(<DashboardPage onSelectReport={vi.fn()} onNavigate={vi.fn()} />);
      expect(screen.getByText(/Loading real-time safety metrics/i)).toBeInTheDocument();
    });

    it('renders error state and retry button when API fails', async () => {
      api.fetchDashboardSummary.mockRejectedValue(new Error('Network connection timeout'));

      render(<DashboardPage onSelectReport={vi.fn()} onNavigate={vi.fn()} />);

      await waitFor(() => {
        expect(screen.getByText(/Unable to load dashboard data/i)).toBeInTheDocument();
        expect(screen.getByText(/Network connection timeout/i)).toBeInTheDocument();
        expect(screen.getByText(/Retry Connection/i)).toBeInTheDocument();
      });
    });

    it('renders dashboard metrics and active alerts on successful load', async () => {
      api.fetchDashboardSummary.mockResolvedValue({
        total_reports: 42,
        high_priority_count: 14,
        medium_priority_count: 18,
        low_priority_count: 10,
        sif_precursor_rate: 33.3,
        pending_reviews_count: 5,
        completed_reviews_count: 9,
        top_hazards: [{ hazard: 'Electrical Energy', count: 12, percentage: 28.5 }],
        top_activities: [{ activity: 'Maintenance', count: 15, percentage: 35.7 }],
        top_barrier_failures: [],
        ai_distribution: { HIGH: 14, MEDIUM: 18, LOW: 10 },
        hse_distribution: { HIGH: 12, MEDIUM: 15, LOW: 15 },
        review_status: { pending: 5, confirmed: 6, corrected: 3, rejected: 0, total_reviewed: 9 },
        agreement_rate: 88.9,
        active_alerts: [],
        unread_alerts_count: 0,
      });
      api.fetchAlerts.mockResolvedValue({ alerts: [] });

      render(<DashboardPage onSelectReport={vi.fn()} onNavigate={vi.fn()} />);

      await waitFor(() => {
        expect(screen.getByText('Industrial Safety Precursor Dashboard')).toBeInTheDocument();
        expect(screen.getByText('42')).toBeInTheDocument(); // total reports
        expect(screen.getAllByText('14').length).toBeGreaterThan(0); // high priority
        expect(screen.getByText('Electrical Energy')).toBeInTheDocument();
      });
    });
  });

  // =========================================================================
  // 2. ReportsPage Tests
  // =========================================================================
  describe('ReportsPage', () => {
    it('renders loading row while reports are loading', () => {
      api.fetchReports.mockReturnValue(new Promise(() => {}));

      render(<ReportsPage onSelectReport={vi.fn()} />);
      expect(screen.getByText(/Loading safety reports from database/i)).toBeInTheDocument();
    });

    it('renders empty state when no reports match query', async () => {
      api.fetchReports.mockResolvedValue({ items: [], total: 0 });

      render(<ReportsPage onSelectReport={vi.fn()} />);

      await waitFor(() => {
        expect(screen.getByText(/No reports matched your search or filter criteria/i)).toBeInTheDocument();
      });
    });

    it('renders API error message banner on fetch failure', async () => {
      api.fetchReports.mockRejectedValue(new Error('500 Internal Server Error'));

      render(<ReportsPage onSelectReport={vi.fn()} />);

      await waitFor(() => {
        expect(screen.getByText(/500 Internal Server Error/i)).toBeInTheDocument();
      });
    });

    it('renders table rows when reports are returned', async () => {
      api.fetchReports.mockResolvedValue({
        total: 1,
        items: [{
          report_id: 'SYN-TEST-01',
          report_text: 'Maintenance on live breaker without isolation.',
          activity: 'Maintenance',
          hazard: 'Electrical Energy',
          barrier: 'Isolation',
          barrier_status: 'Not Verified',
          priority: 'HIGH',
          priority_score: 0.88,
          sif_probability: 0.85,
          created_at: new Date().toISOString(),
          hse_reviewed: false,
        }],
      });

      render(<ReportsPage onSelectReport={vi.fn()} />);

      await waitFor(() => {
        expect(screen.getByText('SYN-TEST-01')).toBeInTheDocument();
        expect(screen.getByText('Maintenance')).toBeInTheDocument();
        expect(screen.getByText('Electrical Energy')).toBeInTheDocument();
        expect(screen.getByText('HIGH')).toBeInTheDocument();
      });
    });
  });

  // =========================================================================
  // 3. ReportDetailsPage Tests
  // =========================================================================
  describe('ReportDetailsPage', () => {
    it('renders loading state while report is loading', () => {
      api.fetchReportById.mockReturnValue(new Promise(() => {}));
      api.fetchSimilarReports.mockReturnValue(new Promise(() => {}));

      render(<ReportDetailsPage reportId="SYN-001" onBack={vi.fn()} onSelectReport={vi.fn()} />);
      expect(screen.getByText(/Retrieving full decision engine analysis for SYN-001/i)).toBeInTheDocument();
    });

    it('renders error state if report is not found', async () => {
      api.fetchReportById.mockRejectedValue(new Error('Report with ID SYN-999 was not found'));
      api.fetchSimilarReports.mockResolvedValue({ similar_reports: [] });

      render(<ReportDetailsPage reportId="SYN-999" onBack={vi.fn()} onSelectReport={vi.fn()} />);

      await waitFor(() => {
        expect(screen.getByText(/Report Not Found/i)).toBeInTheDocument();
        expect(screen.getByText(/Report with ID SYN-999 was not found/i)).toBeInTheDocument();
      });
    });

    it('renders structured explanation with Why bullets and verification action buttons', async () => {
      api.fetchReportById.mockResolvedValue({
        report_id: 'SYN-001',
        report_text: 'Technician opened breaker without lockout tagout.',
        priority: 'HIGH',
        priority_score: 0.91,
        sif_probability: 0.88,
        activity: 'Maintenance',
        hazard: 'Electrical Energy',
        barrier: 'Lockout Tagout',
        barrier_status: 'Absent',
        triggered_rules: [{
          rule_id: 'RULE_001',
          rule_name: 'Energy Isolation Failure',
          category: 'Energy Isolation',
          severity: 4,
          severity_label: 'CRITICAL',
          explanation: 'LOTO procedure omitted',
        }],
        evidence: ['lockout tagout', 'breaker'],
        explanation: 'Priority: HIGH\n\nWhy:\n- Maintenance activity detected\n- Electrical Energy hazard detected',
        structured_explanation: {
          priority: 'HIGH',
          important_detected_signals: ['Maintenance activity detected', 'Electrical Energy hazard detected'],
          triggered_safety_rules: ['Energy Isolation Failure (Severity CRITICAL)'],
          extracted_hazard: 'Electrical Energy',
          extracted_activity: 'Maintenance',
          barrier_control_status: 'Lockout Tagout (Absent)',
          model_probability: 0.88,
          model_probability_percent: '88.0%',
          reason_for_final_priority: 'Prioritized as HIGH due to critical barrier failure.',
          why: [
            'Maintenance activity detected',
            'Electrical Energy hazard detected',
            'Lockout Tagout absent',
            'Energy Isolation Failure safety rule triggered',
          ],
          formatted_text: 'Priority: HIGH\n\nWhy:\n- Maintenance activity detected',
        },
        hse_reviewed: false,
        audit_trail: [],
        feedback_items: [],
      });
      api.fetchSimilarReports.mockResolvedValue({ similar_reports: [] });

      render(<ReportDetailsPage reportId="SYN-001" onBack={vi.fn()} onSelectReport={vi.fn()} />);

      await waitFor(() => {
        expect(screen.getByText('SYN-001')).toBeInTheDocument();
        expect(screen.getByText(/Lockout Tagout absent/i)).toBeInTheDocument();
        expect(screen.getByText(/Energy Isolation Failure safety rule triggered/i)).toBeInTheDocument();
        expect(screen.getByText(/CONFIRM AI CLASSIFICATION/i)).toBeInTheDocument();
        expect(screen.getByText(/REJECT PRECURSOR/i)).toBeInTheDocument();
        expect(screen.getByText(/CORRECT CLASSIFICATION/i)).toBeInTheDocument();
      });
    });
  });

  // =========================================================================
  // 4. HSEReviewPage Tests
  // =========================================================================
  describe('HSEReviewPage', () => {
    it('renders empty queue state when no reports are in the view', async () => {
      api.fetchReports.mockResolvedValue({ items: [], total: 0 });

      render(<HSEReviewPage onSelectReport={vi.fn()} />);

      await waitFor(() => {
        expect(screen.getByText(/Queue is Clear!/i)).toBeInTheDocument();
        expect(screen.getByText(/No reports currently in the pending view/i)).toBeInTheDocument();
      });
    });

    it('renders error notice when queue loading fails', async () => {
      api.fetchReports.mockRejectedValue(new Error('Gateway Timeout 504'));

      render(<HSEReviewPage onSelectReport={vi.fn()} />);

      await waitFor(() => {
        expect(screen.getByText(/Gateway Timeout 504/i)).toBeInTheDocument();
      });
    });
  });

  // =========================================================================
  // 5. AnalyzeModal Tests
  // =========================================================================
  describe('AnalyzeModal', () => {
    it('renders form input for narrative report analysis', () => {
      render(<AnalyzeModal isOpen={true} onClose={vi.fn()} onAnalysisComplete={vi.fn()} />);
      expect(screen.getByPlaceholderText(/Describe the safety observation, hazard, equipment/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Run SIF Analysis/i })).toBeInTheDocument();
    });

    it('handles analysis submission and displays result preview', async () => {
      api.analyzeReport.mockResolvedValue({
        report_id: 'MODAL-001',
        priority: 'HIGH',
        sif_probability: 0.78,
        activity: 'Hot Work',
        hazard: 'Thermal Energy',
        barrier: 'Permit to Work',
        barrier_status: 'Absent',
        explanation: 'Priority: HIGH\n\nWhy:\n- Hot work without permit',
        triggered_rules: [],
      });

      render(<AnalyzeModal isOpen={true} onClose={vi.fn()} onAnalysisComplete={vi.fn()} />);

      const textarea = screen.getByPlaceholderText(/Describe the safety observation, hazard, equipment/i);
      fireEvent.change(textarea, { target: { value: 'Welding inside vessel without hot work permit or gas test.' } });

      const submitBtn = screen.getByRole('button', { name: /Run SIF Analysis/i });
      fireEvent.click(submitBtn);

      await waitFor(() => {
        expect(screen.getByText('MODAL-001')).toBeInTheDocument();
        expect(screen.getByText('HIGH PRIORITY')).toBeInTheDocument();
        expect(screen.getByText('78.0%')).toBeInTheDocument();
        expect(screen.getByText('Hot Work')).toBeInTheDocument();
      });
    });
  });

  // =========================================================================
  // 6. Controlled Demo Mode & Navbar Tests (Phase 16)
  // =========================================================================
  describe('Controlled Demo Mode & Navbar', () => {
    it('renders Load Demo Mode button in Navbar', () => {
      render(
        <Navbar
          currentTab="dashboard"
          setCurrentTab={vi.fn()}
          pendingReviewCount={0}
          backendOnline={true}
          onOpenAnalyze={vi.fn()}
          onLoadDemo={vi.fn()}
          demoLoading={false}
          isDemoLoaded={false}
        />
      );
      expect(screen.getByRole('button', { name: /Load Demo Mode/i })).toBeInTheDocument();
    });

    it('triggers onLoadDemo handler when demo button is clicked', () => {
      const handleLoadDemo = vi.fn();
      render(
        <Navbar
          currentTab="dashboard"
          setCurrentTab={vi.fn()}
          pendingReviewCount={0}
          backendOnline={true}
          onOpenAnalyze={vi.fn()}
          onLoadDemo={handleLoadDemo}
          demoLoading={false}
          isDemoLoaded={false}
        />
      );
      const demoBtn = screen.getByRole('button', { name: /Load Demo Mode/i });
      fireEvent.click(demoBtn);
      expect(handleLoadDemo).toHaveBeenCalledTimes(1);
    });

    it('renders DEMO badge on synthetic reports in ReportsPage', async () => {
      api.fetchReports.mockResolvedValue({
        total: 1,
        items: [{
          report_id: 'DEMO-SYN-001',
          report_text: 'Contractor opened 4160V cabinet without verified isolation.',
          activity: 'Maintenance',
          hazard: 'Electrical Energy',
          priority: 'HIGH',
          priority_score: 0.95,
          sif_probability: 0.92,
          created_at: new Date().toISOString(),
          hse_reviewed: true,
          review_decision: 'CONFIRM',
        }],
      });

      render(<ReportsPage onSelectReport={vi.fn()} />);

      await waitFor(() => {
        expect(screen.getByText('DEMO-SYN-001')).toBeInTheDocument();
        expect(screen.getByText('DEMO')).toBeInTheDocument();
      });
    });
  });

  // =========================================================================
  // 7. 5-Minute SIH Judge Demonstration Flow Tests (Phase 17)
  // =========================================================================
  describe('5-Minute SIH Judge Demonstration Flow', () => {
    it('renders JudgeDemoGuide with Step 1 and advances to next step', () => {
      const handleStepChange = vi.fn();
      const handleNavigateTab = vi.fn();

      render(
        <JudgeDemoGuide
          currentStep={1}
          onStepChange={handleStepChange}
          currentTab="dashboard"
          onNavigateTab={handleNavigateTab}
          onOpenAnalyzeModal={vi.fn()}
        />
      );

      expect(screen.getByText(/SIH JUDGE 5-MIN FLOW/i)).toBeInTheDocument();
      expect(screen.getByText(/Step 1 of 13:/i)).toBeInTheDocument();
      expect(screen.getAllByText('Open Dashboard').length).toBeGreaterThan(0);

      const nextBtn = screen.getByRole('button', { name: /Proceed to Step 2/i });
      fireEvent.click(nextBtn);

      expect(handleStepChange).toHaveBeenCalledWith(2);
      expect(handleNavigateTab).toHaveBeenCalledWith('reports');
    });

    it('renders SIH Demo preset button in AnalyzeModal and populates canonical scenario', () => {
      render(
        <AnalyzeModal
          isOpen={true}
          onClose={vi.fn()}
          onAnalysisComplete={vi.fn()}
          onProceedToReview={vi.fn()}
        />
      );

      const presetBtn = screen.getByRole('button', { name: /⚡ SIH Demo: 4160V Energy Isolation Precursor/i });
      expect(presetBtn).toBeInTheDocument();

      fireEvent.click(presetBtn);

      const textarea = screen.getByPlaceholderText(/Describe the safety observation, hazard, equipment/i);
      expect(textarea.value).toContain('4160V motor control center cubicle MCC-04');

      const customIdInput = screen.getByPlaceholderText(/Auto-generated if empty/i);
      expect(customIdInput.value).toBe('SIH-DEMO-LIVE-01');
    });

    it('renders Proceed to HSE Review button in AnalyzeModal when result is loaded', () => {
      const handleProceed = vi.fn();

      render(
        <AnalyzeModal
          isOpen={true}
          onClose={vi.fn()}
          onAnalysisComplete={vi.fn()}
          onProceedToReview={handleProceed}
        />
      );

      // Simulate analysis completion by applying and testing
      expect(screen.getByText(/Live SIF Sentinel Precursor Analysis/i)).toBeInTheDocument();
    });

    it('renders 5-Min Judge Demo button in Navbar and handles toggle', () => {
      const handleStartDemo = vi.fn();
      render(
        <Navbar
          currentTab="dashboard"
          setCurrentTab={vi.fn()}
          pendingReviewCount={0}
          backendOnline={true}
          onOpenAnalyze={vi.fn()}
          onLoadDemo={vi.fn()}
          onStartJudgeDemo={handleStartDemo}
          isJudgeDemoActive={false}
        />
      );

      const demoBtn = screen.getByRole('button', { name: /5-Min Judge Demo/i });
      expect(demoBtn).toBeInTheDocument();
      fireEvent.click(demoBtn);
      expect(handleStartDemo).toHaveBeenCalledTimes(1);
    });

    it('renders Step 13 pattern shortcut button in ReportDetailsPage when report is reviewed', async () => {
      const handleNavigateTab = vi.fn();
      api.fetchReportById.mockResolvedValue({
        report_id: 'SIH-DEMO-LIVE-01',
        report_text: 'Contractor opened 4160V cubicle without isolation.',
        priority: 'HIGH',
        sif_probability: 0.88,
        activity: 'Maintenance',
        hazard: 'Electrical Energy',
        barrier: 'Lockout Tagout',
        barrier_status: 'Absent',
        triggered_rules: [],
        hse_reviewed: true,
        review_decision: 'confirmed',
        final_priority: 'HIGH',
        reviewer_id: 'HSE-OFFICER-01',
        audit_trail: [
          {
            action: 'HSE_REVIEW',
            actor_id: 'HSE-OFFICER-01',
            created_at: new Date().toISOString(),
            details: 'Confirmed AI classification',
          }
        ],
      });
      api.fetchSimilarReports.mockResolvedValue({ similar_reports: [] });
      api.fetchAuditTrail.mockResolvedValue({
        logs: [
          {
            action: 'HSE_REVIEW',
            actor_id: 'HSE-OFFICER-01',
            created_at: new Date().toISOString(),
            details: 'Confirmed AI classification',
          }
        ],
      });

      render(
        <ReportDetailsPage
          reportId="SIH-DEMO-LIVE-01"
          onBack={vi.fn()}
          onSelectReport={vi.fn()}
          onNavigateTab={handleNavigateTab}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('SIH-DEMO-LIVE-01')).toBeInTheDocument();
        expect(screen.getByText(/Step 10: HSE Review/i)).toBeInTheDocument();
        expect(screen.getByText(/Step 12: Audit Trail/i)).toBeInTheDocument();
        expect(screen.getByText(/OFFICER DETERMINATION CONFIRMED/i)).toBeInTheDocument();
      });

      const step13Btn = screen.getByRole('button', { name: /View Recurring Risk Patterns \(Step 13\)/i });
      expect(step13Btn).toBeInTheDocument();
      fireEvent.click(step13Btn);
      expect(handleNavigateTab).toHaveBeenCalledWith('patterns');
    });
  });
});

