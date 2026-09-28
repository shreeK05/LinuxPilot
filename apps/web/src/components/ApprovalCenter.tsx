import { useState } from 'react';
import type { FC } from 'react';
import { fetchWithAuth } from '../utils/api';
import { ShieldAlert, AlertTriangle, Check, X } from 'lucide-react';
import { cn } from '../utils/cn';

interface ApprovalCenterProps {
  taskId: string;
  apiUrl: string;
  onDecided: () => void;
}

export const ApprovalCenter: FC<ApprovalCenterProps> = ({ taskId, apiUrl, onDecided }) => {
  const [submitting, setSubmitting] = useState(false);
  const [reason, setReason] = useState("");

  const handleDecision = (approved: boolean) => {
    setSubmitting(true);
    fetchWithAuth(`${apiUrl}/tasks/${taskId}/approve?approved=${approved}&reason=${encodeURIComponent(reason)}`, {
      method: 'POST'
    })
      .then(res => {
          if (!res.ok) throw new Error("Approval request failed");
          return res.json();
      })
      .then(() => {
        setSubmitting(false);
        onDecided();
      })
      .catch(err => {
        console.error(err);
        setSubmitting(false);
      });
  };

  return (
    <div className="w-full">
      <div className="bg-surface-800 border-2 border-warning-500/50 rounded-2xl overflow-hidden shadow-2xl relative">
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-warning-500 to-danger-500"></div>
        
        <div className="px-6 py-5 border-b border-white/5 flex items-center gap-3 bg-warning-500/10">
          <ShieldAlert size={24} className="text-warning-500 animate-pulse" />
          <h3 className="text-lg font-bold text-warning-500 tracking-wide">Approval Required</h3>
        </div>

        <div className="p-6 sm:p-8">
          <div className="flex gap-4 mb-8">
            <div className="mt-1 flex-shrink-0">
              <div className="w-10 h-10 rounded-full bg-warning-500/20 border border-warning-500/30 flex items-center justify-center text-warning-400">
                <AlertTriangle size={20} />
              </div>
            </div>
            <div>
              <h4 className="text-white font-medium text-lg mb-2">LinuxPilot requests permission to proceed</h4>
              <p className="text-text-muted leading-relaxed">
                The current task involves potentially destructive actions or modifies system state outside the safe zone. Please review the execution plan in the Advanced Details before proceeding.
              </p>
            </div>
          </div>

          <div className="mb-8">
            <label className="block text-xs font-semibold text-text-muted mb-2 uppercase tracking-widest">Decision Reason (Optional)</label>
            <input
              type="text"
              value={reason}
              onChange={e => setReason(e.target.value)}
              className="w-full bg-surface-900 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-text-muted/50 focus:outline-none focus:border-warning-500/50 focus:ring-1 focus:ring-warning-500/50 transition-all"
              placeholder="e.g. Authorized for cleanup"
            />
          </div>

          <div className="flex flex-col sm:flex-row gap-3">
            <button
              onClick={() => handleDecision(true)}
              disabled={submitting}
              className={cn(
                "flex-1 flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-semibold transition-all",
                submitting ? "opacity-50 cursor-not-allowed bg-surface-700 text-text-muted" : "bg-danger-500 hover:bg-danger-600 text-white shadow-[0_0_15px_rgba(239,68,68,0.3)] hover:shadow-[0_0_20px_rgba(239,68,68,0.5)]"
              )}
            >
              <Check size={18} />
              Approve Action
            </button>
            <button
              onClick={() => handleDecision(false)}
              disabled={submitting}
              className={cn(
                "flex-1 flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-semibold transition-all border",
                submitting ? "opacity-50 cursor-not-allowed bg-surface-800 border-white/5 text-text-muted" : "bg-surface-800 hover:bg-surface-700 border-white/10 text-white hover:border-white/20"
              )}
            >
              <X size={18} />
              Reject Action
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
