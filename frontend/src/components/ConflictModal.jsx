import {AlertCircle} from 'lucide-react'

export default function ConflictModal({ isOpen, onClose, conflictReason }) {
    if (!isOpen) return null;
  
    return (
      <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-[100] p-4">
        <div className="bg-[#1e293b] border border-red-500/50 max-w-lg w-full rounded-2xl p-6 shadow-2xl">
          <div className="flex items-center gap-3 text-red-400 mb-4">
            <AlertCircle size={24} />
            <h2 className="text-xl font-bold">Integrity Conflict Detected</h2>
          </div>
          <p className="text-slate-300 text-sm leading-relaxed mb-6 italic">
            "{conflictReason}"
          </p>
          <button 
            onClick={onClose}
            className="w-full bg-red-500/20 hover:bg-red-500/30 text-red-400 font-semibold py-2 rounded-xl border border-red-500/50 transition-all"
          >
            Acknowledge Risk
          </button>
        </div>
      </div>
    );
  }