"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Activity,
  CheckCircle,
  Clock,
  Code,
  FileDiff,
  FileText,
  Play,
  RotateCcw,
  Shield,
  ShieldAlert,
  Terminal,
  XCircle,
  Eye,
} from "lucide-react";
import { format } from "date-fns";

export default function Dashboard() {
  const [tasks, setTasks] = useState<any[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [goal, setGoal] = useState("");
  const [mode, setMode] = useState("hybrid");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchTasks();
    const interval = setInterval(fetchTasks, 2000);
    return () => clearInterval(interval);
  }, []);

  const fetchTasks = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/v1/tasks/");
      if (res.ok) {
        const data = await res.json();
        setTasks(data.tasks);
      }
    } catch (e) {
      console.error("Failed to fetch tasks", e);
    }
  };

  const createTask = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/api/v1/tasks/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal, mode, auto_approve: false }),
      });
      if (res.ok) {
        const data = await res.json();
        setGoal("");
        setSelectedTaskId(data.task_id);
        fetchTasks();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100 font-sans">
      {/* Sidebar */}
      <div className="w-80 border-r border-gray-800 bg-gray-900/50 flex flex-col backdrop-blur-xl">
        <div className="p-6 border-b border-gray-800">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/20 text-blue-400 rounded-lg">
              <Shield size={24} />
            </div>
            <div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">
                LinuxPilot
              </h1>
              <p className="text-xs text-gray-400">Trust-First OS Agent</p>
            </div>
          </div>
        </div>

        <div className="p-4 border-b border-gray-800">
          <form onSubmit={createTask} className="space-y-4">
            <div>
              <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 block">
                New Task
              </label>
              <textarea
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                placeholder="Organize my Downloads folder..."
                className="w-full bg-gray-950 border border-gray-800 rounded-lg p-3 text-sm focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 outline-none resize-none placeholder-gray-600 transition-all"
                rows={3}
                required
              />
            </div>
            <div className="flex gap-2">
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value)}
                className="bg-gray-950 border border-gray-800 rounded-lg p-2 text-sm text-gray-300 flex-1 outline-none"
              >
                <option value="hybrid">Hybrid</option>
                <option value="api">API Only</option>
                <option value="gui">GUI Only</option>
              </select>
              <button
                type="submit"
                disabled={loading || !goal}
                className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
              >
                <Play size={16} />
                Run
              </button>
            </div>
          </form>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Active Tasks
          </h2>
          {tasks.length === 0 ? (
            <div className="text-center py-8 text-gray-500 text-sm">
              No active tasks
            </div>
          ) : (
            tasks.map((task) => (
              <button
                key={task.task_id}
                onClick={() => setSelectedTaskId(task.task_id)}
                className={`w-full text-left p-4 rounded-xl border transition-all ${
                  selectedTaskId === task.task_id
                    ? "bg-blue-900/20 border-blue-500/50 shadow-[0_0_15px_rgba(59,130,246,0.1)]"
                    : "bg-gray-950/50 border-gray-800 hover:border-gray-700 hover:bg-gray-800/50"
                }`}
              >
                <div className="flex justify-between items-start mb-2">
                  <span className="text-xs font-mono text-gray-500 truncate">
                    {task.task_id.substring(0, 8)}
                  </span>
                  <StatusBadge status={task.status} />
                </div>
                <p className="text-sm font-medium line-clamp-2 leading-snug">
                  {task.goal}
                </p>
                <div className="flex items-center gap-4 mt-3 text-xs text-gray-400">
                  <div className="flex items-center gap-1">
                    <Activity size={14} />
                    {task.current_step}/{task.total_steps || "?"}
                  </div>
                  <div className="flex items-center gap-1">
                    <Clock size={14} />
                    {task.elapsed_time.toFixed(0)}s
                  </div>
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-gray-900 via-gray-950 to-gray-950">
        {selectedTaskId ? (
          <TaskDetail taskId={selectedTaskId} />
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center space-y-4 max-w-md p-8">
              <div className="w-16 h-16 bg-gray-900 border border-gray-800 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-2xl">
                <Terminal size={32} className="text-gray-600" />
              </div>
              <h2 className="text-2xl font-bold text-gray-300">
                Select or Create a Task
              </h2>
              <p className="text-gray-500 leading-relaxed text-sm">
                LinuxPilot runs tasks in a fully sandboxed overlay filesystem.
                Your real data is never touched without explicit approval.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    init: "bg-gray-500/20 text-gray-400 border-gray-500/30",
    planning: "bg-purple-500/20 text-purple-400 border-purple-500/30",
    policy_check: "bg-indigo-500/20 text-indigo-400 border-indigo-500/30",
    waiting_approval: "bg-amber-500/20 text-amber-400 border-amber-500/30",
    ready: "bg-blue-500/20 text-blue-400 border-blue-500/30",
    executing: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
    verifying: "bg-teal-500/20 text-teal-400 border-teal-500/30",
    review: "bg-blue-500/20 text-blue-400 border-blue-500/30 shadow-[0_0_10px_rgba(59,130,246,0.2)]",
    rolling_back: "bg-orange-500/20 text-orange-400 border-orange-500/30",
    replanning: "bg-purple-500/20 text-purple-400 border-purple-500/30",
    completed: "bg-green-500/20 text-green-400 border-green-500/30",
    failed: "bg-red-500/20 text-red-400 border-red-500/30",
    aborted: "bg-red-500/20 text-red-400 border-red-500/30",
  };

  return (
    <span
      className={`px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider border ${
        colors[status] || colors.init
      }`}
    >
      {status.replace("_", " ")}
    </span>
  );
}

function TaskDetail({ taskId }: { taskId: string }) {
  const [task, setTask] = useState<any>(null);
  const [events, setEvents] = useState<any[]>([]);
  const [diff, setDiff] = useState<any>(null);
  const [audit, setAudit] = useState<any>(null);
  const [activeTab, setActiveTab] = useState("timeline");
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Reset state
    setTask(null);
    setEvents([]);
    setDiff(null);
    setAudit(null);

    // Initial fetch
    fetchTask();
    
    // Connect WebSocket
    const ws = new WebSocket(`ws://localhost:8000/api/v1/tasks/${taskId}/events`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type !== "heartbeat") {
        setEvents((prev) => [...prev, { ...data, id: Date.now() + Math.random() }]);
        
        // Refresh task if state changed
        if (data.type === "state_change") {
          fetchTask();
          if (data.to_state === "review") {
            fetchDiff();
          }
          if (["completed", "failed", "aborted"].includes(data.to_state)) {
            fetchAudit();
          }
        }
      }
    };

    const interval = setInterval(() => {
      fetchTask();
      if (task?.status === "review" && !diff) fetchDiff();
      if (["completed", "failed", "aborted"].includes(task?.status) && !audit) fetchAudit();
    }, 2000);

    return () => {
      ws.close();
      clearInterval(interval);
    };
  }, [taskId]);

  const fetchTask = async () => {
    try {
      const res = await fetch(`http://localhost:8000/api/v1/tasks/${taskId}`);
      if (res.ok) setTask(await res.json());
    } catch (e) { }
  };

  const fetchDiff = async () => {
    try {
      const res = await fetch(`http://localhost:8000/api/v1/tasks/${taskId}/diff`);
      if (res.ok) setDiff(await res.json());
    } catch (e) { }
  };

  const fetchAudit = async () => {
    try {
      const res = await fetch(`http://localhost:8000/api/v1/tasks/${taskId}/audit`);
      if (res.ok) setAudit(await res.json());
    } catch (e) { }
  };

  const handleAction = async (action: string, payload: any = {}) => {
    try {
      await fetch(`http://localhost:8000/api/v1/tasks/${taskId}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      fetchTask();
    } catch (e) { }
  };

  if (!task) return <div className="flex-1 flex items-center justify-center"><Activity className="animate-spin text-gray-600" /></div>;

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-gray-800 bg-gray-900/30 backdrop-blur-md">
        <div className="flex justify-between items-start">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h2 className="text-xl font-bold">{task.goal}</h2>
              <StatusBadge status={task.status} />
            </div>
            <p className="text-sm text-gray-400 font-mono">Task ID: {taskId}</p>
          </div>
          
          {/* Action Buttons */}
          <div className="flex gap-2">
            {task.status === "waiting_approval" && (
              <>
                <button
                  onClick={() => handleAction("approve", { approved: true })}
                  className="bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors"
                >
                  <CheckCircle size={16} /> Approve
                </button>
                <button
                  onClick={() => handleAction("approve", { approved: false })}
                  className="bg-red-600 hover:bg-red-500 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors"
                >
                  <XCircle size={16} /> Reject
                </button>
              </>
            )}
            
            {task.status === "review" && (
              <>
                <button
                  onClick={() => handleAction("commit")}
                  className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors shadow-[0_0_15px_rgba(59,130,246,0.3)]"
                >
                  <CheckCircle size={16} /> Commit Changes
                </button>
                <button
                  onClick={() => handleAction("discard")}
                  className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors"
                >
                  <RotateCcw size={16} /> Discard
                </button>
              </>
            )}

            {!["completed", "failed", "aborted", "review"].includes(task.status) && (
              <button
                onClick={() => handleAction("kill")}
                className="bg-red-900/50 hover:bg-red-900 text-red-400 border border-red-800 px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors"
              >
                <XCircle size={16} /> Kill Task
              </button>
            )}
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-4 mt-6">
          <StatBox icon={<Activity size={18} />} label="Progress" value={`${task.current_step} / ${task.total_steps || "?"} steps`} />
          <StatBox icon={<Clock size={18} />} label="Elapsed" value={`${task.elapsed_time.toFixed(1)}s`} />
          <StatBox icon={<RotateCcw size={18} />} label="Rollbacks" value={task.rollback_count} />
          <StatBox icon={<Terminal size={18} />} label="Mode" value={task.mode} />
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-800 px-6 pt-4 bg-gray-900/10">
        <TabButton id="timeline" label="Live Timeline" icon={<Activity size={16} />} active={activeTab === "timeline"} onClick={() => setActiveTab("timeline")} />
        <TabButton id="diff" label="Changes (Diff)" icon={<FileDiff size={16} />} active={activeTab === "diff"} onClick={() => setActiveTab("diff")} badge={diff?.changes?.length} />
        <TabButton id="audit" label="Audit Trail" icon={<Shield size={16} />} active={activeTab === "audit"} onClick={() => setActiveTab("audit")} />
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6 relative">
        {activeTab === "timeline" && <EventTimeline events={events} />}
        {activeTab === "diff" && <DiffViewer diff={diff} isLoading={task.status === "review" && !diff} />}
        {activeTab === "audit" && <AuditViewer audit={audit} />}
      </div>
    </div>
  );
}

function StatBox({ icon, label, value }: { icon: React.ReactNode; label: string; value: string | number }) {
  return (
    <div className="bg-gray-950/50 border border-gray-800 rounded-xl p-3 flex items-center gap-3">
      <div className="text-gray-500">{icon}</div>
      <div>
        <div className="text-[10px] uppercase tracking-wider text-gray-500 font-bold">{label}</div>
        <div className="text-sm font-medium text-gray-200">{value}</div>
      </div>
    </div>
  );
}

function TabButton({ id, label, icon, active, onClick, badge }: any) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-3 border-b-2 text-sm font-medium transition-colors ${
        active
          ? "border-blue-500 text-blue-400"
          : "border-transparent text-gray-500 hover:text-gray-300 hover:border-gray-700"
      }`}
    >
      {icon} {label}
      {badge > 0 && (
        <span className="ml-1 bg-gray-800 text-gray-300 px-1.5 py-0.5 rounded-full text-xs">
          {badge}
        </span>
      )}
    </button>
  );
}

function EventTimeline({ events }: { events: any[] }) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);

  if (events.length === 0) {
    return <div className="text-center text-gray-500 py-12">Waiting for events...</div>;
  }

  return (
    <div className="space-y-4 max-w-3xl mx-auto">
      {events.map((event) => (
        <div key={event.id} className="flex gap-4">
          <div className="flex flex-col items-center">
            <div className="w-8 h-8 rounded-full bg-gray-900 border border-gray-800 flex items-center justify-center z-10 shadow-sm">
              <EventIcon type={event.type} />
            </div>
            <div className="w-px h-full bg-gray-800 mt-2 -mb-6" />
          </div>
          <div className="bg-gray-950/80 border border-gray-800/80 rounded-xl p-4 flex-1 backdrop-blur-sm shadow-sm hover:border-gray-700 transition-colors">
            <div className="flex justify-between items-start mb-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-gray-500">
                {event.type.replace("_", " ")}
              </span>
              <span className="text-[10px] font-mono text-gray-600">
                {event.timestamp ? format(new Date(event.timestamp), "HH:mm:ss.SSS") : ""}
              </span>
            </div>
            <EventContent event={event} />
          </div>
        </div>
      ))}
      <div ref={endRef} className="h-4" />
    </div>
  );
}

