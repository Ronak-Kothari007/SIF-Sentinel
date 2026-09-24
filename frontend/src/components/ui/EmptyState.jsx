/**
 * SIF Sentinel — Empty State Component
 * ======================================
 * Professional empty state with icon, title, description, and optional action.
 * Used when a list/section has zero items to display.
 */

import React from 'react';
import { motion } from 'framer-motion';
import { Inbox } from 'lucide-react';

export default function EmptyState({
  icon: Icon = Inbox,
  title = 'No data available',
  description = 'There is nothing to display at the moment.',
  action = null,
  actionLabel = null,
  onAction = null,
  iconSize = 40,
  iconColor,
  className = '',
}) {
  return (
    <motion.div
      className={`empty-state ${className}`}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
    >
      <div
        style={{
          width: '72px',
          height: '72px',
          borderRadius: '16px',
          background: 'var(--slate-100)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto',
        }}
      >
        <Icon size={iconSize} color={iconColor || 'var(--slate-400)'} strokeWidth={1.5} />
      </div>
      <h3>{title}</h3>
      <p>{description}</p>
      {(action || (actionLabel && onAction)) && (
        <div style={{ marginTop: 'var(--space-5)' }}>
          {action || (
            <button className="btn btn-outline" onClick={onAction}>
              {actionLabel}
            </button>
          )}
        </div>
      )}
    </motion.div>
  );
}
