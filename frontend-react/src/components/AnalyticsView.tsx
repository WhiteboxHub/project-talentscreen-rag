import { useState, useEffect } from 'react';
import { getAnalytics } from '../api';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Database, Search, Clock, RefreshCw } from 'lucide-react';

export default function AnalyticsView() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const stats = await getAnalytics();
      setData(stats);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  if (loading && !data) {
    return <div className="flex-center" style={{ height: '50vh' }}><div className="spinner"></div></div>;
  }

  if (!data || data.error) {
    return (
      <div className="glass-panel" style={{ padding: '40px', textAlign: 'center', color: 'var(--color-danger)' }}>
        Failed to load analytics data. Ensure the backend is running.
      </div>
    );
  }

  const { documents, activity, insights } = data;

  // Format skills for Recharts
  const skillData = Object.entries(insights.top_skills || {}).map(([name, count]) => ({
    name,
    count
  }));

  const docTypeData = Object.entries(documents.by_type || {}).map(([name, count]) => ({
    name: name.toUpperCase(),
    count
  }));

  const COLORS = ['#3b82f6', '#2dd4bf', '#8b5cf6', '#ec4899', '#f59e0b'];

  return (
    <div className="animate-fade-in">
      <div className="flex-between" style={{ marginBottom: '32px' }}>
        <div>
          <h1 className="text-gradient" style={{ fontSize: '2.5rem', marginBottom: '8px' }}>Talent Pool Stats</h1>
          <p style={{ color: 'var(--color-text-muted)', fontSize: '1.125rem' }}>
            Real-time analytics across your entire recruitment database.
          </p>
        </div>
        <button onClick={fetchStats} className="btn-secondary flex-center" style={{ gap: '8px' }}>
          <RefreshCw size={16} className={loading ? 'spin' : ''} /> Refresh
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '24px', marginBottom: '32px' }}>
        <div className="glass-panel card">
          <div className="flex-between" style={{ marginBottom: '16px' }}>
            <h3 style={{ color: 'var(--color-text-muted)', fontSize: '1rem', fontWeight: 500 }}>Total Documents</h3>
            <Database size={20} color="var(--color-primary)" />
          </div>
          <div style={{ fontSize: '2.5rem', fontWeight: 800, color: 'var(--color-text-main)' }}>
            {documents.total}
          </div>
          <div style={{ fontSize: '0.875rem', color: 'var(--color-success)', marginTop: '8px' }}>
            {documents.completed} successfully indexed
          </div>
        </div>

        <div className="glass-panel card">
          <div className="flex-between" style={{ marginBottom: '16px' }}>
            <h3 style={{ color: 'var(--color-text-muted)', fontSize: '1rem', fontWeight: 500 }}>Avg. Experience</h3>
            <Clock size={20} color="var(--color-accent)" />
          </div>
          <div style={{ fontSize: '2.5rem', fontWeight: 800, color: 'var(--color-text-main)' }}>
            {insights.avg_experience_years} <span style={{ fontSize: '1rem', color: 'var(--color-text-muted)' }}>Years</span>
          </div>
          <div style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)', marginTop: '8px' }}>
            Across all candidate profiles
          </div>
        </div>

        <div className="glass-panel card">
          <div className="flex-between" style={{ marginBottom: '16px' }}>
            <h3 style={{ color: 'var(--color-text-muted)', fontSize: '1rem', fontWeight: 500 }}>Total Searches</h3>
            <Search size={20} color="#8b5cf6" />
          </div>
          <div style={{ fontSize: '2.5rem', fontWeight: 800, color: 'var(--color-text-main)' }}>
            {activity.total_searches}
          </div>
          <div style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)', marginTop: '8px' }}>
            Queries executed by recruiters
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        <div className="glass-panel" style={{ padding: '24px' }}>
          <h3 style={{ marginBottom: '24px' }}>Top Skills in Talent Pool</h3>
          {skillData.length > 0 ? (
            <div style={{ height: '300px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={skillData} layout="vertical" margin={{ top: 0, right: 0, left: 40, bottom: 0 }}>
                  <XAxis type="number" hide />
                  <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} tick={{ fill: 'var(--color-text-muted)' }} />
                  <Tooltip 
                    cursor={{ fill: 'rgba(255,255,255,0.05)' }} 
                    contentStyle={{ background: 'var(--color-bg-surface)', border: '1px solid var(--color-border)', borderRadius: '8px' }}
                  />
                  <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                    {skillData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div style={{ color: 'var(--color-text-muted)', textAlign: 'center', padding: '40px' }}>No skill data available</div>
          )}
        </div>

        <div className="glass-panel" style={{ padding: '24px' }}>
          <h3 style={{ marginBottom: '24px' }}>Document Types</h3>
          {docTypeData.length > 0 ? (
            <div style={{ height: '300px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={docTypeData} margin={{ top: 20, right: 0, left: 0, bottom: 0 }}>
                  <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: 'var(--color-text-muted)', fontSize: 12 }} />
                  <YAxis hide />
                  <Tooltip 
                    cursor={{ fill: 'rgba(255,255,255,0.05)' }} 
                    contentStyle={{ background: 'var(--color-bg-surface)', border: '1px solid var(--color-border)', borderRadius: '8px' }}
                  />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {docTypeData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[(index + 2) % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div style={{ color: 'var(--color-text-muted)', textAlign: 'center', padding: '40px' }}>No document data available</div>
          )}
        </div>
      </div>
    </div>
  );
}
