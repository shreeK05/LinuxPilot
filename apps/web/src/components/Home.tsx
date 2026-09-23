import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Send, Terminal, FolderOpen, Search, Copy, CheckCircle2 } from 'lucide-react';
import { fetchWithAuth } from '../utils/api';

export const Home: React.FC<{ apiUrl: string }> = ({ apiUrl }) => {
  const [goal, setGoal] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent | string) => {
    if (typeof e !== 'string') e.preventDefault();

    const text = typeof e === 'string' ? e : goal;
    if (!text.trim()) return;

    setIsSubmitting(true);
    try {
      const res = await fetchWithAuth(`${apiUrl}/tasks/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal: text.trim(), risk_level: 1 })
      });

      if (!res.ok) throw new Error("Failed to create task");

      const data = await res.json();
      // Start execution automatically to provide a seamless chat flow
      await fetchWithAuth(`${apiUrl}/tasks/${data.id}/execute`, { method: 'POST' });

      navigate(`/tasks/${data.id}`);
    } catch (err) {
      console.error(err);
      alert("Error starting task. See console for details.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const suggestions = [
    { text: "Find all PDF files in Downloads", icon: <Search size={18} className="text-blue-500" /> },
    { text: "Organize my Downloads folder", icon: <FolderOpen size={18} className="text-purple-500" /> },
    { text: "Show me files modified today", icon: <CheckCircle2 size={18} className="text-green-500" /> },
    { text: "Find duplicate files", icon: <Copy size={18} className="text-amber-500" /> }
  ];

  return (
    <div className="flex flex-col items-center justify-center min-h-[80vh] w-full max-w-3xl mx-auto animation-fade-in">

      <div className="flex flex-col items-center mb-10 text-center">
        <div className="w-16 h-16 bg-blue-600 rounded-2xl flex items-center justify-center text-white mb-6 shadow-lg shadow-blue-500/20">
          <Terminal size={32} />
        </div>
        <h1 className="text-4xl font-bold text-slate-900 tracking-tight mb-3">
          How can I help you?
        </h1>
        <p className="text-lg text-slate-500">
          Tell LinuxPilot what you want to do on your system.
        </p>
      </div>

      <div className="w-full relative group">
        <div className="absolute -inset-1 bg-gradient-to-r from-blue-500 to-purple-500 rounded-2xl blur opacity-20 group-hover:opacity-30 transition duration-500"></div>
        <form
          onSubmit={handleSubmit}
          className="relative bg-white flex items-center p-2 rounded-2xl shadow-sm border border-slate-200"
        >
          <input
            type="text"
            className="flex-1 bg-transparent px-4 py-4 text-lg outline-none text-slate-800 placeholder-slate-400"
            placeholder="What would you like me to do?"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            disabled={isSubmitting}
            autoFocus
          />
          <button
            type="submit"
            disabled={!goal.trim() || isSubmitting}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white p-3 rounded-xl transition-colors shadow-sm flex items-center gap-2 font-medium mr-1"
          >
            <span>Run Task</span>
            <Send size={18} />
          </button>
        </form>
      </div>

      <div className="w-full mt-12">
        <p className="text-sm font-medium text-slate-400 uppercase tracking-wider mb-4 px-2">Suggestions</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {suggestions.map((s, idx) => (
            <button
              key={idx}
              onClick={() => handleSubmit(s.text)}
              disabled={isSubmitting}
              className="flex items-center gap-3 p-4 bg-white border border-slate-200 rounded-xl hover:border-blue-300 hover:shadow-md transition-all text-left text-slate-700 hover:text-slate-900 group"
            >
              <div className="bg-slate-50 p-2 rounded-lg group-hover:bg-blue-50 transition-colors">
                {s.icon}
              </div>
              <span className="font-medium text-sm">{s.text}</span>
            </button>
          ))}
        </div>
      </div>

    </div>
  );
};
