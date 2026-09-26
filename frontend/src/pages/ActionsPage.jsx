import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { fetchActions, updateActionStatus } from '../services/api';
import { 
  CheckCircle, 
  Clock, 
  AlertTriangle, 
  UserPlus, 
  PlayCircle,
  Shield,
  MapPin,
  Calendar,
  XCircle,
  FileText
} from 'lucide-react';
import { formatDistanceToNow, parseISO } from 'date-fns';

const PRIORITY_COLORS = {
  CRITICAL: 'var(--critical)',
  HIGH: 'var(--high)',
  MEDIUM: 'var(--medium)',
  LOW: 'var(--low)',
};

const STATUS_ORDER = ['Open', 'Assigned', 'In Progress', 'Verification', 'Closed'];

export default function ActionsPage({ onSelectReport }) {
  const navigate = useNavigate();
  const [actions, setActions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const [statusFilter, setStatusFilter] = useState('All');

  useEffect(() => {
    loadActions();
  }, [statusFilter]);

  const loadActions = async () => {
    try {
      setLoading(true);
      const res = await fetchActions(statusFilter !== 'All' ? statusFilter : null);
      setActions(res.actions || []);
      setError(null);
    } catch (err) {
      setError('Failed to load Action Center data.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleStatusChange = async (actionId, newStatus, assignedTo = null) => {
    try {
      // Optimistic update
      setActions(prev => prev.map(a => 
        a.id === actionId ? { ...a, status: newStatus, assigned_to: assignedTo || a.assigned_to } : a
      ));
      await updateActionStatus(actionId, newStatus, assignedTo);
    } catch (err) {
      console.error('Failed to update action status:', err);
      loadActions(); // Revert on failure
    }
  };

  return (
    <div className="page-container">
      
      <div className="page-header">
        <div className="page-title">
          <h1>Action Center</h1>
          <p>Track and manage HSE work generated from high-priority precursor signals.</p>
        </div>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '2rem', flexWrap: 'wrap' }}>
        {['All', ...STATUS_ORDER].map(st => (
          <button
            key={st}
            onClick={() => setStatusFilter(st)}
            style={{
              padding: '0.5rem 1rem',
              borderRadius: '20px',
              border: `1px solid ${statusFilter === st ? 'var(--primary)' : 'var(--border)'}`,
              background: statusFilter === st ? 'var(--primary-light)' : 'var(--bg-card)',
              color: statusFilter === st ? 'var(--primary-dark)' : 'var(--text-secondary)',
              cursor: 'pointer',
              fontWeight: 500,
              transition: 'all 0.2s ease',
            }}
          >
            {st}
          </button>
        ))}
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--text-muted)' }}>
          <div className="spinner" style={{ margin: '0 auto 1rem', borderColor: 'var(--primary)', borderRightColor: 'transparent' }} />
          Loading actions...
        </div>
      ) : error ? (
        <div className="alert-banner" style={{ background: '#FEE2E2', color: '#991B1B' }}>
          <AlertTriangle size={20} />
          <span>{error}</span>
          <button onClick={loadActions} style={{ marginLeft: 'auto', background: 'transparent', border: 'none', color: 'inherit', fontWeight: 'bold', cursor: 'pointer' }}>Retry</button>
        </div>
      ) : actions.length === 0 ? (
        <div className="empty-state">
          <Shield size={48} style={{ color: 'var(--border-subtle)', margin: '0 auto 1rem' }} />
          <h3>No trackable actions found.</h3>
          <p>High-priority reports that require immediate action will appear here once verified.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <AnimatePresence>
            {actions.map((action) => (
              <ActionCard 
                key={action.id} 
                action={action} 
                onStatusChange={handleStatusChange} 
                onSelectReport={onSelectReport}
                navigate={navigate}
              />
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}

function ActionCard({ action, onStatusChange, onSelectReport, navigate }) {
  const getStatusColor = (status) => {
    switch(status) {
      case 'Open': return '#9CA3AF';
      case 'Assigned': return '#60A5FA';
      case 'In Progress': return '#F59E0B';
      case 'Verification': return '#8B5CF6';
      case 'Closed': return '#10B981';
      default: return '#9CA3AF';
    }
  };

  const statusColor = getStatusColor(action.status);
  const priorityColor = PRIORITY_COLORS[action.priority] || PRIORITY_COLORS.HIGH;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.3 }}
      className="panel"
      style={{
        padding: '1.5rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '1rem',
        marginBottom: '1rem'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              padding: '0.25rem 0.5rem',
              borderRadius: '4px',
              fontSize: '0.75rem',
              fontWeight: 700,
              background: `${priorityColor}20`,
              color: priorityColor,
            }}>
              {action.priority}
            </span>
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              padding: '0.25rem 0.75rem',
              borderRadius: '20px',
              fontSize: '0.75rem',
              fontWeight: 600,
              background: `${statusColor}20`,
              color: statusColor,
              border: `1px solid ${statusColor}40`
            }}>
              {action.status}
            </span>
          </div>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '0.5rem' }}>
            {action.title}
          </h3>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <FileText size={16} />
              <span>Report ID: {action.report_id}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <MapPin size={16} />
              <span>{action.site_location || 'Location Unknown'}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <Calendar size={16} />
              <span>Created {formatDistanceToNow(parseISO(action.created_at), { addSuffix: true })}</span>
            </div>
          </div>
        </div>
        
        {/* Assignee Badge */}
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '0.5rem',
          background: 'var(--bg-main)',
          padding: '0.5rem 1rem',
          borderRadius: '8px',
          border: '1px solid var(--border)'
        }}>
          <UserPlus size={18} style={{ color: action.assigned_to ? 'var(--primary)' : 'var(--text-muted)' }} />
          <span style={{ fontSize: '0.9rem', fontWeight: 500, color: action.assigned_to ? 'var(--text-main)' : 'var(--text-muted)' }}>
            {action.assigned_to || 'Unassigned'}
          </span>
        </div>
      </div>

      <div style={{ height: '1px', background: 'var(--border)', margin: '0.5rem 0' }} />

      {/* Workflow Actions */}
      <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
        <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginRight: '0.5rem' }}>
          Workflow:
        </span>
        
        {action.status === 'Open' && (
          <WorkflowButton 
            icon={<UserPlus size={16} />} 
            label="Assign" 
            onClick={() => onStatusChange(action.id, 'Assigned', 'HSE-OFFICER-03')} 
          />
        )}
        
        {action.status === 'Assigned' && (
          <WorkflowButton 
            icon={<PlayCircle size={16} />} 
            label="Mark In Progress" 
            onClick={() => onStatusChange(action.id, 'In Progress')} 
            primary
          />
        )}

        {action.status === 'In Progress' && (
          <WorkflowButton 
            icon={<CheckCircle size={16} />} 
            label="Submit for Verification" 
            onClick={() => onStatusChange(action.id, 'Verification')} 
            primary
          />
        )}

        {action.status === 'Verification' && (
          <WorkflowButton 
            icon={<Shield size={16} />} 
            label="Verify & Close" 
            onClick={() => onStatusChange(action.id, 'Closed')} 
            success
          />
        )}
        
        {action.status === 'Closed' && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#10B981', fontWeight: 500, fontSize: '0.9rem' }}>
            <CheckCircle size={18} />
            <span>Action completed and verified</span>
          </div>
        )}

        {action.status !== 'Closed' && (
          <button
            className="btn btn-outline"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              console.log("View Details clicked! Report ID:", action.report_id);
              if (onSelectReport && action.report_id) {
                onSelectReport(action.report_id);
              } else if (navigate && action.report_id) {
                navigate('/reports/details', { state: { reportId: action.report_id } });
              } else {
                console.error("Missing onSelectReport or report_id", { onSelectReport, id: action.report_id });
                alert("Cannot navigate: Missing properties.");
              }
            }}
            style={{ marginLeft: 'auto', position: 'relative', zIndex: 10 }}
          >
            View Details
          </button>
        )}
      </div>
    </motion.div>
  );
}
function WorkflowButton({ icon, label, onClick, primary, success }) {
  return (
    <motion.button
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      className={`btn ${primary ? 'btn-primary' : success ? 'btn-confirm' : 'btn-outline'}`}
    >
      {icon}
      {label}
    </motion.button>
  );
}
