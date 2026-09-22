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

interface AuditEvent {
  timestamp: string;
  type: string;
  status: string;
  payload: any;
}

import { ChangeViewer } from './ChangeViewer';

export const TaskDetails: FC<TaskDetailsProps> = ({ task, onBack, apiUrl }) => {
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [plan, setPlan] = useState<any>(null);
  const [snapshot, setSnapshot] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [isRollingBack, setIsRollingBack] = useState(false);

  useEffect(() => {
    Promise.all([
      fetch(`${apiUrl}/tasks/${task.id}/audit`).then(res => res.json()),
      fetch(`${apiUrl}/tasks/${task.id}/plan`).then(res => res.json()),
      fetch(`${apiUrl}/tasks/${task.id}/snapshot`).then(res => {
        if (!res.ok) return null;
        return res.json();
      }).catch(() => null)
    ])
    .then(([auditData, planData, snapshotData]) => {
      setAuditEvents(auditData);
      setPlan(planData);
      setSnapshot(snapshotData);
      setLoading(false);
    })
    .catch(err => {
      console.error(err);
      setLoading(false);
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

      <h3 className="text-lg font-semibold text-gray-800 mb-4">Execution Audit Trail</h3>
      
      {loading ? (
        <p className="text-gray-500">Loading audit trail...</p>
      ) : auditEvents.length === 0 ? (
        <p className="text-gray-500">No events found for this task.</p>
      ) : (
        <div className="space-y-4">
          {auditEvents.map((ev, idx) => (
            <div key={idx} className="flex gap-4 p-4 border border-gray-100 rounded-lg">
              <div className="text-xs text-gray-400 font-mono mt-1 w-24 shrink-0">
                {new Date(ev.timestamp).toLocaleTimeString()}
              </div>
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-semibold text-sm text-gray-800">{ev.type}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    ev.status === 'SUCCESS' ? 'bg-green-100 text-green-800' :
                    ev.status === 'FAILED' ? 'bg-red-100 text-red-800' :
                    'bg-blue-100 text-blue-800'
                  }`}>
                    {ev.status}
                  </span>
                </div>
                {ev.type === 'VERIFICATION_COMPLETED' && ev.payload ? (
                  <div className="mt-2 space-y-2">
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="bg-blue-50 p-2 rounded border border-blue-100">
                        <span className="font-bold text-blue-800 block mb-1">Expected State</span>
                        <pre className="text-blue-900 whitespace-pre-wrap font-mono">
                          {typeof ev.payload.expected_state === 'object' ? JSON.stringify(ev.payload.expected_state, null, 2) : String(ev.payload.expected_state)}
                        </pre>
                      </div>
                      <div className={`p-2 rounded border ${ev.status === 'SUCCESS' ? 'bg-green-50 border-green-100' : 'bg-red-50 border-red-100'}`}>
                        <span className={`font-bold block mb-1 ${ev.status === 'SUCCESS' ? 'text-green-800' : 'text-red-800'}`}>Actual State</span>
                        <pre className={`whitespace-pre-wrap font-mono ${ev.status === 'SUCCESS' ? 'text-green-900' : 'text-red-900'}`}>
                          {typeof ev.payload.actual_state === 'object' ? JSON.stringify(ev.payload.actual_state, null, 2) : String(ev.payload.actual_state)}
                        </pre>
                      </div>
                    </div>
                    {ev.payload.diff && (
                      <div className="bg-gray-50 p-2 rounded border border-gray-200">
                        <span className="font-bold text-gray-700 text-xs block mb-1">Diff / Match Analysis</span>
                        <pre className="text-gray-600 text-xs font-mono overflow-x-auto">
                          {JSON.stringify(ev.payload.diff, null, 2)}
                        </pre>
                      </div>
                    )}
                    <div className="flex gap-2 text-[10px] font-mono text-gray-500">
                      <span className="bg-gray-100 px-1.5 py-0.5 rounded">Method: {ev.payload.verification_method || 'unknown'}</span>
                      <span className="bg-gray-100 px-1.5 py-0.5 rounded">Confidence: {ev.payload.confidence || '1.0'}</span>
                      {ev.payload.retry_suggested && <span className="bg-yellow-100 text-yellow-800 px-1.5 py-0.5 rounded">Retry Suggested</span>}
                    </div>
                  </div>
                ) : (
                  <pre className="text-xs text-gray-600 bg-gray-50 p-2 rounded overflow-x-auto">
                    {JSON.stringify(ev.payload, null, 2)}
                  </pre>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
