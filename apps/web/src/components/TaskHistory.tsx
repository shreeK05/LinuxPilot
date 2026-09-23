import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Clock, CheckCircle2, AlertCircle, AlertTriangle, ShieldAlert } from 'lucide-react';

export interface Task {
  id: string;
  goal: string;
  status: string;
  risk_level: number;
  created_at: string;
  completed_at?: string;
}

export const TaskHistory: React.FC<{ tasks: Task[] }> = ({ tasks }) => {
  const navigate = useNavigate();

  const getStatusDisplay = (status: string) => {
    switch(status) {
      case 'COMPLETED':
        return { text: 'Completed', icon: <CheckCircle2 size={16} />, className: 'text-green-600 bg-green-50 border-green-200' };
      case 'FAILED':
        return { text: 'Failed', icon: <AlertCircle size={16} />, className: 'text-red-600 bg-red-50 border-red-200' };
      case 'WAITING_APPROVAL':
        return { text: 'Needs Approval', icon: <ShieldAlert size={16} />, className: 'text-amber-600 bg-amber-50 border-amber-200' };
      case 'ROLLING_BACK':
      case 'ROLLED_BACK':
        return { text: 'Rolled Back', icon: <AlertTriangle size={16} />, className: 'text-orange-600 bg-orange-50 border-orange-200' };
      default:
        return { text: 'Active', icon: <Clock size={16} />, className: 'text-blue-600 bg-blue-50 border-blue-200' };
    }
  };

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffDays === 1) return 'Yesterday';
    return date.toLocaleDateString();
  };

  return (
    <div className="w-full animation-fade-in">
      <div className="flex justify-between items-end mb-6">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Task History</h2>
          <p className="text-slate-500 mt-1">Review your past activities and active tasks</p>
        </div>
      </div>

      {tasks.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-2xl p-12 text-center shadow-sm">
          <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4 text-slate-400">
            <Clock size={32} />
          </div>
          <h3 className="text-lg font-medium text-slate-900 mb-2">No tasks found</h3>
          <p className="text-slate-500">Go to Home to start your first task.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {tasks.map(task => {
            const display = getStatusDisplay(task.status);
            return (
              <div
                key={task.id}
                className="bg-white border border-slate-200 rounded-xl p-5 hover:shadow-md transition-shadow cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-4 group"
                onClick={() => navigate(`/tasks/${task.id}`)}
              >
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border ${display.className}`}>
                      {display.icon}
                      {display.text}
                    </span>
                    <span className="text-xs text-slate-400 font-medium">
                      {formatTime(task.completed_at || task.created_at)}
                    </span>
                  </div>
                  <h3 className="text-lg font-medium text-slate-900 group-hover:text-blue-600 transition-colors">
                    {task.goal}
                  </h3>
                </div>

                <div className="flex items-center">
                  <button className="text-sm font-medium text-slate-500 group-hover:text-blue-600 bg-slate-50 px-4 py-2 rounded-lg group-hover:bg-blue-50 transition-colors">
                    View
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
