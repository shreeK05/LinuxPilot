import { useEffect, useState } from 'react';
import type { FC } from 'react';
import type { Task } from './TaskTable';

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

export const TaskDetails: FC<TaskDetailsProps> = ({ task, onBack, apiUrl }) => {
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${apiUrl}/tasks/${task.id}/audit`)
      .then(res => res.json())
      .then(data => {
        setAuditEvents(data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, [apiUrl, task.id]);

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
                <pre className="text-xs text-gray-600 bg-gray-50 p-2 rounded overflow-x-auto">
                  {JSON.stringify(ev.payload, null, 2)}
                </pre>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
