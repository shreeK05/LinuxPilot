import type { FC } from 'react';
import { useEffect, useState } from 'react';
import { fetchWithAuth } from '../utils/api';

interface AuditEvent {
  id: string;
  task_id: string;
  timestamp: string;
  type: string;
  status: string;
  payload: any;
}

interface ActivityFeedProps {
  apiUrl: string;
}

export const ActivityFeed: FC<ActivityFeedProps> = ({ apiUrl }) => {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchActivity = () => {
      fetchWithAuth(`${apiUrl}/dashboard/activity`)
        .then(res => {
            if (res.ok) return res.json();
            throw new Error("Failed to fetch activity");
        })
        .then(data => {
          setEvents(data);
          setError(null);
        })
        .catch(err => setError(err.message));
    };

    fetchActivity();
    const intervalId = setInterval(fetchActivity, 5000);
    return () => clearInterval(intervalId);
  }, [apiUrl]);

  if (error) {
    return <div className="text-red-500 p-4 border border-red-200 bg-red-50 rounded-lg">Error loading activity: {error}</div>;
  }

  if (events.length === 0) {
    return <div className="p-4 text-gray-500 text-sm italic">No recent activity.</div>;
  }

  return (
    <div className="bg-white rounded-lg shadow border border-gray-200 overflow-hidden mb-8 max-h-96 flex flex-col">
      <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-800">Global Activity Feed</h3>
      </div>
      <div className="overflow-y-auto p-4">
        <ul className="space-y-4">
          {events.map((event, idx) => {
            const timeString = new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

            let color = "bg-gray-100 text-gray-700";
            if (event.status === "SUCCESS" || event.type.includes("COMPLETED")) color = "bg-green-100 text-green-800";
            if (event.status === "FAILED" || event.type.includes("FAILED")) color = "bg-red-100 text-red-800";
            if (event.type.includes("ROLLBACK")) color = "bg-orange-100 text-orange-800";
            if (event.type.includes("APPROVAL")) color = "bg-purple-100 text-purple-800";
            if (event.type === "ACTION_EXECUTED") color = "bg-blue-100 text-blue-800";

            return (
              <li key={`${event.id}-${idx}`} className="flex items-start gap-3 text-sm">
                <span className="text-gray-400 font-mono text-xs whitespace-nowrap mt-0.5">{timeString}</span>
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${color}`}>
                      {event.type}
                    </span>
                    <span className="text-gray-500 font-mono text-xs" title="Task ID">
                      {event.task_id.substring(0, 8)}
                    </span>
                  </div>
                  <div className="text-gray-700 text-xs">
                    {event.payload?.message || "No additional details provided."}
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
};
