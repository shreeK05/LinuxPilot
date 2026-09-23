import type { FC } from 'react';
import { useEffect, useState } from 'react';
import { fetchWithAuth } from '../utils/api';

interface DashboardStats {
  active_tasks: {
    running: number;
    waiting_approval: number;
    completed: number;
    failed: number;
  };
  success_rate: number;
  safety: {
    sandbox_escapes: number;
    rollbacks: number;
    approval_gates: number;
  };
  performance: {
    avg_step_latency_ms: number;
    avg_task_duration_s: number;
  };
}

interface DashboardProps {
  apiUrl: string;
}

export const Dashboard: FC<DashboardProps> = ({ apiUrl }) => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStats = () => {
      fetchWithAuth(`${apiUrl}/dashboard/stats`)
        .then(res => {
            if (res.ok) return res.json();
            throw new Error("Failed to fetch dashboard stats");
        })
        .then(data => {
          setStats(data);
          setError(null);
        })
        .catch(err => setError(err.message));
    };

    fetchStats();
    const intervalId = setInterval(fetchStats, 5000);
    return () => clearInterval(intervalId);
  }, [apiUrl]);

  if (error) {
    return <div className="text-red-500 p-4 border border-red-200 bg-red-50 rounded-lg">Error loading dashboard stats: {error}</div>;
  }

  if (!stats) {
    return <div className="p-4 text-gray-500">Loading metrics...</div>;
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
      <div className="bg-white p-5 rounded-lg shadow-sm border border-gray-200">
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">Active Tasks</h3>
        <div className="text-3xl font-bold text-gray-900 mb-1">{stats.active_tasks.running + stats.active_tasks.waiting_approval}</div>
        <p className="text-xs text-gray-600">
          <span className="font-medium text-blue-600">{stats.active_tasks.running}</span> Running,{' '}
          <span className="font-medium text-yellow-600">{stats.active_tasks.waiting_approval}</span> Waiting
        </p>
      </div>

      <div className="bg-white p-5 rounded-lg shadow-sm border border-gray-200">
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">Success Rate</h3>
        <div className="text-3xl font-bold text-gray-900 mb-1">{stats.success_rate}%</div>
        <p className="text-xs text-gray-600">
          <span className="font-medium text-green-600">{stats.active_tasks.completed}</span> Completed,{' '}
          <span className="font-medium text-red-600">{stats.active_tasks.failed}</span> Failed
        </p>
      </div>

      <div className="bg-white p-5 rounded-lg shadow-sm border border-gray-200">
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">Safety</h3>
        <div className="text-2xl font-bold text-gray-900 mb-1">
          {stats.safety.sandbox_escapes} <span className="text-xs font-normal text-gray-500">Escapes</span>
        </div>
        <p className="text-xs text-gray-600">
          <span className="font-medium text-orange-600">{stats.safety.rollbacks}</span> Rollbacks,{' '}
          <span className="font-medium text-purple-600">{stats.safety.approval_gates}</span> Approvals
        </p>
      </div>

      <div className="bg-white p-5 rounded-lg shadow-sm border border-gray-200">
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">Performance</h3>
        <div className="text-2xl font-bold text-gray-900 mb-1">
          {stats.performance.avg_task_duration_s}s <span className="text-xs font-normal text-gray-500">Avg Task</span>
        </div>
        <p className="text-xs text-gray-600">
          Avg Step Latency: <span className="font-medium text-gray-800">{stats.performance.avg_step_latency_ms}ms</span>
        </p>
      </div>
    </div>
  );
};
