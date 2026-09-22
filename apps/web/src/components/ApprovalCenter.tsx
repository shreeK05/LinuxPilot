import { useState } from 'react';
import type { FC } from 'react';

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
    fetch(`${apiUrl}/tasks/${taskId}/approve?approved=${approved}&reason=${encodeURIComponent(reason)}`, {
      method: 'POST'
    })
      .then(res => res.json())
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
    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 mb-6">
      <div className="flex items-start gap-4">
        <div className="bg-yellow-100 p-2 rounded-full">
          <svg className="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <div className="flex-1">
          <h3 className="text-lg font-bold text-yellow-800 mb-2">Human Approval Required</h3>
          <p className="text-yellow-700 text-sm mb-4">
            The policy engine has halted execution. A destructive or high-risk action requires your explicit approval.
          </p>
          
          <div className="mb-4">
            <label className="block text-sm font-medium text-yellow-800 mb-1">Reason (Optional)</label>
            <input 
              type="text" 
              value={reason}
              onChange={e => setReason(e.target.value)}
              className="w-full bg-white border border-yellow-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-500"
              placeholder="E.g., Authorized for demo"
            />
          </div>

          <div className="flex gap-3 mt-6">
            <button
              onClick={() => handleDecision(true)}
              disabled={submitting}
              className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded text-sm font-medium transition-colors disabled:opacity-50"
            >
              Approve Destructive Action
            </button>
            <button
              onClick={() => handleDecision(false)}
              disabled={submitting}
              className="bg-gray-200 hover:bg-gray-300 text-gray-800 px-4 py-2 rounded text-sm font-medium transition-colors disabled:opacity-50"
            >
              Reject Action
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
