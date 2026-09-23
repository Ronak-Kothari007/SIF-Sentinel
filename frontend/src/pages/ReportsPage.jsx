import React, { useState, useEffect } from 'react';
import { 
  Search, 
  Filter, 
  RefreshCw, 
  ChevronRight, 
  ArrowUpDown, 
  Calendar,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ExternalLink
} from 'lucide-react';
import { fetchReports } from '../services/api';

export default function ReportsPage({ onSelectReport }) {
  const [reports, setReports] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters & Search
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPriority, setSelectedPriority] = useState('');
  const [selectedHazard, setSelectedHazard] = useState('');

  const loadReports = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchReports({
        limit: 100,
        offset: 0,
        priority: selectedPriority || undefined,
        hazard: selectedHazard || undefined,
      });

      setReports(data.items || []);
      setTotalCount(data.total || 0);
    } catch (err) {
      console.error("Error loading reports list:", err);
      setError(err.message || "Failed to load reports from API");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReports();
  }, [selectedPriority, selectedHazard]);

  // Client-side text filter on top of backend filters
  const filteredReports = reports.filter((item) => {
    if (!searchQuery.trim()) return true;
    const query = searchQuery.toLowerCase();
    return (
      item.report_id.toLowerCase().includes(query) ||
      (item.activity && item.activity.toLowerCase().includes(query)) ||
      (item.hazard && item.hazard.toLowerCase().includes(query)) ||
      (item.report_text && item.report_text.toLowerCase().includes(query)) ||
      (item.location && item.location.toLowerCase().includes(query))
    );
  });

  const formatDate = (isoStr) => {
    if (!isoStr) return '—';
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return isoStr;
    }
  };

  return (
    <div className="reports-page">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h2>Safety Observation & Incident Reports</h2>
          <p>Complete repository of ingested reports with AI precursor classification and barrier status</p>
        </div>
        <button className="btn btn-outline" onClick={loadReports} title="Reload records">
          <RefreshCw size={14} /> Refresh Records
        </button>
      </div>

      {/* Filter & Search Controls */}
      <div className="filter-bar">
        <div className="search-input-wrapper">
          <Search size={16} className="search-icon" />
          <input
            id="reports-search-input"
            type="text"
            className="search-input"
            placeholder="Search report ID, narrative, activity, hazard, or zone..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="filter-selects">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Filter size={15} color="#64748b" />
            <select
              id="priority-filter-select"
              className="filter-select"
              value={selectedPriority}
              onChange={(e) => setSelectedPriority(e.target.value)}
            >
              <option value="">All Priorities</option>
              <option value="HIGH">HIGH Priority</option>
              <option value="MEDIUM">MEDIUM Priority</option>
              <option value="LOW">LOW Priority</option>
            </select>
          </div>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div style={{ 
          backgroundColor: '#fef2f2', 
          color: '#991b1b', 
          border: '1px solid #fecaca', 
          padding: '0.85rem', 
          borderRadius: '6px', 
          marginBottom: '1rem',
          fontSize: '0.85rem' 
        }}>
          <strong>API Notice:</strong> {error}
        </div>
      )}

      {/* Reports Table */}
      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th style={{ width: '130px' }}>Report ID</th>
              <th>Activity</th>
              <th>Hazard</th>
              <th style={{ width: '120px' }}>Priority</th>
              <th style={{ width: '130px' }}>Date</th>
              <th style={{ width: '150px' }}>Status</th>
              <th style={{ width: '80px', textAlign: 'center' }}>Details</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '3rem 1rem', color: '#64748b' }}>
                  <RefreshCw size={22} className="spin" style={{ margin: '0 auto 0.5rem auto' }} />
                  <div>Loading safety reports from database...</div>
                </td>
              </tr>
            ) : filteredReports.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '3rem 1rem', color: '#64748b' }}>
                  No reports matched your search or filter criteria.
                </td>
              </tr>
            ) : (
              filteredReports.map((report) => (
                <tr 
                  key={report.report_id} 
                  id={`row-${report.report_id}`}
                  onClick={() => onSelectReport(report.report_id)}
                >
                  {/* Report ID */}
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
                      <span className="mono-id">{report.report_id}</span>
                      {report.report_id && report.report_id.startsWith('DEMO-SYN-') && (
                        <span 
                          style={{
                            fontSize: '0.65rem',
                            fontWeight: 700,
                            padding: '0.1rem 0.35rem',
                            borderRadius: '3px',
                            backgroundColor: '#e0e7ff',
                            color: '#3730a3',
                            border: '1px solid #c7d2fe',
                            letterSpacing: '0.02em',
                          }}
                          title="Synthetic Controlled Demo Record"
                        >
                          DEMO
                        </span>
                      )}
                    </div>
                  </td>

                  {/* Activity */}
                  <td style={{ fontWeight: 500 }}>
                    {report.activity || (
                      <span style={{ color: '#94a3b8' }}>Unspecified</span>
                    )}
                  </td>

                  {/* Hazard */}
                  <td>
                    {report.hazard ? (
                      <span style={{ color: '#0f172a' }}>{report.hazard}</span>
                    ) : (
                      <span style={{ color: '#94a3b8' }}>Unspecified</span>
                    )}
                  </td>

                  {/* Priority */}
                  <td>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                      <span className={`badge-priority ${report.priority}`}>
                        {report.priority}
                      </span>
                      {report.hse_reviewed && report.final_priority && report.final_priority !== report.priority && (
                        <span style={{ fontSize: '0.7rem', color: '#64748b' }}>
                          HSE: <strong>{report.final_priority}</strong>
                        </span>
                      )}
                    </div>
                  </td>

                  {/* Date */}
                  <td style={{ color: '#475569', fontSize: '0.8rem' }}>
                    {formatDate(report.created_at)}
                  </td>

                  {/* Status */}
                  <td>
                    {report.hse_reviewed ? (
                      <span className={`badge-priority badge-status-${report.review_decision}`}>
                        <CheckCircle2 size={12} style={{ marginRight: '3px' }} />
                        {report.review_decision}
                      </span>
                    ) : (
                      <span className="badge-priority badge-status-pending">
                        <Clock size={12} style={{ marginRight: '3px' }} />
                        Pending
                      </span>
                    )}
                  </td>

                  {/* Action / Inspect icon */}
                  <td style={{ textAlign: 'center' }}>
                    <button 
                      className="btn btn-outline" 
                      style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectReport(report.report_id);
                      }}
                      title="Inspect full decision evidence"
                    >
                      View
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination & Count summary */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        marginTop: '0.75rem', 
        fontSize: '0.8rem', 
        color: '#64748b' 
      }}>
        <div>
          Showing <strong>{filteredReports.length}</strong> of <strong>{totalCount}</strong> reports in repository
        </div>
        {filteredReports.length > 0 && (
          <div>
            Click any row to open comprehensive HSE decision analysis
          </div>
        )}
      </div>
    </div>
  );
}
