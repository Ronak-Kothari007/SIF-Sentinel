import React, { useState, useEffect, useRef } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { 
  ShieldAlert, 
  LayoutDashboard, 
  FileText, 
  UploadCloud,
  CheckSquare, 
  GitBranch, 
  Activity,
  BarChart2,
  PlusCircle, 
  BellRing,
  Menu,
  X,
  User,
  Settings
} from 'lucide-react';

export default function Navbar({ 
  pendingReviewCount = 0, 
  unreadAlertsCount = 0,
  backendOnline, 
  onOpenAnalyze,
  onLoadDemo,
  demoLoading = false,
  isDemoLoaded = false,
  onStartJudgeDemo,
  isJudgeDemoActive = false,
}) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);
  const profileMenuRef = useRef(null);
  
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (profileMenuRef.current && !profileMenuRef.current.contains(event.target)) {
        setIsProfileMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const navItems = [
    { path: '/', label: 'Overview', icon: <LayoutDashboard size={16} /> },
    { path: '/reports', label: 'Reports', icon: <FileText size={16} /> },
    { path: '/import', label: 'Import Reports', icon: <UploadCloud size={16} /> },
    { path: '/review', label: 'HSE Review', icon: <CheckSquare size={16} />, badge: pendingReviewCount },
    { path: '/patterns', label: 'Risk Patterns', icon: <GitBranch size={16} /> },
    { path: '/actions', label: 'Actions', icon: <Activity size={16} /> },
    { path: '/analytics', label: 'Analytics', icon: <BarChart2 size={16} /> },
  ];

  return (
    <header className="navbar">
      <div className="navbar-inner">
        {/* Brand */}
        <NavLink to="/" className="brand-section" style={{ textDecoration: 'none' }}>
          <div className="brand-icon-wrapper">
            <ShieldAlert size={22} color="#0f172a" />
          </div>
          <div className="brand-text">
            <h1>SIF SENTINEL</h1>
            <p>Industrial Precursor Risk Triage System</p>
          </div>
        </NavLink>

        {/* Desktop Navigation */}
        <nav className="nav-links desktop-only">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            >
              {item.icon}
              {item.label}
              {item.badge > 0 && <span className="nav-link-badge">{item.badge}</span>}
            </NavLink>
          ))}
        </nav>

        {/* Right Section Actions & Status */}
        <div className="nav-actions">
          {unreadAlertsCount > 0 && (
            <button 
              className="btn btn-outline alert-btn desktop-only" 
              title={`${unreadAlertsCount} active precursor alerts`}
              onClick={() => navigate('/review')}
            >
              <BellRing size={14} color="var(--sif-high)" />
              <span>{unreadAlertsCount} Alerts</span>
            </button>
          )}

          <button 
            className="btn btn-primary btn-add-report desktop-only" 
            onClick={onOpenAnalyze}
          >
            <PlusCircle size={15} />
            <span>Add Report</span>
          </button>

          {/* User Profile / System Menu */}
          <div className="profile-menu-container" ref={profileMenuRef}>
            <button 
              className="profile-btn"
              onClick={() => setIsProfileMenuOpen(!isProfileMenuOpen)}
              title="System Status & Profile"
              aria-expanded={isProfileMenuOpen}
            >
              <div className="avatar">
                <User size={16} />
                <span className={`status-indicator ${backendOnline ? 'online' : 'offline'}`} />
              </div>
            </button>

            {isProfileMenuOpen && (
              <div className="profile-dropdown">
                <div className="dropdown-header">
                  <strong>Operations User</strong>
                  <div className="system-status">
                    <span className={`status-dot ${backendOnline ? '' : 'error'}`} />
                    <span>{backendOnline ? "API Online" : "API Offline"}</span>
                  </div>
                </div>
                
                <div className="dropdown-divider" />
                <div className="dropdown-section-title">System</div>
                
                <button className="dropdown-item" onClick={onLoadDemo} disabled={demoLoading}>
                  <Settings size={14} />
                  {demoLoading ? 'Loading...' : isDemoLoaded ? 'Reload Demo Dataset' : 'Load Demo Dataset'}
                </button>

                {onStartJudgeDemo && (
                  <button className="dropdown-item" onClick={onStartJudgeDemo}>
                    <Settings size={14} />
                    {isJudgeDemoActive ? 'Exit Presentation Mode' : 'Presentation Mode'}
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Mobile Menu Toggle */}
          <button 
            className="mobile-menu-toggle"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            aria-expanded={isMobileMenuOpen}
            aria-label="Toggle navigation menu"
          >
            {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>
      </div>

      {/* Mobile Navigation Menu */}
      {isMobileMenuOpen && (
        <div className="mobile-nav">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => `mobile-nav-link ${isActive ? 'active' : ''}`}
              onClick={() => setIsMobileMenuOpen(false)}
            >
              {item.icon}
              <span>{item.label}</span>
              {item.badge > 0 && <span className="nav-link-badge">{item.badge}</span>}
            </NavLink>
          ))}
          <div className="mobile-nav-actions">
            <button className="btn btn-primary w-full" onClick={() => {
              onOpenAnalyze();
              setIsMobileMenuOpen(false);
            }}>
              <PlusCircle size={15} />
              <span>Add Report</span>
            </button>
          </div>
        </div>
      )}
    </header>
  );
}
