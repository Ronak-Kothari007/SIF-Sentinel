import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  BarChart2,
  TrendingUp,
  Shield,
  AlertTriangle,
  CheckCircle,
  Activity,
  Layers,
  PieChart,
  RefreshCw,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  PieChart as RechartsPie,
  Pie,
  Cell,
} from 'recharts';
import { fetchDashboardSummary, fetchPatterns } from '../services/api';
import { Skeleton, EmptyState, ErrorState } from '../components/ui';

const COLORS = {
  HIGH: '#dc2626',
  MEDIUM: '#d97706',
  LOW: '#16a34a',
  UNREVIEWED: '#94a3b8',
  confirmed: '#16a34a',
  corrected: '#6366f1',
  rejected: '#dc2626',
  pending: '#94a3b8',
};

const PIE_COLORS = ['#dc2626', '#d97706', '#16a34a', '#94a3b8'];

export default function AnalyticsPage() {
  const [summary, setSummary] = useState(null);
  const [patterns, setPatterns] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sumRes, patRes] = await Promise.all([
        fetchDashboardSummary(),
        fetchPatterns().catch(() => null),
      ]);
      setSummary(sumRes);
      setPatterns(patRes);
    } catch (err) {
      setError(err.message || 'Failed to load analytics data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  if (loading) {
    return (
      <div className="page-container">
        <div className="page-header">
          <div className="page-title"><h1>Analytics</h1></div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1.5rem', marginBottom: '2rem' }}>
          {[1,2,3,4].map(i => <Skeleton key={i} height="120px" borderRadius="12px" />)}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
          {[1,2,3,4].map(i => <Skeleton key={i} height="320px" borderRadius="12px" />)}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <ErrorState message={error} onRetry={loadData} />
      </div>
    );
  }

  if (!summary || summary.total_reports === 0) {
    return (
      <div className="page-container">
        <div className="page-header">
          <div className="page-title"><h1>Analytics</h1><p>Cross-functional safety intelligence overview.</p></div>
        </div>
        <EmptyState
          icon={BarChart2}
          title="No Data Available"
          description="Analytics will populate once safety reports are analyzed through the system."
        />
      </div>
    );
  }

  // Prepare chart data
  const priorityDistData = [
    { name: 'High', value: summary.ai_distribution?.HIGH || 0, color: COLORS.HIGH },
    { name: 'Medium', value: summary.ai_distribution?.MEDIUM || 0, color: COLORS.MEDIUM },
    { name: 'Low', value: summary.ai_distribution?.LOW || 0, color: COLORS.LOW },
  ];

  const reviewStatusData = [
    { name: 'Confirmed', value: summary.review_status?.confirmed || 0, color: COLORS.confirmed },
    { name: 'Corrected', value: summary.review_status?.corrected || 0, color: COLORS.corrected },
    { name: 'Rejected', value: summary.review_status?.rejected || 0, color: COLORS.rejected },
    { name: 'Pending', value: summary.review_status?.pending || 0, color: COLORS.pending },
  ].filter(d => d.value > 0);

  const aiVsHseData = [
    { priority: 'HIGH', 'AI Triage': summary.ai_distribution?.HIGH || 0, 'HSE Final': summary.hse_distribution?.HIGH || 0 },
    { priority: 'MEDIUM', 'AI Triage': summary.ai_distribution?.MEDIUM || 0, 'HSE Final': summary.hse_distribution?.MEDIUM || 0 },
    { priority: 'LOW', 'AI Triage': summary.ai_distribution?.LOW || 0, 'HSE Final': summary.hse_distribution?.LOW || 0 },
  ];

  const topHazards = (patterns?.top_hazards || summary.top_hazards || []).slice(0, 6);
  const topActivities = (patterns?.top_activities || summary.top_activities || []).slice(0, 6);
  const topBarrierGaps = (patterns?.top_barrier_gaps || summary.top_barrier_failures || []).slice(0, 6);

  const agreementRate = summary.agreement_rate || 0;
  const totalReviewed = summary.review_status?.total_reviewed || 0;
  const sifRate = summary.sif_precursor_rate || 0;

  return (
    <div className="page-container">
      <div className="page-header" style={{ marginBottom: '2rem' }}>
        <div className="page-title">
          <h1>Analytics</h1>
          <p>Cross-functional safety intelligence derived from {summary.total_reports} analyzed observations.</p>
        </div>
        <button className="btn btn-outline" onClick={loadData}>
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* KPI ROW */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.25rem', marginBottom: '2rem' }}>
        <KPICard icon={<Activity size={20} />} label="Total Reports" value={summary.total_reports} color="var(--accent-blue)" />
        <KPICard icon={<AlertTriangle size={20} />} label="High Priority" value={summary.high_priority_count} color="var(--sif-high)" />
        <KPICard icon={<CheckCircle size={20} />} label="HSE Reviews" value={totalReviewed} color="var(--sif-low)" />
        <KPICard icon={<Shield size={20} />} label="AI–HSE Agreement" value={`${agreementRate}%`} color="var(--accent-blue)" />
        <KPICard icon={<TrendingUp size={20} />} label="SIF Precursor Rate" value={`${sifRate}%`} color="var(--sif-medium)" />
      </div>

      {/* CHARTS ROW 1 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>
        
        {/* AI Priority Distribution */}
        <div className="panel">
          <div className="panel-header">
            <div className="panel-title"><PieChart size={18} color="var(--accent-blue)" /><h3>AI Priority Distribution</h3></div>
          </div>
          <div className="panel-content" style={{ height: '300px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <RechartsPie>
                <Pie
                  data={priorityDistData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={4}
                  dataKey="value"
                  label={({ name, value }) => `${name}: ${value}`}
                >
                  {priorityDistData.map((entry, idx) => (
                    <Cell key={idx} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </RechartsPie>
            </ResponsiveContainer>
          </div>
        </div>

        {/* AI vs HSE Comparison */}
        <div className="panel">
          <div className="panel-header">
            <div className="panel-title"><BarChart2 size={18} color="#6366f1" /><h3>AI Triage vs HSE Final</h3></div>
          </div>
          <div className="panel-content" style={{ height: '300px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={aiVsHseData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="priority" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
                <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: 'var(--shadow-md)' }} />
                <Legend />
                <Bar dataKey="AI Triage" fill="#6366f1" radius={[4, 4, 0, 0]} />
                <Bar dataKey="HSE Final" fill="#16a34a" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* CHARTS ROW 2 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>

        {/* Review Outcomes */}
        <div className="panel">
          <div className="panel-header">
            <div className="panel-title"><CheckCircle size={18} color="var(--sif-low)" /><h3>HSE Review Outcomes</h3></div>
          </div>
          <div className="panel-content" style={{ height: '300px' }}>
            {reviewStatusData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <RechartsPie>
                  <Pie
                    data={reviewStatusData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={4}
                    dataKey="value"
                    label={({ name, value }) => `${name}: ${value}`}
                  >
                    {reviewStatusData.map((entry, idx) => (
                      <Cell key={idx} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </RechartsPie>
              </ResponsiveContainer>
            ) : (
              <EmptyState icon={CheckCircle} title="No Reviews Yet" description="HSE review outcomes will appear here." />
            )}
          </div>
        </div>

        {/* Top Hazards */}
        <div className="panel">
          <div className="panel-header">
            <div className="panel-title"><AlertTriangle size={18} color="var(--sif-high)" /><h3>Top Hazards</h3></div>
          </div>
          <div className="panel-content" style={{ height: '300px' }}>
            {topHazards.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={topHazards} layout="vertical" margin={{ top: 5, right: 30, left: 80, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
                  <XAxis type="number" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
                  <YAxis type="category" dataKey="hazard" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#334155' }} width={75} />
                  <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: 'var(--shadow-md)' }} />
                  <Bar dataKey="count" fill="#dc2626" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState icon={AlertTriangle} title="No Hazard Data" />
            )}
          </div>
        </div>
      </div>

      {/* ROW 3: Activities + Barrier Gaps */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>
        
        {/* Top Activities */}
        <div className="panel">
          <div className="panel-header">
            <div className="panel-title"><Activity size={18} color="var(--sif-medium)" /><h3>Top Activities</h3></div>
          </div>
          <div className="panel-content" style={{ height: '300px' }}>
            {topActivities.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={topActivities} layout="vertical" margin={{ top: 5, right: 30, left: 80, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
                  <XAxis type="number" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
                  <YAxis type="category" dataKey="activity" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#334155' }} width={75} />
                  <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: 'var(--shadow-md)' }} />
                  <Bar dataKey="count" fill="#d97706" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState icon={Activity} title="No Activity Data" />
            )}
          </div>
        </div>

        {/* Barrier Failures */}
        <div className="panel">
          <div className="panel-header">
            <div className="panel-title"><Layers size={18} color="#6366f1" /><h3>Critical Barrier Gaps</h3></div>
          </div>
          <div className="panel-content">
            {topBarrierGaps.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {topBarrierGaps.map((gap, idx) => (
                  <div key={idx} style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '0.75rem 1rem', background: 'var(--slate-50)', borderRadius: '8px',
                    borderLeft: '3px solid #6366f1'
                  }}>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--slate-800)' }}>
                        {gap.barrier}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--slate-500)' }}>
                        Status: {gap.barrier_status}
                      </div>
                    </div>
                    <span style={{
                      fontWeight: 700, fontSize: '1.1rem', color: '#6366f1',
                      background: '#6366f120', padding: '0.25rem 0.75rem', borderRadius: '20px'
                    }}>
                      {gap.count}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState icon={Layers} title="No Barrier Data" />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function KPICard({ icon, label, value, color }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="panel"
      style={{ padding: '1.25rem', display: 'flex', alignItems: 'center', gap: '1rem' }}
    >
      <div style={{
        width: '44px', height: '44px', borderRadius: '12px',
        background: `${color}15`, display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: color, flexShrink: 0,
      }}>
        {icon}
      </div>
      <div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.04em' }}>
          {label}
        </div>
        <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1.2 }}>
          {value}
        </div>
      </div>
    </motion.div>
  );
}
