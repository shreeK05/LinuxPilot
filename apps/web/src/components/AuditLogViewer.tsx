import type { FC } from 'react';
import { useEffect, useState } from 'react';
import { fetchWithAuth } from '../utils/api';
import { Terminal, Loader2, ServerCrash } from 'lucide-react';
import { cn } from '../utils/cn';

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
    return (
      <div className="bg-surface-900 border border-white/5 rounded-xl p-8 flex items-center justify-center text-text-muted gap-3">
        <Loader2 size={18} className="animate-spin text-brand-500" />
        Loading audit logs...
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-danger-500/10 border border-danger-500/20 rounded-xl p-6 text-danger-400 flex items-center gap-3">
        <ServerCrash size={20} />
        <span className="font-medium">Error loading audit log:</span> {error}
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className="bg-surface-900 border border-white/5 rounded-xl p-8 text-center text-text-muted italic text-sm">
        No audit events recorded for this task.
      </div>
    );
  }

  return (
    <div className="bg-surface-900 border border-white/5 rounded-xl shadow-xl overflow-hidden font-mono text-xs text-text-main">
      <div className="bg-surface-800 px-5 py-3 border-b border-white/5 flex justify-between items-center">
        <h3 className="font-semibold text-white tracking-widest uppercase flex items-center gap-2">
          <Terminal size={14} className="text-brand-400" />
          Raw Event Stream
        </h3>
        <span className="text-text-muted text-[10px] uppercase tracking-widest font-sans font-bold flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-success-500 animate-pulse"></span>
          Auto-updating
        </span>
      </div>
      <div className="p-1 max-h-[500px] overflow-y-auto hide-scrollbar">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-surface-900/50 text-text-muted uppercase tracking-widest text-[10px]">
              <th className="p-3 font-semibold w-32">Timestamp</th>
              <th className="p-3 font-semibold w-48">Event Type</th>
              <th className="p-3 font-semibold w-24">Status</th>
              <th className="p-3 font-semibold">Details</th>
            </tr>
          </thead>
          <tbody>
            {events.map((event, idx) => {
              const timeString = new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', fractionalSecondDigits: 3 });

              return (
                <tr key={idx} className="border-t border-white/5 hover:bg-surface-800/30 transition-colors">
                  <td className="p-3 text-surface-500 whitespace-nowrap align-top">{timeString}</td>
                  <td className="p-3 text-brand-400 font-medium whitespace-nowrap align-top">{event.type}</td>
                  <td className="p-3 font-bold whitespace-nowrap align-top">
                    <span className={cn(
                      "px-2 py-0.5 rounded text-[10px] tracking-widest uppercase",
                      event.status === "SUCCESS" ? "bg-success-500/10 text-success-400 border border-success-500/20" :
                      event.status === "FAILED" ? "bg-danger-500/10 text-danger-400 border border-danger-500/20" :
                      "bg-surface-700/50 text-text-muted border border-white/10"
                    )}>
                      {event.status || "N/A"}
                    </span>
                  </td>
                  <td className="p-3 text-text-muted align-top break-all">
                    {event.payload?.message ? (
                      <span className="text-white">{event.payload.message}</span>
                    ) : (
                      <pre className="text-[10px] text-surface-400 max-w-[400px] overflow-hidden text-ellipsis whitespace-nowrap" title={JSON.stringify(event.payload, null, 2)}>
                        {JSON.stringify(event.payload)}
                      </pre>
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
