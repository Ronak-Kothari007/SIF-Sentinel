/**
 * SIF Sentinel — Loading State Component
 * ========================================
 * Professional loading indicator with animated dots.
 */

import React from 'react';
import { motion } from 'framer-motion';

export default function LoadingState({
  message = 'Loading...',
  className = '',
  variant = 'dots', // 'dots' | 'spinner'
}) {
  return (
    <motion.div
      className={`loading-state ${className}`}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.25 }}
    >
      {variant === 'dots' ? (
        <div className="spinner-dots">
          <div className="spinner-dot" />
          <div className="spinner-dot" />
          <div className="spinner-dot" />
        </div>
      ) : (
        <motion.div
          style={{
            width: 28,
            height: 28,
            border: '3px solid var(--slate-200)',
            borderTopColor: 'var(--accent-blue)',
            borderRadius: '50%',
          }}
          animate={{ rotate: 360 }}
          transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }}
        />
      )}
      <p>{message}</p>
    </motion.div>
  );
}
