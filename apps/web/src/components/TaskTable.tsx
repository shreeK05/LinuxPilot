import type { FC } from 'react';

export interface Task {
  id: string;
  goal: string;
  status: string;
  risk_level: number;
  created_at: string;
}

interface TaskTableProps {
  tasks: Task[];
  onSelectTask: (taskId: string) => void;
}

export const TaskTable: FC<TaskTableProps> = ({ tasks, onSelectTask }) => {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="border-b border-gray-200 text-gray-600 text-sm">
            <th className="pb-3 pr-4 font-medium">Task ID</th>
            <th className="pb-3 pr-4 font-medium">Goal</th>
            <th className="pb-3 pr-4 font-medium">Status</th>
            <th className="pb-3 font-medium">Created</th>
            <th className="pb-3 font-medium text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {tasks.length === 0 ? (
            <tr>
              <td colSpan={5} className="py-8 text-center text-gray-500">
                No tasks found. Create one to get started.
              </td>
            </tr>
          ) : (
            tasks.map(task => (
              <tr key={task.id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="py-3 pr-4 text-xs font-mono text-gray-500">
                  {task.id.split('-')[0]}
                </td>
                <td className="py-3 pr-4 font-medium text-gray-900">
                  {task.goal}
                </td>
                <td className="py-3 pr-4">
                  <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                    task.status === 'COMPLETED' ? 'bg-green-100 text-green-800' :
                    task.status === 'FAILED' ? 'bg-red-100 text-red-800' :
                    'bg-blue-100 text-blue-800'
                  }`}>
                    {task.status}
                  </span>
                </td>
                <td className="py-3 text-sm text-gray-500">
                  {new Date(task.created_at).toLocaleString()}
                </td>
                <td className="py-3 text-right">
                  <button 
                    onClick={() => onSelectTask(task.id)}
                    className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                  >
                    View Details
                  </button>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
};
