import React, { useEffect, useState } from 'react';
import ChatWindow from './components/ChatWindow';
import { Shield, CheckCircle2, LogOut, Trash2, Loader2 } from 'lucide-react'
import api from './utils/api.util';


function App() {
  const [docs, setDocs] = useState([]);
  const [user] = useState({ username: "anonymous", department: "general" })
  const [deletingDocName, setDeletingDocName] = useState(null);
  const [docActionMessage, setDocActionMessage] = useState('');

  const fetchDocs = async () => {
    try {
      const docs = await api.get("/retriveAllDocuments");
      setDocs(docs.data.files);

    } catch (err) {
      alert(err);
    }

  }

  const handleDeleteDocument = async (sourceName) => {
    if (!sourceName || deletingDocName) return;
    if (!window.confirm(`Delete document "${sourceName}"?`)) return;

    try {
      setDeletingDocName(sourceName);
      setDocActionMessage('');
      const res = await api.delete(`/deleteDocument/${encodeURIComponent(sourceName)}`);
      const message = res?.data?.message || 'Document deleted successfully.';
      setDocActionMessage(message);
      await fetchDocs();
    } catch (err) {
      console.error('Failed to delete document', err);
      setDocActionMessage('Failed to delete document.');
    } finally {
      setDeletingDocName(null);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, [user])

  return (
    <div className="flex h-screen bg-[#0f172a] text-slate-200 font-sans">
      {/* 1. SIDEBAR */}
      <aside className="w-72 bg-[#1e293b] border-r border-slate-700 flex flex-col">
        <div className="p-6 border-b border-slate-700 flex items-center gap-3">
          <div className="bg-blue-600 p-2 rounded-lg"><Shield size={20} /></div>
          <div>
            <h1 className="font-bold text-sm tracking-tight">DEEPCONTEXT</h1>
            <p className="text-[10px] text-slate-400 uppercase tracking-widest">KNOWLEDGE BASE NODE</p>
          </div>
        </div>

    

        <div className="flex-1 overflow-y-auto p-4">
          <h2 className="text-[10px] font-semibold text-slate-500 mb-4 uppercase">Knowledge Base</h2>
          {docActionMessage && (
            <p className="mb-3 text-[11px] text-slate-400">{docActionMessage}</p>
          )}
          <div className="space-y-2">
            {(!docs || docs.length === 0) && (
              <div className="rounded-xl border border-dashed border-slate-700 p-4 text-xs text-slate-500">
                No documents available.
              </div>
            )}
            {docs?.map((doc, i) => (
              <div key={i} className="p-3 rounded-xl border transition-all bg-slate-800/50 border-slate-700">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium truncate w-40">{doc.name}</span>
                  <div className="flex items-center gap-2">
                    <CheckCircle2 size={14} className="text-emerald-400" />
                    <button
                      type="button"
                      onClick={() => handleDeleteDocument(doc.name)}
                      disabled={deletingDocName === doc.name}
                      className="text-slate-500 hover:text-rose-400 disabled:cursor-not-allowed disabled:text-slate-600 transition"
                      aria-label={`Delete ${doc.name}`}
                      title={`Delete ${doc.name}`}
                    >
                      {deletingDocName === doc.name ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
                    </button>
                  </div>
                </div>
                <div className="text-[10px] text-slate-500 flex justify-between">
                  <span>{doc.status}</span>
                  <span>{doc.time ? doc.time.split(' ')[0] : 'N/A'}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <button onClick={() => window.location.reload()} className="p-4 border-t border-slate-700 flex items-center gap-2 text-slate-400 hover:text-white transition">
          <LogOut size={16} /> <span className="text-xs">Refresh</span>
        </button>
      </aside>

      {/* 2. MAIN CHAT */}
      <main className="flex-1 flex flex-col relative bg-gradient-to-b from-[#0f172a] to-[#1e293b]">
        <ChatWindow user={user} />
      </main>
    </div>
  );
}

export default App;
