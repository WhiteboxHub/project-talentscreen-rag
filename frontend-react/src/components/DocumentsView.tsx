import { useState, useEffect, useRef } from 'react';
import { getDocuments, uploadDocuments } from '../api';
import { Upload, RefreshCw, FileText, CheckCircle, XCircle, Clock } from 'lucide-react';

export default function DocumentsView() {
  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [docType, setDocType] = useState('auto-detect');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchDocs = async () => {
    setLoading(true);
    try {
      const data = await getDocuments();
      setDocuments(data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, []);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;
    
    setUploading(true);
    try {
      await uploadDocuments(e.target.files, docType);
      // Wait a moment before refreshing to let the background task start
      setTimeout(() => fetchDocs(), 1500);
    } catch (err) {
      console.error('Upload failed:', err);
      alert('Upload failed. Check backend connection.');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const renderStatus = (status: string) => {
    if (status === 'completed') return <span className="flex-center" style={{ gap: '6px', color: 'var(--color-success)' }}><CheckCircle size={14}/> Indexed</span>;
    if (status.includes('failed')) return <span className="flex-center" style={{ gap: '6px', color: 'var(--color-danger)' }}><XCircle size={14}/> Failed</span>;
    return <span className="flex-center" style={{ gap: '6px', color: 'var(--color-warning)' }}><Clock size={14}/> Processing</span>;
  };

  return (
    <div className="animate-fade-in">
      <div className="flex-between" style={{ marginBottom: '32px' }}>
        <div>
          <h1 className="text-gradient" style={{ fontSize: '2.5rem', marginBottom: '8px' }}>Document Hub</h1>
          <p style={{ color: 'var(--color-text-muted)', fontSize: '1.125rem' }}>
            Manage resumes, SOPs, and interview guides in the knowledge base.
          </p>
        </div>
        
        <button onClick={fetchDocs} className="btn-secondary flex-center" style={{ gap: '8px' }}>
          <RefreshCw size={16} className={loading ? 'spin' : ''} /> Refresh Sync
        </button>
      </div>

      <div className="glass-panel" style={{ padding: '32px', marginBottom: '32px', border: '1px dashed var(--color-border)' }}>
        <div className="flex-center" style={{ flexDirection: 'column', gap: '16px' }}>
          <div style={{ background: 'rgba(59, 130, 246, 0.1)', padding: '16px', borderRadius: '50%', color: 'var(--color-primary)' }}>
            <Upload size={32} />
          </div>
          <div style={{ textAlign: 'center' }}>
            <h3 style={{ marginBottom: '8px' }}>Ingest New Documents</h3>
            <p style={{ color: 'var(--color-text-muted)', fontSize: '0.875rem', marginBottom: '16px' }}>Supported formats: PDF, DOCX, TXT, MD</p>
            
            <div className="flex-center" style={{ gap: '16px' }}>
              <select value={docType} onChange={(e) => setDocType(e.target.value)} style={{ minWidth: '150px' }}>
                <option value="auto-detect">Auto Detect Type</option>
                <option value="resume">Resume / CV</option>
                <option value="job_description">Job Description</option>
                <option value="policy">Hiring Policy</option>
                <option value="interview_guide">Interview Guide</option>
              </select>

              <input 
                type="file" 
                multiple 
                ref={fileInputRef}
                style={{ display: 'none' }}
                onChange={handleUpload}
                accept=".pdf,.docx,.txt,.md"
              />
              <button 
                className="btn-primary" 
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
              >
                {uploading ? 'Queueing...' : 'Select Files'}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="glass-panel" style={{ padding: '24px' }}>
        <h3 style={{ marginBottom: '20px' }}>Indexed Documents ({documents.length})</h3>
        
        {loading && documents.length === 0 ? (
          <div className="flex-center" style={{ padding: '40px' }}><div className="spinner"></div></div>
        ) : documents.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--color-text-muted)' }}>
            No documents found in the database.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--color-border)', color: 'var(--color-text-muted)' }}>
                  <th style={{ padding: '12px 16px' }}>File Name</th>
                  <th style={{ padding: '12px 16px' }}>Type</th>
                  <th style={{ padding: '12px 16px' }}>Status</th>
                  <th style={{ padding: '12px 16px' }}>Chunks</th>
                  <th style={{ padding: '12px 16px' }}>Uploaded</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr key={doc.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <td style={{ padding: '16px' }}>
                      <div className="flex-center" style={{ justifyContent: 'flex-start', gap: '8px' }}>
                        <FileText size={16} color="var(--color-text-muted)" />
                        <span style={{ fontWeight: 500 }}>{doc.filename}</span>
                      </div>
                    </td>
                    <td style={{ padding: '16px', color: 'var(--color-text-muted)' }}>
                      <span className="badge" style={{ background: 'rgba(255,255,255,0.1)', color: 'white', border: 'none' }}>
                        {doc.type.toUpperCase()}
                      </span>
                    </td>
                    <td style={{ padding: '16px' }}>{renderStatus(doc.status)}</td>
                    <td style={{ padding: '16px', color: 'var(--color-text-muted)' }}>{doc.chunks || 0}</td>
                    <td style={{ padding: '16px', color: 'var(--color-text-muted)' }}>
                      {new Date(doc.uploaded_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
