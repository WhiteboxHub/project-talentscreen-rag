import { useState } from 'react';
import { Search, MessageSquare, Files, BarChart2, Target } from 'lucide-react';
import SearchView from './components/SearchView';
import ChatView from './components/ChatView';
import DocumentsView from './components/DocumentsView';
import AnalyticsView from './components/AnalyticsView';

function App() {
  const [activeTab, setActiveTab] = useState('search');

  const renderContent = () => {
    switch (activeTab) {
      case 'search': return <SearchView />;
      case 'chat': return <ChatView />;
      case 'documents': return <DocumentsView />;
      case 'analytics': return <AnalyticsView />;
      default: return <SearchView />;
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar */}
      <nav className="sidebar animate-fade-in">
        <div className="flex-center" style={{ gap: '12px', marginBottom: '40px' }}>
          <Target size={32} color="var(--color-primary)" />
          <div>
            <h2 className="text-gradient" style={{ fontSize: '1.5rem', fontWeight: 800 }}>Talent Screen</h2>
            <span style={{ fontSize: '0.75rem', color: 'var(--color-accent)' }}>Enterprise Edition</span>
          </div>
        </div>

        <div style={{ flex: 1 }}>
          <button 
            className={`nav-item ${activeTab === 'search' ? 'active' : ''}`}
            onClick={() => setActiveTab('search')}
          >
            <Search size={20} /> Smart Retrieval
          </button>
          
          <button 
            className={`nav-item ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => setActiveTab('chat')}
          >
            <MessageSquare size={20} /> Talent Intelligence
          </button>
          
          <button 
            className={`nav-item ${activeTab === 'documents' ? 'active' : ''}`}
            onClick={() => setActiveTab('documents')}
          >
            <Files size={20} /> Documents
          </button>
          
          <button 
            className={`nav-item ${activeTab === 'analytics' ? 'active' : ''}`}
            onClick={() => setActiveTab('analytics')}
          >
            <BarChart2 size={20} /> Analytics
          </button>
        </div>

        <div className="glass-panel" style={{ padding: '16px', textAlign: 'center', marginTop: 'auto' }}>
          <div className="flex-center" style={{ gap: '8px' }}>
            <div className="pulse-indicator"></div>
            <span style={{ fontSize: '0.875rem', fontWeight: 600 }}>System Online</span>
          </div>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="main-content">
        <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
          {renderContent()}
        </div>
      </main>
    </div>
  );
}

export default App;
