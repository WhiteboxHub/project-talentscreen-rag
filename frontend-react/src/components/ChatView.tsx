import { useState, useRef, useEffect } from 'react';
import { BACKEND_URL } from '../api';
import { Send, Bot, User } from 'lucide-react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export default function ChatView() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [sessionId] = useState(() => crypto.randomUUID());
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsTyping(true);

    try {
      const response = await fetch(`${BACKEND_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: userMessage, session_id: sessionId })
      });

      if (!response.body) throw new Error('No response body');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantMessage = '';

      setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value);
        assistantMessage += chunk;
        
        setMessages(prev => {
          const newMessages = [...prev];
          newMessages[newMessages.length - 1].content = assistantMessage;
          return newMessages;
        });
      }
    } catch (err) {
      console.error('Chat error:', err);
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error connecting to the intelligence engine.' }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 64px)' }}>
      <div style={{ marginBottom: '24px' }}>
        <h1 className="text-gradient" style={{ fontSize: '2.5rem', marginBottom: '8px' }}>Talent Intelligence</h1>
        <p style={{ color: 'var(--color-text-muted)', fontSize: '1.125rem' }}>
          Converse with your AI recruitment assistant to analyze profiles or compare candidates.
        </p>
      </div>

      <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Chat History */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>
          {messages.length === 0 ? (
            <div className="flex-center" style={{ height: '100%', flexDirection: 'column', color: 'var(--color-text-muted)', gap: '16px' }}>
              <Bot size={48} opacity={0.5} />
              <p>Start by asking about a specific candidate, skill, or role requirements.</p>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div key={idx} style={{ display: 'flex', marginBottom: '16px', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
                {msg.role === 'assistant' && (
                  <div style={{ marginRight: '12px', marginTop: '4px' }}>
                    <div className="flex-center" style={{ width: '32px', height: '32px', borderRadius: '50%', background: 'rgba(45, 212, 191, 0.2)', color: 'var(--color-accent)' }}>
                      <Bot size={18} />
                    </div>
                  </div>
                )}
                
                <div className={`chat-message ${msg.role === 'user' ? 'chat-user' : 'chat-assistant'}`}>
                  {msg.content || <span style={{ opacity: 0.5 }}>Thinking...</span>}
                </div>
                
                {msg.role === 'user' && (
                  <div style={{ marginLeft: '12px', marginTop: '4px' }}>
                    <div className="flex-center" style={{ width: '32px', height: '32px', borderRadius: '50%', background: 'rgba(59, 130, 246, 0.2)', color: 'var(--color-primary)' }}>
                      <User size={18} />
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Chat Input */}
        <div style={{ padding: '20px', borderTop: '1px solid var(--color-border)', background: 'rgba(15, 23, 42, 0.5)' }}>
          <form onSubmit={handleSend} style={{ display: 'flex', gap: '12px' }}>
            <input 
              type="text" 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask me to compare the top 3 Python developers..."
              style={{ flex: 1 }}
              disabled={isTyping}
            />
            <button type="submit" className="btn-primary flex-center" disabled={!input.trim() || isTyping} style={{ padding: '0 24px' }}>
              <Send size={18} />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
