import { useState } from 'react';
import type { FC } from 'react';
import { fetchWithAuth } from '../utils/api';
import { ShieldAlert } from 'lucide-react';
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
    <div className="w-full max-w-2xl mx-auto mt-6 animation-fade-in">
      <div className="bg-white border-2 border-amber-400 rounded-2xl overflow-hidden shadow-lg">
        <div className="bg-amber-400 px-6 py-4 flex items-center gap-3">
          <ShieldAlert size={24} className="text-amber-900" />
          <h3 className="text-lg font-bold text-amber-900">Approval Required</h3>
        </div>

        <div className="p-6">
          <p className="text-slate-700 font-medium mb-6 text-lg">
            LinuxPilot needs your permission to proceed with potentially destructive actions.
          </p>

          <div className="mb-6">
            <label className="block text-sm font-semibold text-slate-700 mb-2 uppercase tracking-wide">Provide a reason (Optional)</label>
            <input
              type="text"
              value={reason}
              onChange={e => setReason(e.target.value)}
              className="w-full bg-slate-50 border border-slate-300 rounded-xl px-4 py-3 text-slate-900 focus:outline-none focus:ring-2 focus:ring-amber-500 transition-shadow"
              placeholder="E.g., Authorized for cleanup"
            />
          </div>

          <div className="flex flex-col sm:flex-row gap-3">
            <button
              onClick={() => handleDecision(true)}
              disabled={submitting}
              className="flex-1 bg-red-600 hover:bg-red-700 text-white px-6 py-3 rounded-xl font-semibold transition-colors disabled:opacity-50 text-center"
            >
              Approve Destructive Action
            </button>
            <button
              onClick={() => handleDecision(false)}
              disabled={submitting}
              className="flex-1 bg-slate-100 hover:bg-slate-200 text-slate-800 px-6 py-3 rounded-xl font-semibold transition-colors disabled:opacity-50 text-center border border-slate-200"
            >
              Reject Action
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
