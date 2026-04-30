import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Loader2, SendHorizontal } from 'lucide-react';
import api from '../utils/api.util';
import ChatHistoryDrawer from './ChatHistoryDrawer';
import MarkdownRenderer from './MarkdownRenderer';
import {
  createNewChatSession,
  ensureInitialChatSession,
  maybeSetChatTitleFromFirstMessage,
  touchChatSession,
} from '../utils/chatSessions.util';

function normalizeHistoryPayload(payload) {
  const raw = payload?.['chat-history'];
  if (!Array.isArray(raw)) return [];

  return raw
    .map((item) => {
      if (item && typeof item === 'object' && !Array.isArray(item)) {
        return {
          role: item.role,
          content: item.content,
          diagrams:Array.isArray(item.diagrams) ? item.diagrams : [],
        };
      }
      if (Array.isArray(item) && item.length >= 2) {
        const diagramsFromTuple = Array.isArray(item[3])
          ? item[3]
          : (Array.isArray(item[2]) ? item[2] : []);
        return { 
          role: item[0], 
          content: item[1],
          diagrams: diagramsFromTuple,
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
    const messagesContainerRef = useRef(null);
    const messagesEndRef = useRef(null);
    const shouldAutoScrollRef = useRef(true);
    const forceAutoScrollRef = useRef(false);


    const username = user?.username ?? null;

    const effectiveSessionId = useMemo(() => activeSessionId, [activeSessionId]);

    const scrollToBottom = useCallback((behavior = 'smooth') => {
      messagesEndRef.current?.scrollIntoView({ behavior, block: 'end' });
    }, []);

    const loadSession = useCallback(
      async (sessionId) => {
        if (!username || !sessionId) return;
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
              diagrams: Array.isArray(m.diagrams) ? m.diagrams : [],
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
      (async () => {
        const { activeSessionId: initialActive } = await ensureInitialChatSession(username);
        if (initialActive) {
          await loadSession(initialActive);
        }
      })();
    }, [username, loadSession]);

    useEffect(() => {
      const container = messagesContainerRef.current;
      if (!container) return;

      const handleScroll = () => {
        const distanceFromBottom =
          container.scrollHeight - container.scrollTop - container.clientHeight;
        shouldAutoScrollRef.current = distanceFromBottom < 80;
      };

      handleScroll();
      container.addEventListener('scroll', handleScroll);
      return () => container.removeEventListener('scroll', handleScroll);
    }, []);

    useEffect(() => {
      if (!forceAutoScrollRef.current && !shouldAutoScrollRef.current) return;

      requestAnimationFrame(() => {
        scrollToBottom('smooth');
        requestAnimationFrame(() => {
          scrollToBottom('smooth');
          forceAutoScrollRef.current = false;
        });
      });
    }, [messages, isTyping, scrollToBottom]);

    useEffect(() => {
      const container = messagesContainerRef.current;
      if (!container || typeof ResizeObserver === 'undefined') return;

      const observer = new ResizeObserver(() => {
        if (!forceAutoScrollRef.current && !shouldAutoScrollRef.current) return;
        scrollToBottom('auto');
      });

      observer.observe(container);
      return () => observer.disconnect();
    }, [scrollToBottom]);

    const startNewChat = useCallback(() => {
      if (!username) return;
      (async () => {
        const newSession = await createNewChatSession(username);
        setSessionsVersion((v) => v + 1);
        setMessages([]);
        setInput('');
        setIsTyping(false);
        if (newSession?.sessionId) {
          setActiveSessionIdState(newSession.sessionId);
        }
      })();
    }, [username]);
  
    const sendMessage = async () => {
      const text = input.trim();
      if (!text || isTyping) return;
      if (!username || !effectiveSessionId) return;

      forceAutoScrollRef.current = true;
      const userMsg = { role: 'human', content: text };
      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      setIsTyping(true);

      try {
        await maybeSetChatTitleFromFirstMessage(effectiveSessionId, text);
        await touchChatSession(effectiveSessionId, {
          lastMessageAt: new Date().toISOString(),
          lastMessagePreview: text,
        });
        setSessionsVersion((v) => v + 1);

        const res = await api.post('/get-answer', { 
          question: text, 
          sessionId: effectiveSessionId,
        });
        console.log(res);

        const answer = String(res?.data?.answer ?? '').trim();
        const diagrams = Array.isArray(res?.data?.diagrams) ? res?.data?.diagrams : [];
        const content = answer || (diagrams.length > 0 ? '' : 'No response was generated.');
        const preview = answer || (diagrams.length > 0 ? 'Diagram response' : text);
        setMessages(prev => [...prev, {
          role: 'ai',
          content,
          diagrams
        }]);

        await touchChatSession(effectiveSessionId, {
          lastMessageAt: new Date().toISOString(),
          lastMessagePreview: preview,
        });
        setSessionsVersion((v) => v + 1);
      } catch (err) {
        setMessages((prev) => [
          ...prev,
          {
            role: 'ai',
            content: 'Something went wrong while fetching the answer.',
          },
        ]);
      }
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

        <div
          ref={messagesContainerRef}
          className="messagesBox flex-1 overflow-y-auto space-y-6 mb-4 pr-4 custom-scrollbar"
        >
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'human' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] overflow-hidden rounded-2xl p-4 ${m.role === 'human' ? 'bg-blue-600 text-white' : 'bg-slate-800 border border-slate-700 text-slate-200'}`}>
                {m.role === 'human' ? (
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">{m.content}</p>
                ) : (
                  <MarkdownRenderer content={m.content} diagrams={m.diagrams || []} />
                )}
              </div>
            </div>
          ))}
          {isTyping && <Loader2 className="animate-spin text-blue-500" />}
          <div ref={messagesEndRef} />
        </div>
  
        <div className="relative">
          <input 
            value={input} 
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="Ask your knowledge base..."
            className="w-full bg-slate-800 border border-slate-700 rounded-xl py-4 pl-6 pr-16 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all text-sm"
          />
          <button
            type="button"
            onClick={sendMessage}
            disabled={!input.trim() || isTyping}
            className="absolute right-2 top-1/2 -translate-y-1/2 inline-flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600 text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
            aria-label="Send message"
            title="Send message"
          >
            {isTyping ? <Loader2 size={16} className="animate-spin" /> : <SendHorizontal size={16} />}
          </button>
        </div>
      </div>
    );
  }
