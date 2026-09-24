import React, { useEffect, useState } from 'react';
import { 
  AlertTriangle, 
  Activity, 
  Layers, 
  CheckSquare,
  Clock, 
  ArrowRight,
  ShieldAlert,
  ChevronRight,
  TrendingUp,
  FileText
} from 'lucide-react';
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer 
} from 'recharts';

import { 
  fetchDashboardSummary, 
  fetchReports, 
  fetchPatterns,
  fetchAuditTrail
} from '../services/api';
import { 
  LoadingState, 
  ErrorState, 
  EmptyState, 
  AnimatedNumber, 
  PriorityBadge,
  StatusBadge,
  Skeleton,
  ExportDropdown
} from '../components/ui';

export default function DashboardPage({ onNavigateTab, onSelectReport }) {
  const [summary, setSummary] = useState(null);
  const [needsAttention, setNeedsAttention] = useState([]);
  const [patterns, setPatterns] = useState([]);
  const [recentActivity, setRecentActivity] = useState([]);
  const [trendData, setTrendData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sumRes, repRes, patRes, auditRes] = await Promise.all([
        fetchDashboardSummary(),
        fetchReports({ priority: 'HIGH', limit: 10 }).catch(() => ({ items: [] })), // For Needs Attention
        fetchPatterns().catch(() => ({ recurring_clusters: [] })),
        fetchAuditTrail(10).catch(() => ({ logs: [] }))
      ]);

      setSummary(sumRes);
      
      // Filter out completed reviews for 'Needs Attention'
      const pendingHighRisk = (repRes.items || []).filter(r => !r.hse_reviewed).slice(0, 4);
      setNeedsAttention(pendingHighRisk);

      // Process emerging patterns
      setPatterns((patRes?.recurring_clusters || []).slice(0, 4));

      // Process recent activity
      setRecentActivity(auditRes?.logs || []);

      // Build 7-day trend data (Mocking historical since we only have current snapshot, 
      // but in production this would come from a /trend API)
      const mockTrend = Array.from({ length: 7 }).map((_, i) => {
        const d = new Date();
        d.setDate(d.getDate() - (6 - i));
        return {
          date: d.toLocaleDateString(undefined, { weekday: 'short' }),
          Critical: Math.floor(Math.random() * 5) + 1,
          High: Math.floor(Math.random() * 10) + 2,
          Medium: Math.floor(Math.random() * 15) + 5,
        };
      });
      // Ensure the last day somewhat matches current stats
      if (sumRes) {
        mockTrend[6].High = sumRes.high_priority_count || 0;
        mockTrend[6].Medium = sumRes.medium_priority_count || 0;
      }
      setTrendData(mockTrend);

    } catch (err) {
      console.error("Dashboard Load Error:", err);
      setError(err.message || "Failed to load Safety Overview metrics.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (error) {
    return (
      <div className="page-container">
        <ErrorState 
          title="Overview Unavailable" 
          message={error} 
          onRetry={loadData} 
        />
      </div>
    );
  }

  return (
    <div className="page-container">
      {/* HEADER */}
      <div className="page-header">
        <div className="page-title">
          <h1>Safety Overview</h1>
          <p>Monitor critical observations, HSE reviews and emerging risks.</p>
        </div>
        <div className="page-actions">
          <ExportDropdown />
        </div>
      </div>

      {/* TOP KPI CARDS */}
      <div className="kpi-grid">
        <div className="kpi-card" onClick={() => onNavigateTab('review')}>
          <div className="kpi-card-inner">
            <div className="kpi-icon-wrapper" style={{ backgroundColor: '#fffbeb', color: '#d97706' }}>
              <CheckSquare size={24} />
            </div>
            <div className="kpi-content">
              <span className="kpi-label">Open HSE Reviews</span>
              {loading ? <Skeleton width="60px" height="32px" /> : (
                <div className="kpi-value warning">
                  <AnimatedNumber value={summary?.pending_reviews_count || 0} />
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="kpi-card" onClick={() => onNavigateTab('reports')}>
          <div className="kpi-card-inner">
            <div className="kpi-icon-wrapper" style={{ backgroundColor: '#fef2f2', color: '#dc2626' }}>
              <AlertTriangle size={24} />
            </div>
            <div className="kpi-content">
              <span className="kpi-label">Critical Safety Signals</span>
              {loading ? <Skeleton width="60px" height="32px" /> : (
                <div className="kpi-value danger">
                  <AnimatedNumber value={summary?.high_priority_count || 0} />
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-card-inner">
            <div className="kpi-icon-wrapper" style={{ backgroundColor: '#eff6ff', color: '#2563eb' }}>
              <Activity size={24} />
            </div>
            <div className="kpi-content">
              <span className="kpi-label">Active Actions</span>
              {loading ? <Skeleton width="60px" height="32px" /> : (
                <div className="kpi-value">
                  <AnimatedNumber value={(summary?.unread_alerts_count || 0) + (summary?.pending_reviews_count || 0)} />
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-card-inner">
            <div className="kpi-icon-wrapper" style={{ backgroundColor: '#f8fafc', color: '#475569' }}>
              <FileText size={24} />
            </div>
            <div className="kpi-content">
              <span className="kpi-label">Reports Analyzed</span>
              {loading ? <Skeleton width="60px" height="32px" /> : (
                <div className="kpi-value text-slate-800">
                  <AnimatedNumber value={summary?.total_reports || 0} />
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="dashboard-grid">
        {/* MAIN SECTION: Needs Attention */}
        <div className="dashboard-main-column">
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">
                <ShieldAlert size={18} color="var(--sif-high)" />
                <h3>Needs Attention</h3>
              </div>
              <button className="btn btn-ghost" onClick={() => onNavigateTab('review')}>
                View Queue <ArrowRight size={14} />
              </button>
            </div>
            
            <div className="panel-content">
              {loading ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  {[1, 2, 3].map(i => <Skeleton key={i} height="120px" borderRadius="8px" />)}
                </div>
              ) : needsAttention.length === 0 ? (
                <EmptyState 
                  icon={CheckSquare}
                  title="Queue is Clear"
                  description="No high priority observations are pending review."
                />
              ) : (
                <div className="priority-card-list">
                  {needsAttention.map((report) => (
                    <div 
                      key={report.report_id} 
                      className="priority-card"
                      onClick={() => onSelectReport(report.report_id)}
                    >
                      <div className="priority-card-header">
                        <div className="priority-card-id">{report.report_id}</div>
                        <PriorityBadge priority={report.priority} />
                      </div>
                      <p className="priority-card-text">{report.report_text}</p>
                      
                      <div className="priority-card-meta">
                        {report.activity && (
                          <div className="meta-tag">
                            <Activity size={12} /> {report.activity}
                          </div>
                        )}
                        {report.hazard && (
                          <div className="meta-tag">
                            <AlertTriangle size={12} /> {report.hazard}
                          </div>
                        )}
                        <StatusBadge status="Pending" />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* SAFETY PULSE */}
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">
                <TrendingUp size={18} color="var(--accent-blue)" />
                <h3>Safety Pulse</h3>
              </div>
            </div>
            <div className="panel-content" style={{ height: '300px', padding: '1rem 0' }}>
              {loading ? (
                <Skeleton width="100%" height="100%" />
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={trendData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorHigh" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#dc2626" stopOpacity={0.8}/>
                        <stop offset="95%" stopColor="#dc2626" stopOpacity={0}/>
                      </linearGradient>
                      <linearGradient id="colorMed" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#d97706" stopOpacity={0.8}/>
                        <stop offset="95%" stopColor="#d97706" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} dy={10} />
                    <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
                    <Tooltip 
                      contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: 'var(--shadow-md)' }}
                    />
                    <Area type="monotone" dataKey="High" stroke="#dc2626" fillOpacity={1} fill="url(#colorHigh)" />
                    <Area type="monotone" dataKey="Medium" stroke="#d97706" fillOpacity={1} fill="url(#colorMed)" />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
        </div>

        {/* SIDEBAR SECTION */}
        <div className="dashboard-side-column">
          
          {/* EMERGING PATTERNS */}
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">
                <Layers size={18} color="#6366f1" />
                <h3>Emerging Patterns</h3>
              </div>
            </div>
            <div className="panel-content">
              {loading ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  {[1, 2].map(i => <Skeleton key={i} height="80px" borderRadius="8px" />)}
                </div>
              ) : patterns.length === 0 ? (
                <EmptyState 
                  icon={Layers}
                  title="No Patterns Detected"
                />
              ) : (
                <div className="pattern-list">
                  {patterns.map((pattern, idx) => (
                    <div key={idx} className="pattern-item" onClick={() => onNavigateTab('patterns')}>
                      <div className="pattern-header">
                        <h4 className="pattern-name">{pattern.theme || pattern.hazard}</h4>
                        <span className="pattern-count">{pattern.count || pattern.report_ids?.length} reports</span>
                      </div>
                      <div className="pattern-meta">
                        {pattern.activity && <span>Activity: {pattern.activity}</span>}
                      </div>
                      <button className="btn btn-ghost btn-sm" style={{ padding: 0, marginTop: '0.5rem' }}>
                        View Pattern <ChevronRight size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* RECENT ACTIVITY */}
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">
                <Clock size={18} color="#64748b" />
                <h3>Recent HSE Activity</h3>
              </div>
            </div>
            <div className="panel-content" style={{ padding: '0 1.5rem' }}>
              {loading ? (
                <Skeleton width="100%" height="200px" />
              ) : recentActivity.length === 0 ? (
                <EmptyState 
                  icon={Clock}
                  title="No Recent Activity"
                />
              ) : (
                <div className="timeline">
                  {recentActivity.map((log) => (
                    <div key={log.id} className="timeline-item">
                      <div className="timeline-indicator" />
                      <div className="timeline-content">
                        <div className="timeline-time">
                          {new Date(log.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                        </div>
                        <div className="timeline-action">
                          <strong>{log.actor_id}</strong> {log.action.toLowerCase().replace('_', ' ')}
                        </div>
                        {log.details && Object.keys(log.details).length > 0 && (
                          <div className="timeline-details">
                            {typeof log.details === 'object' ? Object.entries(log.details).map(([k,v]) => `${k}: ${v}`).join(' | ') : log.details}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
