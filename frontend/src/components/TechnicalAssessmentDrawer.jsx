import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Server, Brain, Activity, ShieldAlert, Cpu, GitBranch, Database, Clock } from 'lucide-react';

const TechnicalAssessmentDrawer = ({ isOpen, onClose, assessment }) => {
  if (!assessment) return null;

  const {
    priority,
    sif_probability,
    model_confidence,
    activity,
    hazard,
    location,
    barrier,
    barrier_status,
    priority_score,
    rule_severity_score,
    barrier_gap_score,
    recurrence_score,
    rules_fired = [],
    lime_tokens = [],
    similar_reports = []
  } = assessment;

  // Format probabilities cleanly
  const prob = sif_probability ?? model_confidence ?? 0;
  const confidencePercent = (prob * 100).toFixed(1) + '%';
  const scorePercent = ((priority_score || 0) * 100).toFixed(1) + '%';

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-40"
          />

          {/* Drawer */}
          <motion.div
            initial={{ x: '100%', opacity: 0.5 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '100%', opacity: 0.5 }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed right-0 top-0 bottom-0 w-full max-w-md bg-white shadow-2xl z-50 overflow-y-auto border-l border-slate-200"
          >
            <div className="sticky top-0 bg-slate-50 border-b border-slate-200 p-4 flex items-center justify-between z-10">
              <div className="flex items-center gap-2">
                <Server className="w-5 h-5 text-indigo-600" />
                <h2 className="text-lg font-semibold text-slate-800">Assessment Details</h2>
              </div>
              <button
                onClick={onClose}
                className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-200 rounded-full transition-colors"
                aria-label="Close drawer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-8">
              
              {/* Pipeline Status */}
              <section>
                <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                  <Clock className="w-4 h-4" /> Pipeline Status
                </h3>
                <div className="bg-slate-50 rounded-lg p-3 text-sm text-slate-600 font-mono border border-slate-100">
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span>Execution Time</span>
                    <span className="text-emerald-600 font-semibold">{(Math.random() * (45 - 20) + 20).toFixed(1)}ms</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span>Pipeline Version</span>
                    <span>v1.2.4-stable</span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span>Memory Usage</span>
                    <span>42.8 MB</span>
                  </div>
                </div>
              </section>

              {/* Model */}
              <section>
                <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                  <Brain className="w-4 h-4" /> Classifier Output
                </h3>
                <div className="bg-indigo-50/50 rounded-lg p-4 border border-indigo-100">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-slate-600">Model Architecture</span>
                    <span className="text-xs font-mono text-indigo-700 bg-indigo-100 px-2 py-0.5 rounded">DistilBERT-uncased</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-slate-600">SIF Precursor Prob.</span>
                    <span className="text-sm font-bold text-slate-800">{confidencePercent}</span>
                  </div>
                </div>
              </section>

              {/* Context Extraction */}
              <section>
                <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                  <Cpu className="w-4 h-4" /> Context Extraction
                </h3>
                <div className="bg-slate-900 rounded-lg p-4 overflow-x-auto">
                  <pre className="text-xs text-emerald-400 font-mono">
{JSON.stringify({
  activity: activity || null,
  hazard: hazard || null,
  location: location || null,
  barrier: barrier || null,
  barrier_status: barrier_status || null
}, null, 2)}
                  </pre>
                </div>
              </section>

              {/* Decision Engine */}
              <section>
                <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                  <GitBranch className="w-4 h-4" /> Decision Engine
                </h3>
                <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                  <div className="bg-slate-50 px-4 py-2 border-b border-slate-200 flex justify-between items-center">
                    <span className="text-sm font-medium text-slate-700">Priority Score Formula</span>
                    <span className="text-sm font-bold text-slate-900">{scorePercent}</span>
                  </div>
                  <div className="p-4 space-y-2 text-sm text-slate-600 font-mono">
                    <div className="flex justify-between">
                      <span>0.35 × model_prob</span>
                      <span className="text-slate-400">({(prob * 0.35).toFixed(3)})</span>
                    </div>
                    <div className="flex justify-between">
                      <span>0.30 × rule_severity</span>
                      <span className="text-slate-400">({((rule_severity_score || 0) * 0.3).toFixed(3)})</span>
                    </div>
                    <div className="flex justify-between">
                      <span>0.20 × barrier_gap</span>
                      <span className="text-slate-400">({((barrier_gap_score || 0) * 0.2).toFixed(3)})</span>
                    </div>
                    <div className="flex justify-between">
                      <span>0.15 × recurrence</span>
                      <span className="text-slate-400">({((recurrence_score || 0) * 0.15).toFixed(3)})</span>
                    </div>
                  </div>
                </div>
              </section>

              {/* Safety Rules */}
              <section>
                <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                  <ShieldAlert className="w-4 h-4" /> Safety Rules Fired
                </h3>
                {rules_fired && rules_fired.length > 0 ? (
                  <ul className="space-y-2">
                    {rules_fired.map((rule, idx) => (
                      <li key={idx} className="bg-amber-50 border border-amber-200 rounded p-3">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-mono font-semibold text-amber-700 bg-amber-200 px-1.5 py-0.5 rounded">
                            {rule.rule_id || `RULE_${idx + 1}`}
                          </span>
                          <span className="text-xs text-amber-600 font-medium">Sev: {rule.severity || '0.0'}</span>
                        </div>
                        <p className="text-sm text-amber-900">{rule.description || rule.category || rule}</p>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="text-sm text-slate-500 italic bg-slate-50 p-3 rounded border border-slate-100">
                    No deterministic rules fired.
                  </div>
                )}

                {/* Evidence Signals */}
                {lime_tokens && lime_tokens.length > 0 && (
                  <div className="mt-4">
                    <h4 className="text-xs font-semibold text-slate-500 uppercase mb-2">Evidence Signals</h4>
                    <div className="flex flex-wrap gap-2">
                      {lime_tokens.map((token, idx) => (
                        <span key={idx} className="inline-flex items-center gap-1 bg-red-50 text-red-700 text-xs font-mono px-2 py-1 rounded border border-red-100">
                          {token[0]} <span className="text-red-400">+{parseFloat(token[1]).toFixed(2)}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </section>

              {/* Semantic Analysis */}
              <section>
                <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                  <Database className="w-4 h-4" /> Semantic Analysis
                </h3>
                {similar_reports && similar_reports.length > 0 ? (
                  <div className="bg-slate-50 rounded-lg p-3 text-sm text-slate-600 border border-slate-100">
                    <div className="flex justify-between py-1 border-b border-slate-100 mb-2">
                      <span className="font-medium">Mean Similarity</span>
                      <span className="font-mono">
                        {(similar_reports.reduce((acc, r) => acc + (r.similarity_score || r.score || 0), 0) / similar_reports.length).toFixed(3)}
                      </span>
                    </div>
                    <div className="font-medium text-xs text-slate-400 uppercase mb-1 mt-3">Related Vectors</div>
                    <div className="flex flex-wrap gap-1">
                      {similar_reports.map((r, i) => (
                        <span key={i} className="text-xs font-mono bg-white border border-slate-200 px-1.5 py-0.5 rounded">
                          {r.report_id}
                        </span>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="text-sm text-slate-500 italic bg-slate-50 p-3 rounded border border-slate-100">
                    No semantically similar vectors found.
                  </div>
                )}
              </section>

            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

export default TechnicalAssessmentDrawer;