function EventIcon({ type }: { type: string }) {
  switch (type) {
    case "state_change": return <Activity size={14} className="text-blue-400" />;
    case "step_started": return <Play size={14} className="text-emerald-400" />;
    case "step_completed": return <CheckCircle size={14} className="text-emerald-500" />;
    case "verification": return <Shield size={14} className="text-teal-400" />;
    case "invariant_check": return <ShieldAlert size={14} className="text-amber-400" />;
    case "rollback": return <RotateCcw size={14} className="text-orange-400" />;
    case "audit_event": return <FileText size={14} className="text-purple-400" />;
    default: return <Code size={14} className="text-gray-400" />;
  }
}

function EventContent({ event }: { event: any }) {
  switch (event.type) {
    case "state_change":
      return (
        <div>
          <div className="text-sm font-medium">
            <span className="text-gray-400 line-through mr-2">{event.from_state}</span>
            <span className="text-blue-400">→ {event.to_state}</span>
          </div>
          {event.reason && <div className="text-xs text-gray-500 mt-1">{event.reason}</div>}
        </div>
      );
    case "step_started":
      return (
        <div>
          <div className="text-sm font-medium text-gray-200">{event.intent}</div>
          <div className="text-xs font-mono text-gray-500 mt-1 bg-gray-900 inline-block px-2 py-0.5 rounded">
            {event.tool}
          </div>
        </div>
      );
    case "audit_event":
      return (
        <div>
          <div className="text-sm font-medium text-purple-300">{event.kind}</div>
          <pre className="text-[10px] text-gray-400 mt-2 bg-gray-900 p-2 rounded-lg overflow-x-auto">
            {JSON.stringify(event.payload, null, 2)}
          </pre>
        </div>
      );
    default:
      return (
        <pre className="text-[10px] text-gray-400 bg-gray-900 p-2 rounded-lg overflow-x-auto">
          {JSON.stringify(event, (k, v) => ["type", "timestamp", "id"].includes(k) ? undefined : v, 2)}
        </pre>
      );
  }
}

