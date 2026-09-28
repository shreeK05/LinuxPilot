import React, { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { Terminal, Home, ListTodo, ShieldAlert, LogOut, Menu, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '../utils/cn';

interface LayoutProps {
  health: string;
  onLogout: () => void;
}

export const Layout: React.FC<LayoutProps> = ({ health, onLogout }) => {
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = () => {
    onLogout();
    navigate('/');
  };

  const navItems = [
    { to: "/", icon: <Home size={20} />, label: "Home" },
    { to: "/tasks", icon: <ListTodo size={20} />, label: "History" },
    { to: "/approvals", icon: <ShieldAlert size={20} />, label: "Approvals" },
  ];

  const sidebarContent = (
    <>
      <div className="p-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="bg-brand-600 p-2 rounded-xl text-white shadow-lg glow-primary">
            <Terminal size={24} />
          </div>
          <span className="text-xl font-bold text-white tracking-wider">LinuxPilot</span>
        </div>
        {/* Mobile close button */}
        <button className="md:hidden text-text-muted hover:text-white" onClick={() => setMobileMenuOpen(false)}>
          <X size={24} />
        </button>
      </div>

      <div className="flex-1 px-4 space-y-2 mt-4">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            onClick={() => setMobileMenuOpen(false)}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200",
                isActive 
                  ? "bg-brand-500/10 text-brand-500 font-medium border border-brand-500/20" 
                  : "text-text-muted hover:bg-surface-700/50 hover:text-white border border-transparent"
              )
            }
          >
            {item.icon}
            {item.label}
          </NavLink>
        ))}
      </div>

      <div className="p-4 border-t border-surface-700/50 space-y-4">
        <div className="flex items-center justify-between px-2">
          <span className="text-xs uppercase tracking-widest text-text-muted font-semibold">API Status</span>
          <span className={cn(
            "w-2 h-2 rounded-full",
            health === 'ok' ? "bg-success-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]" : "bg-danger-500 glow-danger"
          )} />
        </div>

        <div className="flex items-center justify-between glass-card p-3 rounded-xl">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-tr from-brand-500 to-purple-600 rounded-full flex items-center justify-center text-white font-bold text-sm">
              U
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-medium text-white leading-tight">User</span>
              <span className="text-xs text-text-muted">Admin</span>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="text-text-muted hover:text-white transition-colors"
            title="Logout"
          >
            <LogOut size={18} />
          </button>
        </div>
      </div>
    </>
  );

  return (
    <div className="flex h-screen bg-surface-900 text-text-main font-sans overflow-hidden">
      
      {/* Desktop Sidebar */}
      <nav className="hidden md:flex flex-col w-72 glass-panel border-r-0 flex-shrink-0 z-20">
        {sidebarContent}
      </nav>

      {/* Mobile Top Bar */}
      <div className="md:hidden fixed top-0 left-0 right-0 h-16 glass-panel flex items-center justify-between px-4 z-30">
        <div className="flex items-center gap-2">
          <Terminal size={20} className="text-brand-500" />
          <span className="font-bold text-white tracking-wide">LinuxPilot</span>
        </div>
        <button className="text-text-muted hover:text-white" onClick={() => setMobileMenuOpen(true)}>
          <Menu size={24} />
        </button>
      </div>

      {/* Mobile Sidebar Overlay */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <>
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 md:hidden"
              onClick={() => setMobileMenuOpen(false)}
            />
            <motion.nav
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", bounce: 0, duration: 0.3 }}
              className="fixed inset-y-0 left-0 w-3/4 max-w-sm glass-panel border-r border-surface-700/50 z-50 flex flex-col md:hidden"
            >
              {sidebarContent}
            </motion.nav>
          </>
        )}
      </AnimatePresence>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col relative w-full h-full pt-16 md:pt-0 overflow-hidden">
        {/* Ambient background glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-brand-500/10 rounded-full blur-[120px] pointer-events-none -z-10" />
        
        <div className="flex-1 overflow-y-auto hide-scrollbar p-4 sm:p-8 lg:p-12 relative z-0">
          <div className="max-w-5xl mx-auto h-full">
            <Outlet />
          </div>
        </div>
      </main>
    </div>
  );
};
