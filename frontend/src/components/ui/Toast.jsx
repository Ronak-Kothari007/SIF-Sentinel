/**
 * SIF Sentinel — Toast Notification System
 * ==========================================
 * Manages a stack of timed notifications with entrance/exit animations.
 * 
 * Usage:
 *   import { ToastProvider, useToast } from './ui/Toast';
 *   
 *   // Wrap your app:
 *   <ToastProvider><App /></ToastProvider>
 *   
 *   // In any component:
 *   const toast = useToast();
 *   toast.success('Report analyzed successfully');
 *   toast.error('Failed to submit review');
 *   toast.info('Demo data loaded');
 *   toast.warning('Connection unstable');
 */

import React, { createContext, useContext, useState, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, AlertTriangle, Info, XCircle, X } from 'lucide-react';

const ToastContext = createContext(null);

const TOAST_ICONS = {
  success: CheckCircle2,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
};

const TOAST_COLORS = {
  success: '#22c55e',
  error: '#ef4444',
  warning: '#f59e0b',
  info: '#3b82f6',
};

const TOAST_DURATION = 4500;

let toastId = 0;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const timers = useRef({});

  const removeToast = useCallback((id) => {
    clearTimeout(timers.current[id]);
    delete timers.current[id];
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback((message, type = 'info', duration = TOAST_DURATION) => {
    const id = ++toastId;
    setToasts((prev) => [...prev.slice(-4), { id, message, type }]); // Keep max 5

    timers.current[id] = setTimeout(() => {
      removeToast(id);
    }, duration);

    return id;
  }, [removeToast]);

  const toast = {
    success: (msg, duration) => addToast(msg, 'success', duration),
    error: (msg, duration) => addToast(msg, 'error', duration),
    warning: (msg, duration) => addToast(msg, 'warning', duration),
    info: (msg, duration) => addToast(msg, 'info', duration),
    dismiss: removeToast,
  };

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div className="toast-container" role="status" aria-live="polite">
        <AnimatePresence mode="popLayout">
          {toasts.map((t) => {
            const Icon = TOAST_ICONS[t.type] || Info;
            return (
              <motion.div
                key={t.id}
                className={`toast toast-${t.type}`}
                layout
                initial={{ opacity: 0, y: 16, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 8, scale: 0.95 }}
                transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
              >
                <Icon size={16} color={TOAST_COLORS[t.type]} style={{ flexShrink: 0 }} />
                <span style={{ flex: 1 }}>{t.message}</span>
                <button
                  onClick={() => removeToast(t.id)}
                  style={{
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    padding: '2px',
                    color: 'var(--slate-400)',
                    flexShrink: 0,
                    display: 'flex',
                    alignItems: 'center',
                  }}
                  aria-label="Dismiss notification"
                >
                  <X size={14} />
                </button>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    // Fallback for components not wrapped in ToastProvider
    return {
      success: (msg) => console.log('[Toast]', msg),
      error: (msg) => console.error('[Toast]', msg),
      warning: (msg) => console.warn('[Toast]', msg),
      info: (msg) => console.info('[Toast]', msg),
      dismiss: () => {},
    };
  }
  return ctx;
}
