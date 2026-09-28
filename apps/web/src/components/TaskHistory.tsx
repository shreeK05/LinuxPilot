import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Clock, CheckCircle2, AlertCircle, AlertTriangle, ShieldAlert, ChevronRight } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '../utils/cn';

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
        return { text: 'Completed', icon: <CheckCircle2 size={16} />, className: 'text-success-500 bg-success-500/10 border-success-500/20' };
      case 'FAILED':
        return { text: 'Failed', icon: <AlertCircle size={16} />, className: 'text-danger-500 bg-danger-500/10 border-danger-500/20' };
      case 'WAITING_APPROVAL':
        return { text: 'Needs Approval', icon: <ShieldAlert size={16} />, className: 'text-warning-500 bg-warning-500/10 border-warning-500/20' };
      case 'ROLLING_BACK':
      case 'ROLLED_BACK':
        return { text: 'Rolled Back', icon: <AlertTriangle size={16} />, className: 'text-orange-500 bg-orange-500/10 border-orange-500/20' };
      default:
        return { text: 'Active', icon: <Clock size={16} />, className: 'text-brand-400 bg-brand-500/10 border-brand-500/20' };
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
    if (diffMins < 60) return `${diffMins} min ago`;
    if (diffHours < 24) return `${diffHours} hr ago`;
    if (diffDays === 1) return 'Yesterday';
    return date.toLocaleDateString();
  };

  return (
    <div className="w-full">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h2 className="text-3xl font-bold text-white tracking-tight">Task History</h2>
          <p className="text-text-muted mt-2">Review your past activities and active tasks</p>
        </div>
      </div>

      {tasks.length === 0 ? (
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card rounded-2xl p-16 text-center"
        >
          <div className="w-20 h-20 bg-surface-800 rounded-full flex items-center justify-center mx-auto mb-6 text-text-muted border border-white/5">
            <Clock size={36} />
          </div>
          <h3 className="text-xl font-medium text-white mb-2">No tasks found</h3>
          <p className="text-text-muted">Go to Home to start your first task.</p>
        </motion.div>
      ) : (
        <div className="flex flex-col gap-3">
          {tasks.map((task, idx) => {
            const display = getStatusDisplay(task.status);
            return (
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.05 }}
                key={task.id}
                className="glass-card rounded-xl p-5 hover:bg-surface-700/50 hover:border-brand-500/30 transition-all cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-4 group"
                onClick={() => navigate(`/tasks/${task.id}`)}
              >
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2.5">
                    <span className={cn("inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold border", display.className)}>
                      {display.icon}
                      {display.text}
                    </span>
                    <span className="text-xs text-text-muted font-medium flex items-center gap-1">
                      <Clock size={12} />
                      {formatTime(task.completed_at || task.created_at)}
                    </span>
                  </div>
                  <h3 className="text-lg font-medium text-white group-hover:text-brand-400 transition-colors">
                    {task.goal}
                  </h3>
                </div>

                <div className="flex items-center">
                  <div className="w-10 h-10 rounded-lg bg-surface-800 border border-white/5 flex items-center justify-center text-text-muted group-hover:bg-brand-600/20 group-hover:text-brand-400 group-hover:border-brand-500/30 transition-all">
                    <ChevronRight size={20} />
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
};
