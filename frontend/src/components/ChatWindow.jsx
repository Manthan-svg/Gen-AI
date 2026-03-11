import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Loader2 } from 'lucide-react';
import api from '../utils/api.util';
import ChatHistoryDrawer from './ChatHistoryDrawer';
import {
  createNewChatSession,
  ensureInitialChatSession,
  maybeSetChatTitleFromFirstMessage,
  setActiveChatSessionId,
  touchChatSession,
} from '../utils/chatSessions.util';

function normalizeHistoryPayload(payload) {
  const raw = payload?.['chat-history'];
  if (!Array.isArray(raw)) return [];

  return raw
    .map((item) => {
      if (Array.isArray(item) && item.length >= 2) {
        return { 
          role: item[0], 
          content: item[1],
          // Check if your backend is sending sources as the 3rd element
          sources: item[2] || [] 
        };
      }
      return null;
    })
    .filter(Boolean);
}

export default function ChatWindow({ user }) {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState("");
    const [isTyping, setIsTyping] = useState(false);
    const [activeSessionId, setActiveSessionIdState] = useState(null);
    const [sessionsVersion, setSessionsVersion] = useState(0);

    const username = user?.username ?? null;

    const effectiveSessionId = useMemo(() => activeSessionId, [activeSessionId]);

    const loadSession = useCallback(
      async (sessionId) => {
        if (!username || !sessionId) return;
        setActiveChatSessionId(username, sessionId);
        setActiveSessionIdState(sessionId);
        setIsTyping(false);
        setInput('');

        try {
          const res = await api.post(`/get-history/${sessionId}`);
          const normalized = normalizeHistoryPayload(res?.data);
          setMessages(
            normalized.map((m) => ({
              role: m.role,
              content: m.content,
              sources:m.sources
            }))
          );
        } catch {
          setMessages([]);
        }
      },
      [username]
    );

    useEffect(() => {
      if (!username) return;
      const { activeSessionId: initialActive } = ensureInitialChatSession(username);
      if (initialActive) loadSession(initialActive);
    }, [username, loadSession]);

    const startNewChat = useCallback(() => {
      if (!username) return;
      const newSession = createNewChatSession(username);
      setSessionsVersion((v) => v + 1);
      setMessages([]);
      setInput('');
      setIsTyping(false);
      if (newSession?.sessionId) {
        setActiveSessionIdState(newSession.sessionId);
      }
    }, [username]);
  
    const sendMessage = async () => {
      const text = input.trim();
      if (!text) return;
      if (!username || !effectiveSessionId) return;

      const userMsg = { role: 'human', content: text };
      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      setIsTyping(true);

      maybeSetChatTitleFromFirstMessage(username, effectiveSessionId, text);
      touchChatSession(username, effectiveSessionId, {
        lastMessageAt: new Date().toISOString(),
        lastMessagePreview: text,
      });
      setSessionsVersion((v) => v + 1);
  
      try {
        console.log(effectiveSessionId);

        const res = await api.post('/get-answer', { 
          question: text, 
          sessionId: effectiveSessionId,
        });
        
        setMessages(prev => [...prev, {
          role: 'ai',
          content: res.data.answer,
          sources: res.data.sources
        }]);

        touchChatSession(username, effectiveSessionId, {
          lastMessageAt: new Date().toISOString(),
          lastMessagePreview: String(res?.data?.answer ?? '').trim() || text,
        });
        setSessionsVersion((v) => v + 1);
      } catch (err) { /* Handle Error */ }
      setIsTyping(false);
    };
  
    return (
      <div className="flex-1 flex flex-col p-6 min-h-100  mx-auto w-full">
        {/* Chat History Drawer Trigger & Drawer */}
        <ChatHistoryDrawer
          user={user}
          activeSessionId={effectiveSessionId}
          sessionsVersion={sessionsVersion}
          onNewChat={startNewChat}
          onSelectSession={(sessionId) => loadSession(sessionId)}
          
        />

        <div className="messagesBox flex-1 overflow-y-auto space-y-6 mb-4 pr-4 custom-scrollbar">
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'human' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] rounded-2xl p-4 ${m.role === 'human' ? 'bg-blue-600 text-white' : 'bg-slate-800 border border-slate-700 text-slate-200'}`}>
                <p className="text-sm leading-relaxed">{m.content}</p>
                
                {m.sources && m.sources.length > 0 && (
                  <div className="mt-4 pt-3 border-t border-slate-700 flex flex-wrap gap-2">
                    {m.sources.map((s, idx) => (
                      <div key={idx} className="group relative">
                          <span className="text-[10px] bg-slate-900 px-2 py-1 rounded border border-slate-600 cursor-help">
                            📄 {s.source} (p. {s.page})
                          </span>
                          {/* Hover Tooltip for Content Preview */}
                          <div className="absolute bottom-full mb-2 hidden group-hover:block w-64 p-2 bg-black text-[10px] rounded shadow-xl border border-slate-700 z-50">
                            {s.content_preview}
                          </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          {isTyping && <Loader2 className="animate-spin text-blue-500" />}
        </div>
  
        <div className="relative">
          <input 
            value={input} 
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="Ask your knowledge base..."
            className="w-full bg-slate-800 border border-slate-700 rounded-xl py-4 px-6 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all text-sm"
          />
        </div>
      </div>
    );
  }