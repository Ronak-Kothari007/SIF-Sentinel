/**
 * SIF Sentinel — Page Transition Wrapper
 * ========================================
 * Wraps page content with smooth Framer Motion enter/exit animations.
 * 
 * Usage:
 *   <PageTransition key={tabName}>
 *     <DashboardPage />
 *   </PageTransition>
 */

import React from 'react';
import { motion } from 'framer-motion';

const pageVariants = {
  initial: {
    opacity: 0,
    y: 8,
  },
  animate: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.3,
      ease: [0.16, 1, 0.3, 1],
    },
  },
  exit: {
    opacity: 0,
    y: -4,
    transition: {
      duration: 0.15,
      ease: [0.6, 0.04, 0.98, 0.34],
    },
  },
};

export default function PageTransition({ children, className = '' }) {
  return (
    <motion.div
      className={className}
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
    >
      {children}
    </motion.div>
  );
}
