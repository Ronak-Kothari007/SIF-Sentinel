/**
 * SIF Sentinel — REST API Client (Phase 10)
 * ==========================================
 * Connects the React frontend directly to the production FastAPI endpoints.
 * All metrics, tables, and risk patterns represent real evaluated HSE data.
 */

export const API_BASE = 'https://sif-sentinel-backend-gu7a.onrender.com/api/v1';

/**
 * Generic fetch wrapper with structured error handling
 */
async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const config = {
    headers: {
      'Content-Type': 'application/json',
      'Bypass-Tunnel-Reminder': 'true',
      ...options.headers,
    },
    ...options,
  };

  try {
    const res = await fetch(url, config);
    if (!res.ok) {
      let errorDetail = `HTTP ${res.status}: ${res.statusText}`;
      try {
        const errorJson = await res.json();
        if (errorJson.detail) {
          errorDetail = typeof errorJson.detail === 'string' 
            ? errorJson.detail 
            : JSON.stringify(errorJson.detail);
        }
      } catch {
        // Fallback to text status
      }
      throw new Error(errorDetail);
    }
    return await res.json();
  } catch (err) {
    console.error(`API Error on ${endpoint}:`, err);
    throw err;
  }
}

/**
 * 1. Fetch live executive dashboard summary
 * GET /api/v1/dashboard-summary
 */
export async function fetchDashboardSummary() {
  return await apiRequest('/dashboard-summary');
}

/**
 * 2. Fetch paginated reports list with optional filters
 * GET /api/v1/reports
 */
export async function fetchReports({ limit = 50, offset = 0, priority = '', hazard = '', activity = '' } = {}) {
  const params = new URLSearchParams();
  if (limit) params.append('limit', limit);
  if (offset) params.append('offset', offset);
  if (priority) params.append('priority', priority);
  if (hazard) params.append('hazard', hazard);
  if (activity) params.append('activity', activity);

  const query = params.toString() ? `?${params.toString()}` : '';
  return await apiRequest(`/reports${query}`);
}

/**
 * 3. Fetch full decision details for a single report
 * GET /api/v1/reports/{id}
 */
export async function fetchReportById(reportId) {
  return await apiRequest(`/reports/${encodeURIComponent(reportId)}`);
}

/**
 * 4. Fetch high-risk review queue
 * GET /api/v1/high-risk
 */
export async function fetchHighRiskReports(limit = 50) {
  return await apiRequest(`/high-risk?limit=${limit}`);
}

/**
 * 5. Fetch semantically similar reports via dense embeddings (all-MiniLM-L6-v2)
 * GET /api/v1/similar-reports/{id}
 */
export async function fetchSimilarReports(reportId, limit = 5, threshold = 0.40) {
  return await apiRequest(`/similar-reports/${encodeURIComponent(reportId)}?limit=${limit}&threshold=${threshold}`);
}

/**
 * 6. Fetch recurring risk patterns & clusters
 * GET /api/v1/patterns
 */
export async function fetchPatterns() {
  return await apiRequest('/patterns');
}

/**
 * 6. Submit human-in-the-loop HSE review determination
 * POST /api/v1/hse-review
 * Supports multi-dimensional correction: priority, activity, hazard, barrier
 */
export async function submitHSEReview({
  reportId,
  reviewerId = 'HSE-OFFICER-01',
  decision,
  correctedPriority = null,
  correctedActivity = null,
  correctedHazard = null,
  correctedBarrier = null,
  comments = '',
}) {
  return await apiRequest('/hse-review', {
    method: 'POST',
    body: JSON.stringify({
      report_id: reportId,
      reviewer_id: reviewerId,
      decision: decision.toLowerCase(), // 'confirmed' | 'rejected' | 'corrected'
      corrected_priority: correctedPriority || undefined,
      corrected_activity: correctedActivity || undefined,
      corrected_hazard: correctedHazard || undefined,
      corrected_barrier: correctedBarrier || undefined,
      comments: comments || undefined,
    }),
  });
}

/**
 * 7. Fetch immutable audit trail for a report
 * GET /api/v1/reports/{id}/audit-trail
 */
export async function fetchAuditTrail(reportId) {
  return await apiRequest(`/reports/${encodeURIComponent(reportId)}/audit-trail`);
}

/**
 * 8. Submit model annotation / officer feedback
 * POST /api/v1/feedback
 */
export async function submitFeedback({
  reportId,
  feedbackType = 'label_correction',
  notes,
  userSuggestedPriority = null,
  userId = 'HSE-OFFICER-01',
}) {
  return await apiRequest('/feedback', {
    method: 'POST',
    body: JSON.stringify({
      report_id: reportId,
      feedback_type: feedbackType,
      notes: notes,
      user_suggested_priority: userSuggestedPriority || undefined,
      user_id: userId || undefined,
    }),
  });
}

