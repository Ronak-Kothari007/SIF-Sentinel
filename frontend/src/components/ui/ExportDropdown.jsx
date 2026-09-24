import React, { useState, useRef, useEffect } from 'react';
import { Download, FileSpreadsheet, FileText, ChevronDown } from 'lucide-react';
import { getExportUrl } from '../../services/api';
import { useToast } from './Toast';

export default function ExportDropdown({ filters = {}, disabled = false }) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  const toast = useToast();

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleExport = (format, exportType) => {
    setIsOpen(false);
    toast.success(`Exporting ${exportType === 'all' ? 'All' : 'Filtered'} Reports to ${format.toUpperCase()}...`);
    
    const url = getExportUrl({
      format,
      exportType,
      priority: filters.priority || '',
      hazard: filters.hazard || '',
      activity: filters.activity || ''
    });

    window.open(url, '_blank');
  };

  return (
    <div className="dropdown" ref={dropdownRef} style={{ position: 'relative', display: 'inline-block' }}>
      <button 
        className="btn btn-outline" 
        onClick={() => setIsOpen(!isOpen)} 
        disabled={disabled}
        style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
      >
        <Download size={16} />
        Export
        <ChevronDown size={14} />
      </button>

      {isOpen && (
        <div style={{
          position: 'absolute',
          top: '100%',
          right: 0,
          marginTop: '0.5rem',
          backgroundColor: '#fff',
          border: '1px solid #e2e8f0',
          borderRadius: '6px',
          boxShadow: 'var(--shadow-md)',
          minWidth: '220px',
          zIndex: 50,
          padding: '0.5rem 0'
        }}>
          <div style={{ padding: '0.25rem 1rem', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', textTransform: 'uppercase' }}>
            Current View
          </div>
          <button 
            onClick={() => handleExport('csv', 'current')}
            style={{ width: '100%', display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 1rem', border: 'none', background: 'none', cursor: 'pointer', fontSize: '0.9rem', color: '#1e293b', textAlign: 'left' }}
            onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#f1f5f9'}
            onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
          >
            <FileText size={16} color="#475569" /> Filtered as CSV
          </button>
          <button 
            onClick={() => handleExport('xlsx', 'current')}
            style={{ width: '100%', display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 1rem', border: 'none', background: 'none', cursor: 'pointer', fontSize: '0.9rem', color: '#1e293b', textAlign: 'left' }}
            onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#f1f5f9'}
            onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
          >
            <FileSpreadsheet size={16} color="#0284c7" /> Filtered as XLSX
          </button>
          
          <div style={{ height: '1px', backgroundColor: '#e2e8f0', margin: '0.5rem 0' }} />
          
          <div style={{ padding: '0.25rem 1rem', fontSize: '0.75rem', fontWeight: 600, color: '#64748b', textTransform: 'uppercase' }}>
            Full Database
          </div>
          <button 
            onClick={() => handleExport('csv', 'all')}
            style={{ width: '100%', display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 1rem', border: 'none', background: 'none', cursor: 'pointer', fontSize: '0.9rem', color: '#1e293b', textAlign: 'left' }}
            onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#f1f5f9'}
            onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
          >
            <FileText size={16} color="#475569" /> All Reports as CSV
          </button>
          <button 
            onClick={() => handleExport('xlsx', 'all')}
            style={{ width: '100%', display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 1rem', border: 'none', background: 'none', cursor: 'pointer', fontSize: '0.9rem', color: '#1e293b', textAlign: 'left' }}
            onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#f1f5f9'}
            onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
          >
            <FileSpreadsheet size={16} color="#0284c7" /> All Reports as XLSX
          </button>
        </div>
      )}
    </div>
  );
}
