import React, { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import { fileService } from '../services/api';
import '../styles/Dashboard.css';

const Dashboard = () => {
  const { user, logout } = useContext(AuthContext);
  const navigate = useNavigate();
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState(''); // 'success' or 'error'
  const [dragActive, setDragActive] = useState(false);

  useEffect(() => {
    if (!user) {
      navigate('/login');
      return;
    }
    loadFiles();
  }, [user, navigate]);

  const loadFiles = async () => {
    setLoading(true);
    try {
      const data = await fileService.listFiles();
      setFiles(data.files);
    } catch (error) {
      console.error('Error loading files:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (file) => {
    if (!file.name.match(/\.(fits|fit|fts)$/i)) {
      setMessage('Please upload a valid FITS file (.fits, .fit, or .fts)');
      setMessageType('error');
      return;
    }

    setUploading(true);
    try {
      await fileService.uploadFits(file);
      setMessage('✓ File uploaded successfully!');
      setMessageType('success');
      loadFiles();
      setTimeout(() => setMessage(''), 3000);
    } catch (error) {
      const errorMsg = error.response?.data?.detail || 'Upload failed';
      // Check if file actually uploaded despite backend error
      if (errorMsg.includes('Zenodo') && error.response?.status === 500) {
        setMessage('⚠ File uploaded to Zenodo but with connection warning. Check your files list.');
        setMessageType('warning');
      } else {
        setMessage(errorMsg);
        setMessageType('error');
      }
    } finally {
      setUploading(false);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      handleFileUpload(droppedFile);
    }
  };

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      handleFileUpload(selectedFile);
    }
  };

  const handleDelete = async (filename) => {
    if (window.confirm('Delete this file?')) {
      try {
        await fileService.deleteFile(filename);
        loadFiles();
        setMessage('File deleted successfully');
        setTimeout(() => setMessage(''), 3000);
      } catch (error) {
        setMessage('Failed to delete file');
      }
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="dashboard-container">
      <div className="stars"></div>
      <div className="celestial-bg"></div>

      <nav className="navbar">
        <div className="nav-brand">
          <span className="rocket-icon">🚀</span>
          <h1>AstroSense</h1>
        </div>
        <div className="nav-right">
          <span className="user-email">{user?.email}</span>
          <button onClick={() => navigate('/exoplanet')} className="btn-nav">🔭 Analyze</button>
          <button onClick={handleLogout} className="btn-logout">Sign Out</button>
        </div>
      </nav>

      <div className="dashboard-header">
        <h2>Discover Exoplanets</h2>
        <p>Upload and analyze astronomical data</p>
      </div>

      <div className="dashboard-content">
        {message && <div className={`message ${messageType || 'info'}`}>{message}</div>}

        <div className="upload-section">
          <div
            className={`drop-zone ${dragActive ? 'active' : ''}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <div className="drop-icon">📤</div>
            <h3>Drop your FITS files here</h3>
            <p>or click to browse from your computer</p>
            <label className="btn-select">
              Select Files
              <input
                type="file"
                accept=".fits,.fit,.fts"
                onChange={handleFileSelect}
                disabled={uploading}
                style={{ display: 'none' }}
              />
            </label>
            <div className="supported-formats">
              Supported: FITS, FIT, FTS
            </div>
          </div>

          <div className="status-section">
            <h3>Upload Status</h3>
            <div className="status-box">
              {uploading && (
                <div className="uploading">
                  <div className="spinner"></div>
                  <p>Uploading...</p>
                </div>
              )}
              {!uploading && files.length === 0 && (
                <p className="empty-state">No files uploaded yet</p>
              )}
              {!uploading && files.length > 0 && (
                <p className="file-count">
                  ✓ {files.length} file{files.length !== 1 ? 's' : ''} uploaded
                </p>
              )}
            </div>
          </div>
        </div>

        <div className="files-section">
          <h3>Your Files</h3>
          {loading ? (
            <div className="loading">Loading files...</div>
          ) : files.length === 0 ? (
            <div className="empty-message">No files yet. Upload your first FITS file!</div>
          ) : (
            <div className="files-list">
              {files.map((file, index) => (
                <div key={index} className="file-card">
                  <div className="file-info">
                    <span className="file-icon">📊</span>
                    <div className="file-details">
                      <p className="file-name">{decodeURIComponent(file.name)}</p>
                      <p className="file-meta">
                        {(file.size / 1024 / 1024).toFixed(2)} MB • {new Date(file.created).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <button
                    className="btn-delete"
                    onClick={() => handleDelete(file.name)}
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