/**
 * 9. Fetch feedback annotations
 * GET /api/v1/feedback
 */
export async function fetchFeedback(reportId = null) {
  const query = reportId ? `?report_id=${encodeURIComponent(reportId)}` : '';
  return await apiRequest(`/feedback${query}`);
}

/**
 * 10. Submit new safety report for live AI + Rule analysis
 * POST /api/v1/analyze-report
 */
export async function analyzeReport({ reportText, reportId = null, location = null, recurringRiskSignal = null }) {
  const payload = {
    report_text: reportText,
  };
  if (reportId) payload.report_id = reportId;
  if (location) payload.location = location;
  if (recurringRiskSignal !== null && recurringRiskSignal !== undefined) {
    payload.recurring_risk_signal = parseFloat(recurringRiskSignal);
  }

  return await apiRequest('/analyze-report', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * 11. Fetch internal precursor alerts (Phase 13)
 * GET /api/v1/alerts
 */
export async function fetchAlerts(acknowledged = null, limit = 50) {
  const params = new URLSearchParams();
  if (acknowledged !== null) params.append('acknowledged', acknowledged);
  params.append('limit', limit);
  return await apiRequest(`/alerts?${params.toString()}`);
}

/**
 * 12. Acknowledge alert event (Phase 13)
 * POST /api/v1/alerts/{id}/acknowledge
 */
export async function acknowledgeAlert(alertId, officerId = 'HSE-OFFICER-01', notes = '') {
  return await apiRequest(`/alerts/${encodeURIComponent(alertId)}/acknowledge`, {
    method: 'POST',
    body: JSON.stringify({
      officer_id: officerId,
      notes: notes || undefined,
    }),
  });
}

/**
 * 13. Fetch report workflow lifecycle status (Phase 13)
 * GET /api/v1/workflow/status/{id}
 */
export async function fetchWorkflowStatus(reportId) {
  return await apiRequest(`/workflow/status/${encodeURIComponent(reportId)}`);
}

/**
 * 14. Demo Mode Endpoints (Phase 16)
 */
export async function fetchDemoStatus() {
  return await apiRequest('/demo/status');
}

export async function loadDemoDataset(resetFirst = true) {
  return await apiRequest(`/demo/load?reset_first=${resetFirst}`, {
    method: 'POST',
  });
}

export async function resetDemoDataset() {
  return await apiRequest('/demo/reset', {
    method: 'POST',
  });
}

/**
 * 15. Upload Document for Import
 * POST /api/v1/import/upload
 */
export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append('file', file);
  
  try {
    const res = await fetch(`${API_BASE}/import/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      let errDetail = await res.text();
      throw new Error(`Upload failed: ${res.status} ${errDetail}`);
    }
    return await res.json();
  } catch (err) {
    console.error("Upload API Error:", err);
    throw err;
  }
}

/**
 * 16. Process Extracted Text
 * POST /api/v1/import/process-text
 */
export async function processImportedText(
  reportText, 
  metadata = null, 
  tempFileId = null, 
  sourceFileName = null,
  originalExtractedData = null,
  userCorrectedData = null
) {
  return apiRequest(`/import/process-text`, {
    method: 'POST',
    body: JSON.stringify({ 
      report_text: reportText, 
      metadata,
      temp_file_id: tempFileId,
      source_file_name: sourceFileName,
      original_extracted_data: originalExtractedData,
      user_corrected_data: userCorrectedData
    }),
  });
}

/**
 * 17. Get Export URL
 * GET /api/v1/export/reports
 */
export function getExportUrl({ format = 'csv', exportType = 'current', priority = '', hazard = '', activity = '' } = {}) {
  const params = new URLSearchParams();
  params.append('format', format);
  params.append('export_type', exportType);
  if (priority) params.append('priority', priority);
  if (hazard) params.append('hazard', hazard);
  if (activity) params.append('activity', activity);

  return `${API_BASE}/reports/export/reports?${params.toString()}`;
}

/**
 * 18. Fetch Action Center items
 * GET /api/v1/actions
 */
export async function fetchActions(status = null, limit = 50) {
  const params = new URLSearchParams();
  if (status) params.append('status', status);
  params.append('limit', limit);
  return await apiRequest(`/actions?${params.toString()}`);
}

/**
 * 19. Update Action Status
 * PUT /api/v1/actions/{id}/status
 */
export async function updateActionStatus(actionId, status, assignedTo = null) {
  return await apiRequest(`/actions/${encodeURIComponent(actionId)}/status`, {
    method: 'PUT',
    body: JSON.stringify({
      status,
      assigned_to: assignedTo || undefined,
    }),
  });
}

