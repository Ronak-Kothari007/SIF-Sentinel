/**
 * SIF Sentinel — Skeleton Loading Components
 * ============================================
 * Professional shimmer-animated placeholder components for loading states.
 * Uses CSS classes from the design system (index.css).
 */

import React from 'react';

/**
 * Generic skeleton block with configurable dimensions.
 */
export function Skeleton({ width, height, borderRadius, className = '', style = {} }) {
  return (
    <div
      className={`skeleton ${className}`}
      style={{
        width: width || '100%',
        height: height || '14px',
        borderRadius: borderRadius || undefined,
        ...style,
      }}
    />
  );
}

/**
 * Skeleton text line — mimics a line of text.
 */
export function SkeletonText({ width, size = 'md', className = '' }) {
  const sizeClass = size === 'lg' ? 'lg' : size === 'sm' ? 'sm' : '';
  return (
    <div
      className={`skeleton skeleton-text ${sizeClass} ${className}`}
      style={{ width: width || undefined }}
    />
  );
}

/**
 * Skeleton KPI card — placeholder for a metric tile.
 */
export function SkeletonKPICard() {
  return (
    <div className="kpi-card" style={{ minHeight: '120px' }}>
      <div className="kpi-card-header">
        <Skeleton width="80px" height="10px" />
        <Skeleton width="36px" height="36px" borderRadius="8px" />
      </div>
      <Skeleton width="60px" height="28px" style={{ marginTop: '8px' }} />
      <Skeleton width="120px" height="10px" style={{ marginTop: '12px' }} />
    </div>
  );
}

/**
 * Skeleton row for data tables.
 */
export function SkeletonTableRow({ columns = 5 }) {
  return (
    <tr>
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i}>
          <Skeleton
            width={i === 0 ? '80px' : i === columns - 1 ? '60px' : `${50 + Math.random() * 50}%`}
            height="13px"
          />
        </td>
      ))}
    </tr>
  );
}

/**
 * Skeleton card panel — placeholder for a section panel.
 */
export function SkeletonPanel({ lines = 4 }) {
  return (
    <div className="card-panel">
      <div className="card-panel-header">
        <Skeleton width="140px" height="16px" />
        <Skeleton width="80px" height="12px" />
      </div>
      <div className="card-panel-body">
        {Array.from({ length: lines }).map((_, i) => (
          <SkeletonText
            key={i}
            width={`${60 + Math.random() * 35}%`}
            size={i === 0 ? 'lg' : 'md'}
          />
        ))}
      </div>
    </div>
  );
}

/**
 * Skeleton grid of KPI cards.
 */
export function SkeletonKPIGrid({ count = 4 }) {
  return (
    <div className="kpi-grid">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonKPICard key={i} />
      ))}
    </div>
  );
}

/**
 * Full-page skeleton for dashboard loading.
 */
export function SkeletonDashboard() {
  return (
    <div>
      <div className="page-header" style={{ marginBottom: '24px' }}>
        <div>
          <Skeleton width="200px" height="24px" />
          <Skeleton width="300px" height="13px" style={{ marginTop: '8px' }} />
        </div>
      </div>
      <SkeletonKPIGrid count={4} />
      <div className="grid-2col">
        <SkeletonPanel lines={5} />
        <SkeletonPanel lines={4} />
      </div>
    </div>
  );
}
