/**
 * SIF Sentinel — Animated Number Counter
 * ========================================
 * Smoothly counts up from 0 to a target value using Framer Motion.
 * Used for KPI tiles and dashboard metrics.
 * 
 * Usage:
 *   <AnimatedNumber value={42} duration={1.2} />
 */

import React from 'react';
import { motion, useMotionValue, useTransform, animate } from 'framer-motion';
import { useEffect, useState, useRef } from 'react';

export default function AnimatedNumber({
  value,
  duration = 1.0,
  decimals = 0,
  prefix = '',
  suffix = '',
  className = '',
}) {
  const [display, setDisplay] = useState('0');
  const prevValue = useRef(0);

  useEffect(() => {
    const target = typeof value === 'number' ? value : parseFloat(value) || 0;
    const from = prevValue.current;

    const controls = animate(from, target, {
      duration: duration,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (latest) => {
        if (decimals > 0) {
          setDisplay(latest.toFixed(decimals));
        } else {
          setDisplay(Math.round(latest).toLocaleString());
        }
      },
    });

    prevValue.current = target;
    return () => controls.stop();
  }, [value, duration, decimals]);

  return (
    <span className={className}>
      {prefix}{display}{suffix}
    </span>
  );
}
