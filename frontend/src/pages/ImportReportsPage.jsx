import React, { useState, useRef } from 'react';
import { 
  UploadCloud, 
  FileText, 
  X, 
  CheckCircle,
  AlertTriangle,
  FileSpreadsheet,
  ChevronRight,
  Loader2,
  Download
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { uploadDocument, processImportedText, API_BASE } from '../services/api';
import { useToast, EmptyState, PriorityBadge, ExportDropdown } from '../components/ui';

export default function ImportReportsPage() {
  const [dragActive, setDragActive] = useState(false);
  const [files, setFiles] = useState([]);
  const [extractedData, setExtractedData] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [analysisSubState, setAnalysisSubState] = useState('');
  
  const toast = useToast();
  const inputRef = useRef(null);

  // File Upload Handlers
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleChange = (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      handleFiles(e.target.files);
    }
  };

  const handleFiles = async (fileList) => {
    const file = fileList[0]; // Process one file at a time for MVP
    
    const newFileState = {
      id: Math.random().toString(36).substr(2, 9),
      name: file.name,
      size: (file.size / 1024 / 1024).toFixed(2) + " MB",
      status: 'reading', // reading, extracting, success, error
    };
    
    setFiles([newFileState]);
    setExtractedData(null);
    setAnalysisResult(null);
    setAnalysisSubState('');

    try {
      // Step 1: Upload and Extract
      // simulate brief "Reading report data..."
      await new Promise(r => setTimeout(r, 600));
      
      setFiles([{ ...newFileState, status: 'extracting' }]);
      const res = await uploadDocument(file);
      
      setFiles([{ ...newFileState, status: 'success' }]);
      toast.success(`Successfully extracted ${file.name}`);
      
      setExtractedData({
        ...res.data,
        editableText: res.data.extracted_text || ""
      });

    } catch (err) {
      setFiles([{ ...newFileState, status: 'error', error: err.message }]);
      toast.error(err.message || 'Failed to upload document');
    }
  };

  // Processing Extracted Data
  const handleProcessText = async () => {
    if (!extractedData || !extractedData.editableText) return;
    
    setFiles([{ ...files[0], status: 'analyzing' }]);
    
    try {
      setAnalysisSubState('Preparing safety assessment...');
      
      // We don't want to block the real call, but we can animate the subState message.
      const analyzePromise = processImportedText(
        extractedData.editableText, 
        { filename: extractedData.filename },
        extractedData.temp_file_id,
        extractedData.source_file_name
      );
      
      // Show intermediate message just for UX polish
      setTimeout(() => {
        if (files.length > 0 && files[0].status === 'analyzing') {
          setAnalysisSubState('Checking critical controls...');
        }
      }, 1500);

      const result = await analyzePromise;
      
      setFiles([{ ...files[0], status: 'completed' }]);
      setAnalysisSubState('Assessment ready');
      setAnalysisResult(result);
      toast.success("Safety Assessment Complete");
    } catch (err) {
      setFiles([{ ...files[0], status: 'error', error: err.message }]);
      setAnalysisSubState('Failed');
      toast.error(err.message || "Analysis failed");
    }
  };

  const resetFlow = () => {
    setFiles([]);
    setExtractedData(null);
    setAnalysisResult(null);
    setAnalysisSubState('');
  };
  
  const handleDownloadPdf = () => {
    if (!analysisResult) return;
    window.open(`${API_BASE}/reports/${analysisResult.report_id}/download/assessment`, '_blank');
  };

  // Status rendering helper
  const getStatusDisplay = (file) => {
    switch (file.status) {
      case 'reading': return { label: 'Reading report data...', icon: <Loader2 size={14} className="spin" />, color: 'var(--slate-500)', bgColor: 'transparent', bar: 20 };
      case 'extracting': return { label: 'Extracting narrative...', icon: <Loader2 size={14} className="spin" />, color: 'var(--primary)', bgColor: 'transparent', bar: 50 };
      case 'analyzing': return { label: analysisSubState || 'Preparing safety assessment...', icon: <Loader2 size={14} className="spin" />, color: 'var(--sif-medium)', bgColor: 'transparent', bar: 80 };
      case 'success': return { label: 'Ready for review', icon: <CheckCircle size={14} />, color: 'var(--sif-low)', bgColor: '#f0fdf4', bar: 100 };
      case 'completed': return { label: 'Assessment ready', icon: <CheckCircle size={14} />, color: 'var(--sif-low)', bgColor: '#f0fdf4', bar: 100 };
      case 'error': return { label: file.error, icon: <AlertTriangle size={14} />, color: 'var(--sif-high)', bgColor: '#fef2f2', bar: 100 };
      default: return { label: '', icon: null, color: '', bar: 0 };
    }
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <div className="page-title">
          <h1>Import Reports</h1>
          <p>Extract and analyze safety observations from documents or spreadsheets.</p>
        </div>
        <div className="page-actions">
          <ExportDropdown />
        </div>
      </div>

      <div className="dashboard-grid" style={{ gridTemplateColumns: '1fr' }}>
        
        {/* WIZARD PROGRESS */}
        <AnimatePresence>
          {files.length > 0 && (
            <motion.div 
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="import-progress-bar"
              style={{ overflow: 'hidden' }}
            >
              <div className={`progress-step ${files[0].status !== 'reading' ? 'active' : ''}`}>
                1. Upload & Extract
              </div>
              <div className={`progress-step ${extractedData ? 'active' : ''}`}>
                2. Review Content
              </div>
              <div className={`progress-step ${analysisResult ? 'active' : ''}`}>
                3. Safety Assessment
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* STEP 1: UPLOAD ZONE */}
        <AnimatePresence>
          {files.length === 0 && (
            <motion.div 
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95, height: 0, overflow: 'hidden' }}
              transition={{ duration: 0.2 }}
            >
              <motion.div 
                className={`upload-zone ${dragActive ? 'active' : ''}`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => inputRef.current?.click()}
                onKeyDown={(e) => { if(e.key === 'Enter' || e.key === ' ') inputRef.current?.click(); }}
                tabIndex={0}
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.98 }}
                style={{ cursor: 'pointer', outline: 'none' }}
              >
                <input 
                  ref={inputRef}
                  type="file" 
                  className="hidden" 
                  accept=".pdf,.docx,.txt,.csv,.xlsx" 
                  onChange={handleChange} 
                  tabIndex={-1}
                />
                <UploadCloud size={48} color="var(--primary)" />
                <h3>Drop safety report here</h3>
                <p>or click to browse from your computer</p>
                <div className="supported-formats">
                  Supported formats: PDF, DOCX, TXT, CSV, XLSX
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* FILE CARDS */}
        <AnimatePresence>
          {files.map(file => {
            const statusInfo = getStatusDisplay(file);
            return (
              <motion.div 
                key={file.id} 
                className="panel upload-card"
                layout
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.9 }}
                transition={{ type: "spring", stiffness: 300, damping: 25 }}
                style={{ position: 'relative', overflow: 'hidden' }}
              >
                {/* Progress bar background for states */}
                {(file.status === 'reading' || file.status === 'extracting' || file.status === 'analyzing') && (
                  <motion.div 
                    initial={{ width: '0%' }}
                    animate={{ width: `${statusInfo.bar}%` }}
                    transition={{ duration: 0.5 }}
                    style={{ position: 'absolute', top: 0, left: 0, height: '4px', backgroundColor: statusInfo.color, zIndex: 10 }}
                  />
                )}
                <div className="upload-card-content">
                  {file.name.endsWith('.csv') || file.name.endsWith('.xlsx') ? (
                    <FileSpreadsheet size={24} color="#0284c7" />
                  ) : (
                    <FileText size={24} color="#475569" />
                  )}
                  <div className="file-info">
                    <strong>{file.name}</strong>
                    <span>{file.size}</span>
                  </div>
                </div>
                
                <div className="file-status">
                  <motion.span 
                    key={statusInfo.label}
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="status-badge" 
                    style={{ color: statusInfo.color, backgroundColor: statusInfo.bgColor, gap: '0.4rem', border: 'none' }}
                  >
                    {statusInfo.icon} {statusInfo.label}
                  </motion.span>
                  
                  <motion.button 
                    whileHover={{ scale: 1.1, backgroundColor: '#fee2e2', color: '#dc2626' }}
                    whileTap={{ scale: 0.9 }}
                    className="btn btn-ghost btn-sm" 
                    onClick={resetFlow}
                    title="Cancel / Remove"
                  >
                    <X size={16} />
                  </motion.button>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>

        {/* STEP 2: REVIEW EXTRACTED TEXT */}
        <AnimatePresence>
          {extractedData && !extractedData.is_tabular && !analysisResult && (
            <motion.div 
              layout
              initial={{ opacity: 0, height: 0, scale: 0.95 }}
              animate={{ opacity: 1, height: 'auto', scale: 1 }}
              exit={{ opacity: 0, height: 0, scale: 0.95 }}
              transition={{ duration: 0.3 }}
              style={{ overflow: 'hidden' }}
            >
              <div className="panel import-review-panel">
                <div className="panel-header">
                  <h2>Review Extracted Content</h2>
                  <motion.button 
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className="btn btn-primary" 
                    onClick={() => {
                      if (!extractedData || !extractedData.editableText) return;
                      setFiles([{ ...files[0], status: 'analyzing' }]);
                      setAnalysisSubState('Preparing safety assessment...');
                      
                      const analyzePromise = processImportedText(
                        extractedData.editableText, 
                        { filename: extractedData.filename },
                        extractedData.temp_file_id,
                        extractedData.source_file_name,
                        extractedData.extracted_metadata,
                        extractedData.corrected_metadata
                      );
                      
                      setTimeout(() => {
                        if (files.length > 0 && files[0].status === 'analyzing') {
                          setAnalysisSubState('Checking critical controls...');
                        }
                      }, 1500);

                      analyzePromise.then(result => {
                        setFiles([{ ...files[0], status: 'completed' }]);
                        setAnalysisSubState('Assessment ready');
                        setAnalysisResult(result);
                        toast.success("Safety Assessment Complete");
                      }).catch(err => {
                        setFiles([{ ...files[0], status: 'error', error: err.message }]);
                        setAnalysisSubState('Failed');
                        toast.error(err.message || "Analysis failed");
                      });
                    }}
                    disabled={files.length > 0 && files[0].status === 'analyzing'}
                  >
                    Analyze Report <ChevronRight size={16} />
                  </motion.button>
                </div>
                <div className="panel-content">
                  <p className="help-text">Review and edit the extracted narrative and metadata before sending it to the SIF decision engine.</p>
                  
                  {/* SOURCE FILE */}
                  <div style={{ marginBottom: '1.5rem' }}>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--slate-500)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>Source File</label>
                    <div style={{ padding: '0.75rem', background: 'var(--bg-main)', borderRadius: '6px', border: '1px solid var(--border)', color: 'var(--text-main)', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <FileText size={16} color="var(--slate-400)" />
                      {extractedData.source_file_name || extractedData.filename}
                    </div>
                  </div>

                  {/* EXTRACTED OBSERVATION */}
                  <div style={{ marginBottom: '1.5rem' }}>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--slate-500)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>Extracted Observation</label>
                    <textarea 
                      className="import-textarea"
                      value={extractedData.editableText}
                      onChange={(e) => setExtractedData({...extractedData, editableText: e.target.value})}
                      rows={8}
                      disabled={files.length > 0 && files[0].status === 'analyzing'}
                    />
                  </div>

                  {/* METADATA FIELDS */}
                  <div style={{ borderTop: '1px solid var(--border)', paddingTop: '1.5rem' }}>
                    <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem', color: 'var(--text-main)' }}>Detected Details</h3>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                      {[
                        { key: 'location', label: 'Location' },
                        { key: 'activity', label: 'Activity' },
                        { key: 'hazard', label: 'Hazard' },
                        { key: 'barrier', label: 'Barrier' },
                        { key: 'report_type', label: 'Report Type' },
                        { key: 'date', label: 'Date' },
                      ].map(field => {
                        const originalVal = (extractedData.extracted_metadata || {})[field.key];
                        const currentVal = extractedData.corrected_metadata ? extractedData.corrected_metadata[field.key] : originalVal;
                        const isEdited = currentVal !== originalVal && currentVal !== undefined;
                        const isMissing = !originalVal && !isEdited;
                        const displayVal = currentVal || originalVal || '';

                        return (
                          <div key={field.key} style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--slate-500)', textTransform: 'uppercase' }}>
                                {field.label}
                              </label>
                              <span style={{ 
                                fontSize: '0.7rem', 
                                padding: '0.1rem 0.4rem', 
                                borderRadius: '12px',
                                background: isEdited ? '#dbeafe' : (isMissing ? '#f1f5f9' : '#dcfce3'),
                                color: isEdited ? '#1e40af' : (isMissing ? '#64748b' : '#166534'),
                                fontWeight: 500
                              }}>
                                {isEdited ? 'User edited' : (isMissing ? 'Not identified' : 'Detected')}
                              </span>
                            </div>
                            <input
                              type="text"
                              value={displayVal}
                              placeholder={isMissing ? "Not identified" : ""}
                              disabled={files.length > 0 && files[0].status === 'analyzing'}
                              onChange={(e) => {
                                const newCorrected = { ...(extractedData.corrected_metadata || {}) };
                                newCorrected[field.key] = e.target.value;
                                setExtractedData({ ...extractedData, corrected_metadata: newCorrected });
                              }}
                              style={{
                                padding: '0.5rem',
                                borderRadius: '6px',
                                border: `1px solid ${isEdited ? '#bfdbfe' : 'var(--border)'}`,
                                background: 'var(--bg-main)',
                                color: 'var(--text-main)',
                                fontSize: '0.9rem',
                                outline: 'none',
                                transition: 'border-color 0.2s',
                              }}
                            />
                          </div>
                        );
                      })}
                    </div>
                  </div>

                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* STEP 2: TABULAR DATA (Placeholder for MVP) */}
        <AnimatePresence>
          {extractedData && extractedData.is_tabular && !analysisResult && (
            <motion.div 
              layout
              initial={{ opacity: 0, height: 0, scale: 0.95 }}
              animate={{ opacity: 1, height: 'auto', scale: 1 }}
              exit={{ opacity: 0, height: 0, scale: 0.95 }}
              transition={{ duration: 0.3 }}
              style={{ overflow: 'hidden' }}
            >
              <div className="panel">
                <div className="panel-header">
                  <h2>Map Columns (Bulk Import)</h2>
                </div>
                <div className="panel-content">
                  <EmptyState 
                    icon={FileSpreadsheet}
                    title="Tabular Data Found"
                    description="Column mapping for CSV/XLSX bulk imports will be available in the next release."
                  />
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* STEP 3: ANALYSIS RESULT */}
        <AnimatePresence>
          {analysisResult && (
            <motion.div 
              layout
              initial={{ opacity: 0, height: 0, scale: 0.95 }}
              animate={{ opacity: 1, height: 'auto', scale: 1 }}
              exit={{ opacity: 0, height: 0, scale: 0.95 }}
              transition={{ duration: 0.3 }}
              style={{ overflow: 'hidden' }}
            >
              <div className="panel">
                <div className="panel-header">
                  <div className="panel-title">
                    <h2>Analysis Complete</h2>
                    <PriorityBadge priority={analysisResult.priority} />
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <motion.button 
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      className="btn btn-outline" 
                      onClick={handleDownloadPdf}
                      style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
                    >
                      <Download size={14} /> View Assessment
                    </motion.button>
                  </div>
                </div>
                <div className="panel-content">
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', padding: '1rem' }}>
                    <motion.div 
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.2 }}
                    >
                      <h4 style={{ color: 'var(--slate-500)', marginBottom: '0.5rem', fontSize: '0.8rem', textTransform: 'uppercase' }}>Extracted Metadata</h4>
                      <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                        <li><strong>Activity:</strong> {analysisResult.activity || 'Unknown'}</li>
                        <li><strong>Hazard:</strong> {analysisResult.hazard || 'None Detected'}</li>
                        <li><strong>Barrier Status:</strong> {analysisResult.barrier ? `${analysisResult.barrier} (${analysisResult.barrier_status})` : 'N/A'}</li>
                      </ul>
                    </motion.div>
                    <motion.div 
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.3 }}
                    >
                      <h4 style={{ color: 'var(--slate-500)', marginBottom: '0.5rem', fontSize: '0.8rem', textTransform: 'uppercase' }}>System Actions</h4>
                      <p style={{ fontSize: '0.9rem', color: 'var(--slate-700)' }}>
                        Report <strong>{analysisResult.report_id}</strong> has been saved to the database.
                        {analysisResult.priority === 'HIGH' && " It has been routed to the HSE Review queue."}
                      </p>
                      <motion.button 
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        className="btn btn-outline" 
                        style={{ marginTop: '1rem' }}
                        onClick={resetFlow}
                      >
                        Import Another
                      </motion.button>
                    </motion.div>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

      </div>
    </div>
  );
}
