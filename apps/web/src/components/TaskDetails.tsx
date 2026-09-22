import { useEffect, useState } from 'react';
import type { FC } from 'react';
import type { Task } from './TaskTable';
import { ApprovalCenter } from './ApprovalCenter';
import { PlanViewer } from './PlanViewer';

interface TaskDetailsProps {
  task: Task;
  onBack: () => void;
  apiUrl: string;
}



import { ChangeViewer } from './ChangeViewer';
import { AuditLogViewer } from './AuditLogViewer';

export const TaskDetails: FC<TaskDetailsProps> = ({ task, onBack, apiUrl }) => {
  const [plan, setPlan] = useState<any>(null);
  const [snapshot, setSnapshot] = useState<any>(null);
  const [isRollingBack, setIsRollingBack] = useState(false);

  useEffect(() => {
    Promise.all([
      fetch(`${apiUrl}/tasks/${task.id}/plan`).then(res => res.json()),
      fetch(`${apiUrl}/tasks/${task.id}/snapshot`).then(res => {
        if (!res.ok) return null;
        return res.json();
      }).catch(() => null)
    ])
    .then(([planData, snapshotData]) => {
      setPlan(planData);
      setSnapshot(snapshotData);
    })
    .catch(err => {
      console.error(err);
    });
  }, [apiUrl, task.id]);

  const handleRollback = () => {
    if (!confirm('Are you sure you want to manually rollback this task?')) return;
    setIsRollingBack(true);
    fetch(`${apiUrl}/tasks/${task.id}/rollback`, { method: 'POST' })
      .then(res => res.json())
      .then(res => {
        alert(res.status === 'success' ? 'Rollback successful!' : 'Rollback failed.');
        window.location.reload();
      })
      .catch(err => {
        alert('Error: ' + err.message);
        setIsRollingBack(false);
      });
  };

  const handleExecute = () => {
    fetch(`${apiUrl}/tasks/${task.id}/execute`, { method: 'POST' })
      .then(res => res.json())
      .then(() => alert('Execution started. Refresh the page to see updates.'));
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center gap-4 mb-6">
        <button 
          onClick={onBack}
          className="text-gray-500 hover:text-gray-900"
        >
          &larr; Back
        </button>
        <h2 className="text-xl font-semibold text-gray-800 flex-1">Task Details</h2>
        <span className="text-xs font-mono bg-gray-100 text-gray-600 px-2 py-1 rounded">
          {task.id}
        </span>
        <button
          onClick={handleExecute}
          className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded text-sm font-medium transition-colors"
        >
          Run Execution
        </button>
      </div>

      <div className="grid grid-cols-2 gap-6 mb-8">
        <div className="bg-gray-50 p-4 rounded-lg">
          <h3 className="text-sm font-medium text-gray-500 mb-1">Goal</h3>
          <p className="text-gray-900 font-medium">{task.goal}</p>
        </div>
        <div className="bg-gray-50 p-4 rounded-lg">
          <h3 className="text-sm font-medium text-gray-500 mb-1">Status</h3>
          <p className="text-gray-900 font-medium">{task.status}</p>
        </div>
      </div>
      
      <div className="mb-8">
        <PlanViewer plan={plan} />
      </div>
      
      {task.status === 'WAITING_APPROVAL' && (
        <ApprovalCenter 
          taskId={task.id} 
          apiUrl={apiUrl} 
          onDecided={() => {
            alert('Decision recorded. Refreshing...');
            window.location.reload();
          }} 
        />
      )}

      {snapshot && (
        <ChangeViewer 
          snapshot={snapshot} 
          onRollback={handleRollback} 
          isRollingBack={isRollingBack} 
        />
      )}

      <h3 className="text-lg font-semibold text-gray-800 mb-4 mt-8">Execution Audit Trail</h3>
      <AuditLogViewer taskId={task.id} apiUrl={apiUrl} />
    </div>
  );
};
