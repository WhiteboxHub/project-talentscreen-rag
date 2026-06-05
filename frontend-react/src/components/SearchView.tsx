import { useState } from 'react';
import { searchCandidates } from '../api';
import { Search, ChevronDown, ChevronUp, Star, Award, Briefcase, GraduationCap, User } from 'lucide-react';

// ── Helpers to extract metadata from raw chunk text when backend metadata is empty ──
function extractNameFromText(text: string): string {
  const lines = text.split('\n').map(l => l.trim()).filter(Boolean);
  for (const line of lines.slice(0, 6)) {
    if (line.length < 4 || line.length > 60) continue;
    const words = line.split(/\s+/);
    if (words.length >= 2 && words.length <= 4 && words.every(w => /^[A-Z][a-zA-Z'-]*$/.test(w))) {
      const skip = ['Resume', 'Curriculum', 'Vitae', 'Summary', 'Profile', 'Experience', 'Education', 'Skills'];
      if (!words.some(w => skip.includes(w))) return line;
    }
  }
  return '';
}

function extractRoleFromText(text: string): string {
  const rolePattern = /(?:Senior|Lead|Principal|Junior|Staff|Mid-Level)?\s*(?:Software|Data|ML|AI|Cloud|DevOps|Full[- ]?Stack|Frontend|Backend|Python|Java|React)\s*(?:Engineer|Developer|Architect|Scientist|Analyst|Manager)/gi;
  const match = text.match(rolePattern);
  return match ? match[0].trim() : '';
}

function extractSkillsFromText(text: string): string[] {
  const known = [
    'Python','Java','JavaScript','TypeScript','Go','Rust','C++','C#','Ruby',
    'React','Angular','Vue','Node.js','Django','Flask','FastAPI','Spring',
    'AWS','Azure','GCP','Docker','Kubernetes','Terraform','CI/CD',
    'SQL','PostgreSQL','MySQL','MongoDB','Redis','Elasticsearch','Snowflake',
    'Spark','Airflow','Kafka','dbt','Databricks',
    'Machine Learning','Deep Learning','NLP','Computer Vision',
    'TensorFlow','PyTorch','Scikit-learn','Pandas','NumPy',
    'Git','Linux','REST API','GraphQL','Microservices','ETL',
    'Tableau','Power BI','Agile','Scrum','Selenium','Testing',
  ];
  const lower = text.toLowerCase();
  return known.filter(s => lower.includes(s.toLowerCase()));
}

function extractExperienceFromText(text: string): number {
  const patterns = [
    /(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience/gi,
    /experience\s*[:\-]\s*(\d+)\+?\s*(?:years?|yrs?)/gi,
  ];
  let max = 0;
  for (const p of patterns) {
    const matches = [...text.matchAll(p)];
    for (const m of matches) {
      const y = parseInt(m[1]);
      if (y > 0 && y < 50) max = Math.max(max, y);
    }
  }
  return max;
}

function extractEducationFromText(text: string): string {
  if (/Ph\.?D\.?|Doctor(?:ate)?/i.test(text)) return 'PhD';
  if (/Master(?:'s)?|M\.?S\.?|M\.?Sc\.?|MBA|M\.?Tech/i.test(text)) return "Master's";
  if (/Bachelor(?:'s)?|B\.?S\.?|B\.?Sc\.?|B\.?Tech|B\.?E\./i.test(text)) return "Bachelor's";
  return '';
}

function getScoreColor(score: number): string {
  if (score >= 50) return 'var(--color-success)';
  if (score >= 25) return 'var(--color-warning)';
  return 'var(--color-text-muted)';
}

export default function SearchView() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [aiInsights, setAiInsights] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [expandedCard, setExpandedCard] = useState<string | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError('');
    try {
      const data = await searchCandidates(query, 8);
      setResults(data.results || []);
      setAiInsights({
        optimized_query: data.optimized_query,
        expanded_query: data.expanded_query,
        intent: data.intent
      });
    } catch (err) {
      setError('Search failed. Please ensure the backend is running.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animate-fade-in">
      <div style={{ marginBottom: '32px' }}>
        <h1 className="text-gradient" style={{ fontSize: '2.5rem', marginBottom: '8px' }}>Smart Retrieval</h1>
        <p style={{ color: 'var(--color-text-muted)', fontSize: '1.125rem' }}>
          Semantic search across your entire talent pool with AI intent expansion.
        </p>
      </div>

      <form onSubmit={handleSearch} className="glass-panel" style={{ padding: '24px', marginBottom: '32px' }}>
        <div style={{ display: 'flex', gap: '16px' }}>
          <div style={{ flex: 1, position: 'relative' }}>
            <Search style={{ position: 'absolute', left: '16px', top: '14px', color: 'var(--color-text-muted)' }} size={20} />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Describe the ideal candidate (e.g., 'Senior Frontend Engineer with 5+ years React')..."
              style={{ width: '100%', paddingLeft: '48px', fontSize: '1rem' }}
            />
          </div>
          <button type="submit" className="btn-primary" disabled={loading} style={{ minWidth: '120px' }}>
            {loading ? <div className="spinner" style={{ margin: '0 auto' }}></div> : 'Search Pool'}
          </button>
        </div>
      </form>

      {error && (
        <div className="glass-panel" style={{ padding: '16px', borderColor: 'var(--color-danger)', color: 'var(--color-danger)', marginBottom: '24px' }}>
          {error}
        </div>
      )}

      {aiInsights && (
        <div className="glass-panel" style={{ padding: '20px', marginBottom: '32px', borderLeft: '4px solid var(--color-accent)' }}>
          <div className="flex-center" style={{ justifyContent: 'flex-start', gap: '8px', marginBottom: '12px' }}>
            <Star size={18} color="var(--color-accent)" />
            <h3 style={{ fontSize: '1rem' }}>AI Query Expansion Insights</h3>
          </div>
          <p style={{ color: 'var(--color-text-muted)', fontSize: '0.875rem', marginBottom: '8px' }}>
            <strong style={{ color: 'var(--color-text-main)' }}>Optimized:</strong> {aiInsights.optimized_query}
          </p>
          {aiInsights.expanded_query && (
            <p style={{ color: 'var(--color-text-muted)', fontSize: '0.875rem' }}>
              <strong style={{ color: 'var(--color-text-main)' }}>Expanded Entities:</strong> {aiInsights.expanded_query}
            </p>
          )}
          {aiInsights.intent?.skills?.length > 0 && (
            <div style={{ marginTop: '8px' }}>
              <strong style={{ color: 'var(--color-text-main)', fontSize: '0.875rem' }}>Detected Skills: </strong>
              {aiInsights.intent.skills.map((s: string) => (
                <span key={s} className="badge" style={{ marginRight: '6px' }}>{s}</span>
              ))}
            </div>
          )}
        </div>
      )}

      <div>
        {results.length === 0 && aiInsights ? (
          <div className="glass-panel" style={{ padding: '40px', textAlign: 'center' }}>
            <p style={{ color: 'var(--color-warning)' }}>No candidates match this precise criteria.</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {results.map((result, idx) => {
              const rawMeta = result.metadata || {};
              const text = result.text || '';

              // Enrich missing metadata from chunk text
              const candidateName = rawMeta.candidate_name || extractNameFromText(text) || rawMeta.filename?.replace(/\.pdf$/i,'') || `Candidate ${idx + 1}`;
              const jobRole = rawMeta.job_role || extractRoleFromText(text);
              const skills: string[] = rawMeta.skills?.length ? rawMeta.skills : extractSkillsFromText(text);
              const yearsExp = rawMeta.years_of_experience || extractExperienceFromText(text);
              const education = rawMeta.education || extractEducationFromText(text);
              const filename = rawMeta.filename || rawMeta.source?.split('/').pop() || '';

              // Score: convert rrank_score (0–1) to a 0–100 percentage
              const rawScore = result.rrank_score ?? result.rrf_score ?? 0;
              const displayScore = (rawScore * 1000).toFixed(1);
              const scoreColor = getScoreColor(parseFloat(displayScore));

              const isExpanded = expandedCard === String(result.id);

              return (
                <div key={`${result.id}-${idx}`} className="glass-panel card">
                  <div className="flex-between" style={{ alignItems: 'flex-start' }}>
                    <div style={{ flex: 1 }}>
                      {/* Candidate Name */}
                      <div className="flex-center" style={{ justifyContent: 'flex-start', gap: '8px', marginBottom: '4px' }}>
                        <User size={18} color="var(--color-primary)" />
                        <h3 style={{ fontSize: '1.25rem', color: 'var(--color-primary)' }}>
                          {candidateName}
                        </h3>
                      </div>

                      {/* Role */}
                      {jobRole && (
                        <p style={{ color: 'var(--color-accent)', fontSize: '0.9rem', marginBottom: '8px', marginLeft: '26px' }}>
                          {jobRole}
                        </p>
                      )}

                      {/* Stats row */}
                      <div className="flex-center" style={{ justifyContent: 'flex-start', gap: '20px', color: 'var(--color-text-muted)', fontSize: '0.875rem', marginTop: '8px' }}>
                        {yearsExp > 0 && (
                          <span className="flex-center" style={{ gap: '4px' }}>
                            <Award size={14} /> {yearsExp} Yrs Exp
                          </span>
                        )}
                        {education && (
                          <span className="flex-center" style={{ gap: '4px' }}>
                            <GraduationCap size={14} /> {education}
                          </span>
                        )}
                        {filename && (
                          <span className="flex-center" style={{ gap: '4px' }}>
                            <Briefcase size={14} /> {filename}
                          </span>
                        )}
                        <span className="flex-center" style={{ gap: '4px' }}>
                          <Star size={14} /> {result.source === 'bm25' ? 'Keyword' : 'Semantic'} match
                        </span>
                      </div>
                    </div>

                    {/* Score badge */}
                    <div style={{ textAlign: 'center', minWidth: '80px' }}>
                      <div style={{ fontSize: '1.75rem', fontWeight: 700, color: scoreColor, lineHeight: 1 }}>
                        {displayScore}
                      </div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', marginTop: '2px' }}>Match Score</div>
                    </div>
                  </div>

                  {/* Skills */}
                  {skills.length > 0 && (
                    <div style={{ marginTop: '16px', display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {skills.slice(0, 10).map((s: string) => (
                        <span key={s} className="badge">{s}</span>
                      ))}
                      {skills.length > 10 && (
                        <span style={{ color: 'var(--color-text-muted)', fontSize: '0.8rem', alignSelf: 'center' }}>
                          +{skills.length - 10} more
                        </span>
                      )}
                    </div>
                  )}

                  {/* Expand/Collapse */}
                  <div style={{ marginTop: '16px', borderTop: '1px solid var(--color-border)', paddingTop: '16px' }}>
                    <button
                      onClick={() => setExpandedCard(isExpanded ? null : String(result.id))}
                      className="flex-center"
                      style={{ gap: '8px', color: 'var(--color-primary)', fontSize: '0.875rem', fontWeight: 600, width: '100%', justifyContent: 'center' }}
                    >
                      {isExpanded ? 'Hide Excerpt' : 'View Resume Excerpt'}
                      {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </button>

                    {isExpanded && (
                      <div className="animate-fade-in" style={{ marginTop: '16px', padding: '16px', background: 'rgba(0,0,0,0.2)', borderRadius: 'var(--radius-sm)', fontSize: '0.875rem', lineHeight: 1.6, whiteSpace: 'pre-wrap', maxHeight: '300px', overflowY: 'auto' }}>
                        {text || 'No excerpt available.'}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
