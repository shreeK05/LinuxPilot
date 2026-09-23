import type { FC } from 'react';
import { useEffect, useState } from 'react';
import { fetchWithAuth } from '../utils/api';

interface TaskAuditEvent {
  timestamp: string;
  type: string;
  status: string;
  payload: any;
}

interface AuditLogViewerProps {
  taskId: string;
  apiUrl: string;
}

export const AuditLogViewer: FC<AuditLogViewerProps> = ({ taskId, apiUrl }) => {
  const [events, setEvents] = useState<TaskAuditEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;

    const fetchAudit = () => {
      fetchWithAuth(`${apiUrl}/tasks/${taskId}/audit`)
        .then(res => {
            if (res.ok) return res.json();
            throw new Error("Failed to fetch audit log");
        })
        .then(data => {
          if (isMounted) {
            setEvents(data);
            setError(null);
            setLoading(false);
          }
        })
        .catch(err => {
          if (isMounted) {
            setError(err.message);
            setLoading(false);
          }
        });
    };

    fetchAudit();
    const intervalId = setInterval(fetchAudit, 5000);

    return () => {
      isMounted = false;
      clearInterval(intervalId);
    };
  }, [taskId, apiUrl]);

  if (loading) {
    return <div className="p-4 text-gray-500">Loading audit log...</div>;
  }

  if (error) {
    return <div className="text-red-500 p-4 border border-red-200 bg-red-50 rounded-lg">Error loading audit log: {error}</div>;
  }

  if (events.length === 0) {
    return <div className="p-4 text-gray-500 italic text-sm">No audit events recorded for this task.</div>;
  }

  return (
    <div className="bg-gray-900 rounded-lg shadow overflow-hidden font-mono text-xs text-gray-300">
      <div className="bg-gray-800 px-4 py-2 border-b border-gray-700 flex justify-between items-center">
        <h3 className="font-semibold text-gray-100">Task Audit Trail</h3>
        <span className="text-gray-500 text-[10px]">Auto-updates every 5s</span>
      </div>
      <div className="p-4 max-h-96 overflow-y-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-gray-700 text-gray-400">
              <th className="pb-2 font-medium">Timestamp</th>
              <th className="pb-2 font-medium">Event Type</th>
              <th className="pb-2 font-medium">Status</th>
              <th className="pb-2 font-medium">Details</th>
            </tr>
          </thead>
          <tbody>
            {events.map((event, idx) => {
              const timeString = new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', fractionalSecondDigits: 3 });

              let statusColor = "text-gray-300";
              if (event.status === "SUCCESS") statusColor = "text-green-400";
              if (event.status === "FAILED") statusColor = "text-red-400";

              return (
                <tr key={idx} className="border-b border-gray-800 last:border-0 hover:bg-gray-800/50">
                  <td className="py-2 pr-4 text-gray-500 whitespace-nowrap align-top">{timeString}</td>
                  <td className="py-2 pr-4 text-blue-300 font-bold whitespace-nowrap align-top">{event.type}</td>
                  <td className={`py-2 pr-4 font-bold whitespace-nowrap align-top ${statusColor}`}>{event.status || "-"}</td>
                  <td className="py-2 text-gray-400 align-top break-all">
                    {event.payload?.message ? (
                      <span>{event.payload.message}</span>
                    ) : (
                      <span className="opacity-50 text-[10px]">{JSON.stringify(event.payload)}</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
