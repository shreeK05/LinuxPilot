import React from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { Terminal, Home, ListTodo, ShieldAlert, LogOut } from 'lucide-react';

interface LayoutProps {
  health: string;
  onLogout: () => void;
}

export const Layout: React.FC<LayoutProps> = ({ health, onLogout }) => {
  const navigate = useNavigate();

  const handleLogout = () => {
    onLogout();
    navigate('/');
  };

  return (
    <div className="flex h-screen bg-slate-50 text-slate-900 font-sans">
      {/* Sidebar Navigation */}
      <nav className="w-64 bg-slate-900 text-slate-300 flex flex-col shadow-xl flex-shrink-0">
        <div className="p-6 flex items-center gap-3">
          <div className="bg-blue-600 p-2 rounded-lg text-white">
            <Terminal size={24} />
          </div>
          <span className="text-xl font-bold text-white tracking-wide">LinuxPilot</span>
        </div>

        <div className="flex-1 px-4 space-y-2 mt-4">
          <NavLink
            to="/"
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                isActive ? 'bg-blue-600/10 text-blue-400 font-medium' : 'hover:bg-slate-800 hover:text-white'
              }`
            }
          >
            <Home size={20} />
            Home
          </NavLink>

          <NavLink
            to="/tasks"
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                isActive ? 'bg-blue-600/10 text-blue-400 font-medium' : 'hover:bg-slate-800 hover:text-white'
              }`
            }
          >
            <ListTodo size={20} />
            History
          </NavLink>

          <NavLink
            to="/approvals"
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                isActive ? 'bg-amber-500/10 text-amber-400 font-medium' : 'hover:bg-slate-800 hover:text-white'
              }`
            }
          >
            <ShieldAlert size={20} />
            Approvals
          </NavLink>
        </div>

        {/* Status & Profile Section */}
        <div className="p-4 border-t border-slate-800 space-y-4">
          <div className="flex items-center justify-between px-2">
            <span className="text-xs uppercase tracking-wider text-slate-500 font-semibold">API Status</span>
            <span className={`w-2 h-2 rounded-full ${health === 'ok' ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]' : 'bg-red-500'}`} />
          </div>

          <div className="flex items-center justify-between bg-slate-800 p-3 rounded-xl border border-slate-700">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-gradient-to-tr from-blue-500 to-purple-500 rounded-full flex items-center justify-center text-white font-bold text-sm">
                U
              </div>
              <div className="flex flex-col">
                <span className="text-sm font-medium text-white leading-tight">User</span>
                <span className="text-xs text-slate-400">Owner</span>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="text-slate-400 hover:text-white transition-colors"
              title="Logout"
            >
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-hidden bg-slate-50 relative">
        {/* We can put a subtle gradient mesh in the background if we want, but let's keep it clean */}
        <div className="flex-1 overflow-y-auto p-8 lg:p-12">
          <div className="max-w-5xl mx-auto">
            <Outlet />
          </div>
        </div>
      </main>
    </div>
  );
};
