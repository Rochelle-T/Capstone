import React, { useContext, useEffect, useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';

const navigation = [
  { label: 'Dashboard', to: '/dashboard', end: true },
  { label: 'Analysis', to: '/exoplanet' },
  { label: 'Results', to: '/results' },
  { label: 'Settings', to: '/settings' },
];

export default function MissionSidebar() {
  const { user, logout } = useContext(AuthContext);
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem('sidebar_collapsed') === 'true',
  );

  useEffect(() => {
    document.body.classList.toggle('sidebar-collapsed', collapsed);
    localStorage.setItem('sidebar_collapsed', String(collapsed));
    return () => document.body.classList.remove('sidebar-collapsed');
  }, [collapsed]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const closeSidebar = () => setSidebarOpen(false);

  return (
    <>
      <button
        className="mobile-menu-button"
        onClick={() => setSidebarOpen((open) => !open)}
        aria-label={sidebarOpen ? 'Close navigation' : 'Open navigation'}
        aria-expanded={sidebarOpen}
      >
        {sidebarOpen ? 'Close' : 'Menu'}
      </button>
      {sidebarOpen && (
        <button
          className="sidebar-backdrop"
          onClick={closeSidebar}
          aria-label="Close navigation"
        />
      )}
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''} ${collapsed ? 'collapsed' : ''}`}>
        <Link to="/" className="nav-brand" onClick={closeSidebar}>
          <span className="brand-mark">AS</span>
          <div>
            <h1>AstroSense</h1>
            <span>MISSION CONTROL</span>
          </div>
        </Link>
        <button
          className="sidebar-collapse-button"
          onClick={() => setCollapsed((value) => !value)}
          aria-label={collapsed ? 'Expand navigation' : 'Minimize navigation'}
          title={collapsed ? 'Expand navigation' : 'Minimize navigation'}
        >
          {collapsed ? '>' : '<'}
        </button>
        <nav className="sidebar-nav" aria-label="Primary navigation">
          {navigation.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}
              onClick={closeSidebar}
              title={collapsed ? item.label : undefined}
            >
              <span className="sidebar-link-label">{item.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className="user-email">{user?.email}</span>
          <button onClick={handleLogout} className="btn-logout">Sign Out</button>
        </div>
      </aside>
    </>
  );
}
