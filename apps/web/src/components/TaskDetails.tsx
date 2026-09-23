import { useEffect, useState } from 'react';
import type { FC } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ApprovalCenter } from './ApprovalCenter';
import { PlanViewer } from './PlanViewer';
import { fetchWithAuth } from '../utils/api';
import { ChangeViewer } from './ChangeViewer';
import { AuditLogViewer } from './AuditLogViewer';
import { TaskConversation } from './TaskConversation';

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
      .catch(err => {
        setError(err.message);
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

  if (error) return <div className="p-8 text-red-500 text-center">{error}</div>;
  if (!task) return <div className="p-8 text-slate-500 text-center">Loading task...</div>;

  return (
    <div className="w-full animation-fade-in pb-12">
      <button
        onClick={() => navigate('/tasks')}
        className="text-slate-500 hover:text-slate-900 mb-6 font-medium text-sm transition-colors"
      >
        &larr; Back to History
      </button>

      <TaskConversation
        task={task}
        auditEvents={auditEvents}
        onAdvancedDetailsToggle={() => setShowAdvanced(!showAdvanced)}
        showAdvanced={showAdvanced}
      />

      {task.status === 'WAITING_APPROVAL' && (
        <ApprovalCenter
          taskId={task.id}
          apiUrl={apiUrl}
          onDecided={() => {
            // Let the interval pick up the state change
          }}
        />
      )}

      {showAdvanced && (
        <div className="mt-8 space-y-8 animation-fade-in">
          <div className="border-t border-slate-200 pt-8">
            <h3 className="text-xl font-bold text-slate-900 mb-6">Advanced Details</h3>

            <div className="space-y-8">
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                <h4 className="text-lg font-semibold text-slate-800 mb-4">Execution Plan</h4>
                <PlanViewer plan={plan} />
              </div>

              {snapshot && (
                <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                  <h4 className="text-lg font-semibold text-slate-800 mb-4">Filesystem Changes</h4>
                  <ChangeViewer
                    snapshot={snapshot}
                    onRollback={handleRollback}
                    isRollingBack={isRollingBack}
                  />
                </div>
              )}

              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                <h4 className="text-lg font-semibold text-slate-800 mb-4">Raw Audit Trail</h4>
                <AuditLogViewer taskId={task.id} apiUrl={apiUrl} />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
