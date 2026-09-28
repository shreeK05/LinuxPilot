import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Send, Terminal, FolderOpen, Search, Copy, CheckCircle2 } from 'lucide-react';
import { motion } from 'framer-motion';
import { fetchWithAuth } from '../utils/api';
import { cn } from '../utils/cn';

export const Home: React.FC<{ apiUrl: string }> = ({ apiUrl }) => {
  const [goal, setGoal] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const navigate = useNavigate();

  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent | string) => {
    if (typeof e !== 'string') e.preventDefault();
    setErrorMsg(null);

    const text = typeof e === 'string' ? e : goal;
    if (!text.trim()) return;

    setIsSubmitting(true);
    try {
      const res = await fetchWithAuth(`${apiUrl}/tasks/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal: text.trim(), risk_level: 1 })
      });

      if (!res.ok) {
        if (res.status === 401) throw new Error("Your session has expired. Please sign in again.");
        if (res.status === 403) throw new Error("LinuxPilot rejected this request because the requested path is protected.");
        throw new Error("Task creation failed. Please try again.");
      }

      const data = await res.json();
      await fetchWithAuth(`${apiUrl}/tasks/${data.id}/execute`, { method: 'POST' });

      navigate(`/tasks/${data.id}`);
    } catch (err: any) {
      console.error(err);
      if (err.message === "Failed to fetch") {
        setErrorMsg("Backend is unavailable. Please start the LinuxPilot API server and try again.");
      } else {
        setErrorMsg(err.message || "An unexpected error occurred.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const suggestions = [
    { text: "Find all PDF files in Downloads", icon: <Search size={18} className="text-brand-500" /> },
    { text: "Organize my Downloads folder", icon: <FolderOpen size={18} className="text-purple-500" /> },
    { text: "Show me files modified today", icon: <CheckCircle2 size={18} className="text-success-500" /> },
    { text: "Find duplicate files", icon: <Copy size={18} className="text-amber-500" /> }
  ];

  return (
    <div className="flex flex-col items-center justify-center min-h-[80vh] w-full max-w-3xl mx-auto">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="flex flex-col items-center mb-10 text-center"
      >
        <div className="w-16 h-16 bg-brand-600/20 border border-brand-500/30 rounded-2xl flex items-center justify-center text-brand-400 mb-6 glow-primary">
          <Terminal size={32} />
        </div>
        <h1 className="text-4xl md:text-5xl font-bold text-white tracking-tight mb-4">
          What can I help you with?
        </h1>
        <p className="text-lg text-text-muted max-w-lg mx-auto">
          LinuxPilot understands, plans, and executes system tasks autonomously.
        </p>
      </motion.div>

      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, delay: 0.1, ease: "easeOut" }}
        className="w-full relative group"
      >
        {errorMsg && (
          <div className="absolute -top-12 left-0 right-0 bg-danger-500/10 border border-danger-500/20 text-danger-400 text-sm py-2 px-4 rounded-lg flex items-center justify-center">
            {errorMsg}
          </div>
        )}
        <div className="absolute -inset-1 bg-gradient-to-r from-brand-600 to-purple-600 rounded-2xl blur-lg opacity-30 group-hover:opacity-50 transition duration-500"></div>
        <form
          onSubmit={handleSubmit}
          className="relative bg-surface-900/80 backdrop-blur-xl flex items-center p-2 rounded-2xl border border-white/10"
        >
          <input
            type="text"
            className="flex-1 bg-transparent px-4 py-4 text-lg outline-none text-white placeholder-text-muted"
            placeholder="Describe your goal in natural language..."
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            disabled={isSubmitting}
            autoFocus
          />
          <button
            type="submit"
            disabled={!goal.trim() || isSubmitting}
            className={cn(
              "p-4 rounded-xl transition-all duration-300 flex items-center justify-center",
              goal.trim() && !isSubmitting 
                ? "bg-brand-600 hover:bg-brand-500 text-white shadow-[0_0_15px_rgba(37,99,235,0.5)]" 
                : "bg-surface-700 text-text-muted cursor-not-allowed"
            )}
          >
            {isSubmitting ? (
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <Send size={20} />
            )}
          </button>
        </form>
      </motion.div>

      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.3 }}
        className="w-full mt-12"
      >
        <p className="text-xs font-semibold text-text-muted uppercase tracking-widest mb-4 px-2">Example Tasks</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {suggestions.map((s, idx) => (
            <button
              key={idx}
              onClick={() => handleSubmit(s.text)}
              disabled={isSubmitting}
              className="flex items-center gap-4 p-4 glass-card hover:bg-surface-700/80 hover:border-brand-500/50 transition-all text-left group rounded-xl"
            >
              <div className="bg-surface-800 p-2.5 rounded-lg border border-white/5 group-hover:border-brand-500/30 transition-colors">
                {s.icon}
              </div>
              <span className="font-medium text-sm text-text-main group-hover:text-white transition-colors">{s.text}</span>
            </button>
          ))}
        </div>
      </motion.div>
    </div>
  );
};
