import React, { useEffect, useState } from 'react';
import ChatWindow from './components/ChatWindow';
import { Shield, Database, MessageSquare, AlertCircle, CheckCircle2, Loader2, LogOut, Clock } from 'lucide-react'
import api from './utils/api.util';
import ConflictModal from './components/ConflictModal';


function App() {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [user, setUser] = useState(JSON.parse(localStorage.getItem("user-info")))
  const [isConflictModalOpen, setConflictModal] = useState(false);
  const [conflictReason, setConflictReason] = useState("");

  const fetchDocs = async () => {
    try {
      const docs = await api.get("/retriveAllDocuments");
      setDocs(docs.data.files);

    } catch (err) {
      alert(err);
    }

  }

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
            <p className="text-[10px] text-slate-400 uppercase tracking-widest">{user.department} NODE</p>
          </div>
        </div>

    

        <div className="flex-1 overflow-y-auto p-4">
          <h2 className="text-[10px] font-semibold text-slate-500 mb-4 uppercase">Knowledge Base</h2>
          <div className="space-y-2">
            {docs?.map((doc, i) => (
              <div key={i} className={`p-3 rounded-xl border transition-all ${doc.status === 'conflict' ? 'bg-red-500/10 border-red-500/50' : 'bg-slate-800/50 border-slate-700'}`}>
                <div
                  onClick={() => {
                    if (doc.status === 'conflict') {
                      setConflictModal(true);
                      setConflictReason(doc.conflict_reason);
                    }
                  }}
                  className="flex items-center justify-between mb-1"
                >
                  <span className="text-xs font-medium truncate w-40">{doc.name}</span>
                  {doc.status === 'conflict' ? <AlertCircle size={14} className="text-red-400" /> : <CheckCircle2 size={14} className="text-emerald-400" />}
                </div>
                <div className="text-[10px] text-slate-500 flex justify-between">
                  <span>{doc.status}</span>
                  <span>{doc.time.split(' ')[0]}</span>
                </div>
              </div>
            ))}
          </div>
          {/* Show ConflictModal when isConflictModal is true */}
          {isConflictModalOpen && (
            <ConflictModal
              isOpen={isConflictModalOpen}
              onClose={() => setConflictModal(false)}
              conflictReason={conflictReason}
            />
          )}
        </div>

        <button onClick={() => { localStorage.clear(); window.location.reload(); }} className="p-4 border-t border-slate-700 flex items-center gap-2 text-slate-400 hover:text-white transition">
          <LogOut size={16} /> <span className="text-xs">Secure Sign Out</span>
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