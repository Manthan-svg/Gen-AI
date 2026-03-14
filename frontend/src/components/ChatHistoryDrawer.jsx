import React, { useEffect, useMemo, useState } from 'react';
import { Clock, MessageSquarePlus, X } from 'lucide-react';
import api from '../utils/api.util';
import { ensureInitialChatSession, getChatSessions } from '../utils/chatSessions.util';

function formatTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleString(undefined, {
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function ChatHistoryDrawer({
  user,
  activeSessionId,
  sessionsVersion,
  onSelectSession,
  onNewChat,
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('');

  const username = user?.username ?? null;

  const sortedSessions = useMemo(() => {
    const arr = Array.isArray(sessions) ? [...sessions] : [];
    arr.sort((a, b) => {
      const at = a?.lastMessageAt || a?.createdAt || '';
      const bt = b?.lastMessageAt || b?.createdAt || '';
      return bt.localeCompare(at);
    });
    return arr;
  }, [sessions]);

  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (e) => {
      if (e.key === 'Escape') setIsOpen(false);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [isOpen]);

  useEffect(() => {
    if (!username) return;
    // Ensure there's at least one session (legacy) so the list isn't empty.
    ensureInitialChatSession(username);
    setSessions(getChatSessions(username));
  }, [username, sessionsVersion, isOpen]);

  const pollJobStatus = async (jobId) => {
    const maxAttempts = 300;
    const delay = (ms) => new Promise((r) => setTimeout(r, ms));

    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      try {
        const res = await api.get(`/job-status/${jobId}`);
        const status = res.data?.status;

        console.log(`Polling Job ${jobId}: ${status}`);
        if (status === 'completed') {
          setUploadStatus('File processed successfully.');
          return;
        }
        if (status === 'failed' || status === 'not_found') {
          setUploadStatus('File processing failed.');
          return;
        }
      } catch {
        setUploadStatus('Error while checking job status.');
        return;
      }
      await delay(2000);
    }
    setUploadStatus('Processing is taking longer than expected. Please try again later.');
  };

  const handleUpload = async (file) => {
    if (!file || uploading) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      setUploading(true);
      setUploadStatus('Uploading file...');

      const res = await api.post('/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      const jobId = res.data?.job_id;
      if (jobId) {
        setUploadStatus('Upload successful. Auditing file...');
        await pollJobStatus(jobId);
      } else {
        setUploadStatus('Upload successful.');
      }
    } catch (err) {
      console.error('Upload failed', err);
      setUploadStatus('Upload failed.');
    } finally {
      setUploading(false);
      window.location.href = "/app";
    }
  };

  const deleteChatFunction = async (sessionId) => {
    if (!window.confirm('Delete this chat?')) return;
    try {
      const response = await api.post(`/delete-chat/${sessionId}`);

      // Remove the deleted chat from local storage (chatSessions)
      const username = user?.username ?? null;

      if (username && sessionId) {
        // Remove the session from user's sessions
        const key = `dc_chat_sessions_${username}`;
        const sessions = JSON.parse(localStorage.getItem(key) ?? '[]');
        const filtered = sessions.filter(s => s.sessionId !== sessionId);
        localStorage.setItem(key, JSON.stringify(filtered));

        // If the deleted chat was active, clear the activeSessionId
        const activeSessionKey = `dc_active_chat_${username}`;
        if (localStorage.getItem(activeSessionKey) === sessionId) {
          localStorage.removeItem(activeSessionKey);
        }
      }
      setSessions(getChatSessions(username));
    } catch (err) {
      console.log(err);
      alert('Failed to delete chat.');
    }
  }

  return (
    <div className="w-full flex justify-end gap-2 mb-3">
      <button
        type="button"
        onClick={() => typeof onNewChat === 'function' && onNewChat()}
        className="inline-flex items-center gap-2 text-xs text-slate-300 hover:text-white bg-slate-800/60 hover:bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 transition"
      >
        <MessageSquarePlus size={14} />
        New Chat
      </button>

      <button
        type="button"
        onClick={() => setIsOpen(true)}
        className="inline-flex items-center gap-2 text-xs text-slate-300 hover:text-white bg-slate-800/60 hover:bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 transition"
      >
        <Clock size={14} />
        Chat History
      </button>

      <label className="inline-flex items-center gap-2 text-xs text-slate-300 hover:text-white bg-slate-800/60 hover:bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 transition cursor-pointer">
        <input
          type="file"
          className="hidden"
          onChange={async (e) => {
            const file = e.target.files?.[0];
            if (!file) return;
            await handleUpload(file);
            // allow selecting the same file again
            e.target.value = '';
          }}
          disabled={uploading}
        />
        <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 16v-7m0 0l-3.5 3.5M12 9l3.5 3.5M19 16V7a2 2 0 00-2-2h-6a2 2 0 00-2 2v5.5" />
        </svg>
        {uploading ? 'Uploading...' : 'Upload'}
      </label>

      {uploadStatus && (
        <p className="ml-2 text-[10px] text-slate-400 max-w-xs truncate">
          {uploadStatus}
        </p>
      )}

      {isOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm flex justify-end z-[90]"
          onClick={() => setIsOpen(false)}
        >
          <div
            className="w-full max-w-md h-full bg-gradient-to-b from-[#0f172a] to-[#1e293b] border-l border-slate-700 p-4 flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between pb-3 border-b border-slate-700">
              <div className="flex items-center gap-2">
                <Clock size={16} className="text-slate-300" />
                <h2 className="text-sm font-semibold text-slate-100">
                  Chat History
                </h2>
              </div>
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                className="p-2 rounded-lg hover:bg-slate-800 transition text-slate-300 hover:text-white"
                aria-label="Close chat history"
              >
                <X size={16} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto pt-4 space-y-2 pr-1 custom-scrollbar">
              {sortedSessions.length === 0 && (
                <div className="text-xs text-slate-400 bg-slate-800/40 border border-slate-700 rounded-xl p-3">
                  No chats yet. Click “New Chat” to start one.
                </div>
              )}

              {sortedSessions.map((s) => {
                const isActive = s?.sessionId && s.sessionId === activeSessionId;
                const ts = s?.lastMessageAt || s?.createdAt || null;
                return (
                  <button
                    key={s?.sessionId}
                    type="button"
                    onClick={() => {
                      if (typeof onSelectSession === 'function' && s?.sessionId) {
                        onSelectSession(s.sessionId);
                      }
                      setIsOpen(false);
                    }}
                    className={`w-full text-left rounded-xl border transition p-3 ${isActive
                      ? 'border-blue-500/50 bg-blue-500/10'
                      : 'border-slate-700 bg-slate-900/20 hover:bg-slate-800/60'
                      }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-xs font-semibold text-slate-100 truncate">
                          {String(s?.title ?? 'Chat')}
                        </p>
                        <p className="text-[11px] text-slate-400 truncate mt-1">
                          {String(s?.lastMessagePreview ?? '') || 'No messages yet'}
                        </p>
                      </div>
                      <div className="flex flex-col items-end gap-1 min-w-[46px]">
                        <div className="text-[10px] text-slate-500 text-right">
                          {formatTime(ts)}
                        </div>
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            className="w-4 h-4 text-red-700 hover:text-red-900 cursor-pointer transition"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            onClick={()=>deleteChatFunction(s.sessionId)}
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                            />
                          </svg>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>

            <div className="pt-3 border-t border-slate-700">
              <p className="text-[10px] text-slate-500">
                Tip: Each row is a separate chat, like WhatsApp.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
