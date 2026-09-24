/**
 * SIF Sentinel — Error State Component
 * ======================================
 * Professional error display with retry action.
 */

import React from 'react';
import { motion } from 'framer-motion';
import { AlertTriangle, RefreshCw } from 'lucide-react';

export default function ErrorState({
  title = 'Something went wrong',
  message = 'An unexpected error occurred. Please try again.',
  onRetry = null,
  retryLabel = 'Retry',
  icon: Icon = AlertTriangle,
  className = '',
}) {
  return (
    <motion.div
      className={`error-state ${className}`}
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
    >
      <div
        style={{
          width: '60px',
          height: '60px',
          borderRadius: '14px',
          background: 'var(--sif-high-bg)',
          border: '1px solid var(--sif-high-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto',
        }}
      >
        <Icon size={28} color="var(--sif-high)" strokeWidth={1.5} />
      </div>
      <h3>{title}</h3>
      <p>{message}</p>
      {onRetry && (
        <button
          className="btn btn-outline"
          onClick={onRetry}
          style={{ marginTop: 'var(--space-5)' }}
        >
          <RefreshCw size={14} />
          {retryLabel}
        </button>
      )}
    </motion.div>
  );
}