function DiffViewer({ diff, isLoading }: { diff: any; isLoading: boolean }) {
  if (isLoading) return <div className="text-center text-gray-500 py-12"><Activity className="animate-spin text-gray-600 mx-auto" /></div>;
  if (!diff) return <div className="text-center text-gray-500 py-12">No diff available. Task must be in 'review' state.</div>;

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-gray-950 border border-gray-800 rounded-xl overflow-hidden shadow-lg">
        <div className="bg-gray-900 border-b border-gray-800 px-4 py-3 flex gap-6">
          <div className="flex items-center gap-2 text-sm">
            <div className="w-3 h-3 rounded-full bg-emerald-500/20 border border-emerald-500 flex items-center justify-center">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            </div>
            <span className="text-emerald-400 font-medium">{diff.summary.add || 0} Added</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <div className="w-3 h-3 rounded-full bg-blue-500/20 border border-blue-500 flex items-center justify-center">
              <div className="w-1.5 h-1.5 rounded-full bg-blue-500" />
            </div>
            <span className="text-blue-400 font-medium">{diff.summary.modify || 0} Modified</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <div className="w-3 h-3 rounded-full bg-red-500/20 border border-red-500 flex items-center justify-center">
              <div className="w-1.5 h-1.5 rounded-full bg-red-500" />
            </div>
            <span className="text-red-400 font-medium">{diff.summary.delete || 0} Deleted</span>
          </div>
        </div>
        
        <div className="divide-y divide-gray-800">
          {diff.changes.length === 0 ? (
            <div className="p-8 text-center text-gray-500">No changes detected</div>
          ) : (
            diff.changes.map((change: any, i: number) => (
              <div key={i} className="p-3 flex items-start gap-3 hover:bg-gray-900/50 transition-colors">
                <div className="mt-0.5">
                  {change.kind === "add" && <span className="text-emerald-500 font-mono font-bold">+</span>}
                  {change.kind === "modify" && <span className="text-blue-500 font-mono font-bold">~</span>}
                  {change.kind === "delete" && <span className="text-red-500 font-mono font-bold">-</span>}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-mono text-gray-300 truncate">{change.path}</div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function AuditViewer({ audit }: { audit: any }) {
  if (!audit) return <div className="text-center text-gray-500 py-12">Audit trail available after task completion.</div>;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className={`p-4 rounded-xl border ${audit.chain_verified ? "bg-emerald-950/20 border-emerald-900" : "bg-red-950/20 border-red-900"}`}>
        <div className="flex items-center gap-3 mb-2">
          {audit.chain_verified ? <Shield className="text-emerald-500" /> : <ShieldAlert className="text-red-500" />}
          <h3 className={`font-bold ${audit.chain_verified ? "text-emerald-400" : "text-red-400"}`}>
            {audit.chain_verified ? "Audit Chain Verified" : "Audit Chain Broken"}
          </h3>
        </div>
        {!audit.chain_verified && (
          <p className="text-sm text-red-300 font-mono">{audit.verification_error}</p>
        )}
        <div className="text-xs text-gray-500 font-mono mt-2 flex items-center gap-2">
          <span className="uppercase tracking-wider">Final Hash:</span> 
          <span className="text-gray-400 break-all bg-gray-900 px-2 py-1 rounded">{audit.final_hash}</span>
        </div>
      </div>

      <div className="space-y-2">
        {audit.entries.map((entry: any) => (
          <div key={entry.seq} className="bg-gray-950 border border-gray-800 rounded-lg p-4">
            <div className="flex justify-between items-start mb-3">
              <div className="flex items-center gap-3">
                <span className="text-xs font-mono bg-gray-800 text-gray-400 px-2 py-0.5 rounded">#{entry.seq}</span>
                <span className="text-sm font-bold text-purple-400 uppercase tracking-wider">{entry.kind}</span>
                {entry.step && <span className="text-xs font-mono text-gray-500">Step: {entry.step}</span>}
              </div>
              <span className="text-xs text-gray-500 font-mono">{format(new Date(entry.ts), "yyyy-MM-dd HH:mm:ss.SSS")}</span>
            </div>
            
            <pre className="text-[11px] text-gray-300 font-mono bg-gray-900/50 p-3 rounded border border-gray-800 overflow-x-auto">
              {JSON.stringify(entry.payload, null, 2)}
            </pre>
            
            <div className="mt-3 text-[10px] font-mono text-gray-600 flex flex-col gap-1">
              <div><span className="text-gray-500">Prev:</span> {entry.prev}</div>
              <div><span className="text-gray-500">Hash:</span> {entry.hash}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
