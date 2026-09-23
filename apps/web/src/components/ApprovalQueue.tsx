import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldAlert, ArrowRight, ShieldCheck } from 'lucide-react';
import type { Task } from './TaskHistory';

export const ApprovalQueue: React.FC<{ tasks: Task[] }> = ({ tasks }) => {
  const navigate = useNavigate();
  const pendingTasks = tasks.filter(t => t.status === 'WAITING_APPROVAL');

  return (
    <div className="w-full animation-fade-in">
      <div className="flex justify-between items-end mb-6">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Approval Queue</h2>
          <p className="text-slate-500 mt-1">Review actions that require your explicit consent</p>
        </div>
      </div>

      {pendingTasks.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-2xl p-12 text-center shadow-sm">
          <div className="w-16 h-16 bg-green-50 rounded-full flex items-center justify-center mx-auto mb-4 text-green-500">
            <ShieldCheck size={32} />
          </div>
          <h3 className="text-lg font-medium text-slate-900 mb-2">All clear</h3>
          <p className="text-slate-500">There are no pending actions requiring your approval right now.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {pendingTasks.map(task => (
            <div
              key={task.id}
              className="bg-white border-l-4 border-l-amber-500 border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4"
            >
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <ShieldAlert size={18} className="text-amber-500" />
                  <span className="text-sm font-bold text-amber-700 uppercase tracking-wider">Approval Required</span>
                </div>
                <h3 className="text-lg font-medium text-slate-900 mb-1">
                  {task.goal}
                </h3>
                <p className="text-sm text-slate-500">
                  This task involves destructive or high-risk actions. Please review it carefully.
                </p>
              </div>

              <div className="flex items-center">
                <button
                  onClick={() => navigate(`/tasks/${task.id}`)}
                  className="bg-amber-100 hover:bg-amber-200 text-amber-800 font-medium px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
                >
                  Review Details
                  <ArrowRight size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
