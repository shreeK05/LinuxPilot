import { useEffect, useState } from 'react';
import type { FC } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ApprovalCenter } from './ApprovalCenter';
import { PlanViewer } from './PlanViewer';
import { fetchWithAuth } from '../utils/api';
import { ChangeViewer } from './ChangeViewer';
import { AuditLogViewer } from './AuditLogViewer';
import { TaskConversation } from './TaskConversation';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, Loader2 } from 'lucide-react';

interface TaskDetailsProps {
  apiUrl: string;
}

export const TaskDetails: FC<TaskDetailsProps> = ({ apiUrl }) => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [task, setTask] = useState<any>(null);
  const [plan, setPlan] = useState<any>(null);
  const [snapshot, setSnapshot] = useState<any>(null);
  const [auditEvents, setAuditEvents] = useState<any[]>([]);
  const [isRollingBack, setIsRollingBack] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;

    const fetchAll = () => {
      Promise.all([
        fetchWithAuth(`${apiUrl}/tasks`).then(res => res.json()),
        fetchWithAuth(`${apiUrl}/tasks/${id}/plan`).then(res => res.ok ? res.json() : null).catch(() => null),
        fetchWithAuth(`${apiUrl}/tasks/${id}/snapshot`).then(res => res.ok ? res.json() : null).catch(() => null),
        fetchWithAuth(`${apiUrl}/tasks/${id}/audit`).then(res => res.ok ? res.json() : []).catch(() => [])
      ])
      .then(([tasksData, planData, snapshotData, auditData]) => {
        const foundTask = tasksData.find((t: any) => t.id === id);
        if (foundTask) setTask(foundTask);
        else setError("Task not found");

        setPlan(planData);
        setSnapshot(snapshotData);
        setAuditEvents(auditData);
      })
      .catch((err: any) => {
        if (err.message === "Failed to fetch") {
          setError("Backend is unavailable. Please check your connection to the LinuxPilot API.");
        } else {
          setError(err.message || "An unexpected error occurred");
        }
      });
    };

    fetchAll();
    const interval = setInterval(fetchAll, 5000);
    return () => clearInterval(interval);
  }, [apiUrl, id]);

  const handleRollback = () => {
    if (!confirm('Are you sure you want to manually rollback this task?')) return;
    setIsRollingBack(true);
    fetchWithAuth(`${apiUrl}/tasks/${id}/rollback`, { method: 'POST' })
      .then(res => {
          if (!res.ok) throw new Error("Rollback request failed");
          return res.json();
      })
      .then(res => {
        alert(res.status === 'success' ? 'Rollback successful!' : 'Rollback failed.');
        setIsRollingBack(false);
      })
      .catch(err => {
        alert('Error: ' + err.message);
        setIsRollingBack(false);
      });
  };

  if (error) {
    return (
      <div className="flex items-center justify-center h-64 text-danger-500 font-medium">
        <div className="glass-card p-6 rounded-xl">{error}</div>
      </div>
    );
  }
  
  if (!task) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-brand-500">
        <Loader2 size={32} className="animate-spin mb-4" />
        <span className="text-text-muted">Loading task...</span>
      </div>
    );
  }

  return (
    <div className="w-full pb-12">
      <motion.button
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
        onClick={() => navigate('/tasks')}
        className="flex items-center gap-2 text-text-muted hover:text-white mb-6 font-medium text-sm transition-colors group"
      >
        <ArrowLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
        Back to History
      </motion.button>

      <TaskConversation
        task={task}
        auditEvents={auditEvents}
        onAdvancedDetailsToggle={() => setShowAdvanced(!showAdvanced)}
        showAdvanced={showAdvanced}
        plan={plan}
      />

      <AnimatePresence>
        {task.status === 'WAITING_APPROVAL' && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-8 max-w-2xl mx-auto overflow-hidden"
          >
            <ApprovalCenter
              taskId={task.id}
              apiUrl={apiUrl}
              onDecided={() => {
                // Let the interval pick up the state change
              }}
            />
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {showAdvanced && (
          <motion.div 
            initial={{ opacity: 0, y: -20, height: 0 }}
            animate={{ opacity: 1, y: 0, height: 'auto' }}
            exit={{ opacity: 0, y: -20, height: 0 }}
            className="mt-8 overflow-hidden max-w-4xl mx-auto"
          >
            <div className="pt-8">
              <h3 className="text-xl font-bold text-white mb-6 tracking-tight">Advanced Details</h3>

              <div className="space-y-6">
                <div className="glass-card rounded-xl p-6">
                  <h4 className="text-sm font-semibold text-text-muted uppercase tracking-widest mb-4">Execution Plan</h4>
                  <PlanViewer plan={plan} />
                </div>

                {snapshot && (
                  <div className="glass-card rounded-xl p-6">
                    <h4 className="text-sm font-semibold text-text-muted uppercase tracking-widest mb-4">Filesystem Changes</h4>
                    <ChangeViewer
                      snapshot={snapshot}
                      onRollback={handleRollback}
                      isRollingBack={isRollingBack}
                    />
                  </div>
                )}

                <div className="glass-card rounded-xl p-6">
                  <h4 className="text-sm font-semibold text-text-muted uppercase tracking-widest mb-4">Raw Audit Trail</h4>
                  <AuditLogViewer taskId={task.id} apiUrl={apiUrl} />
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
