/**
 * SIF Sentinel — Badge Components
 * =================================
 * Unified badge system for priorities, statuses, and labels.
 */

import React from 'react';

/**
 * Priority badge: HIGH | MEDIUM | LOW
 */
export function PriorityBadge({ priority, size = 'default' }) {
  const p = (priority || '').toUpperCase();
  const sizeClass = size === 'sm' ? 'badge-sm' : '';
  return (
    <span className={`badge-priority ${p} ${sizeClass}`}>
      {p === 'HIGH' && '●'} {p}
    </span>
  );
}

/**
 * Review status badge: confirmed | rejected | corrected | pending
 */
export function StatusBadge({ status, label }) {
  const s = (status || 'pending').toLowerCase();
  const displayLabel = label || s.charAt(0).toUpperCase() + s.slice(1);

  const classMap = {
    confirmed: 'badge-status-confirmed',
    rejected: 'badge-status-rejected',
    corrected: 'badge-status-corrected',
    pending: 'badge-status-pending',
  };

  return (
    <span className={`badge-neutral ${classMap[s] || ''}`}>
      {displayLabel}
    </span>
  );
}

/**
 * Neutral info badge for tags, categories, counts.
 */
export function InfoBadge({ children, className = '' }) {
  return (
    <span className={`badge-neutral ${className}`}>
      {children}
    </span>
  );
}

/**
 * Severity badge for rule engine results.
 */
export function SeverityBadge({ severity, label }) {
  const severityColors = {
    4: { bg: '#fef2f2', color: '#991b1b', border: '#fecaca', text: 'CRITICAL' },
    3: { bg: '#fef2f2', color: '#991b1b', border: '#fecaca', text: 'HIGH' },
    2: { bg: '#fffbeb', color: '#92400e', border: '#fde68a', text: 'MEDIUM' },
    1: { bg: '#f0fdf4', color: '#166534', border: '#bbf7d0', text: 'LOW' },
  };

  const s = severityColors[severity] || severityColors[1];

  return (
    <span
      className="badge-priority"
      style={{
        backgroundColor: s.bg,
        color: s.color,
        borderColor: s.border,
        border: `1px solid ${s.border}`,
      }}
    >
      {label || s.text}
    </span>
  );
}
