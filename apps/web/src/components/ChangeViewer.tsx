import type { FC } from 'react';
import { motion } from 'framer-motion';
import { HardDrive, RotateCcw, Plus, Minus, FilePenLine, ArrowRight } from 'lucide-react';
import { cn } from '../utils/cn';

interface FileSnapshot {
  snapshot_id: string;
  original_path: string;
  resulting_path: string | null;
  operation_type: string;
  original_hash: string | null;
  restoration_status: string;
}

interface TaskSnapshot {
  task_id: string;
  created_at: string;
  status: string;
  rollback_status: string | null;
  files: FileSnapshot[];
}

interface ChangeViewerProps {
  snapshot: TaskSnapshot | null;
  onRollback: () => void;
  isRollingBack: boolean;
}

export const ChangeViewer: FC<ChangeViewerProps> = ({ snapshot, onRollback, isRollingBack }) => {
  if (!snapshot) return null;

  return (
    <div className="bg-surface-900 border border-white/5 rounded-xl shadow-xl overflow-hidden">
      <div className="bg-surface-800 px-5 py-4 border-b border-white/5 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h3 className="text-white font-semibold flex items-center gap-2">
            <HardDrive size={18} className="text-brand-400" />
            Snapshot & Changes
          </h3>
          <p className="text-xs text-text-muted mt-1 uppercase tracking-widest font-bold flex items-center gap-2">
            Status: 
            <span className={cn(
              "px-2 py-0.5 rounded",
              snapshot.status === 'ACTIVE' ? "bg-brand-500/10 text-brand-400" :
              snapshot.status === 'ROLLED_BACK' ? "bg-orange-500/10 text-orange-400" :
              "bg-surface-700/50 text-text-muted"
            )}>
              {snapshot.status} {snapshot.rollback_status ? `(${snapshot.rollback_status})` : ''}
            </span>
          </p>
        </div>
        <div>
          <button 
            onClick={onRollback}
            disabled={isRollingBack || snapshot.status === 'ROLLED_BACK'}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all",
              isRollingBack || snapshot.status === 'ROLLED_BACK' 
                ? "bg-surface-800 text-text-muted cursor-not-allowed border border-white/5" 
                : "bg-danger-500/10 text-danger-400 hover:bg-danger-500/20 border border-danger-500/20 hover:border-danger-500/30"
            )}
          >
            <RotateCcw size={16} className={cn(isRollingBack && "animate-spin")} />
            {isRollingBack ? 'Rolling back...' : (snapshot.status === 'ROLLED_BACK' ? 'Rolled Back' : 'Manual Rollback')}
          </button>
        </div>
      </div>
      
      <div className="p-5 sm:p-6">
        {snapshot.files.length === 0 ? (
          <p className="text-sm text-text-muted italic text-center py-4 bg-surface-800/50 rounded-lg border border-white/5">
            No filesystem changes recorded.
          </p>
        ) : (
          <ul className="space-y-3">
            {snapshot.files.map((file, idx) => {
              let icon = <div className="w-4 h-4 rounded-full bg-surface-600" />;
              let badgeColor = "bg-surface-700/50 text-text-muted border-white/10";
              
              if (file.operation_type === "CREATE") {
                icon = <Plus size={14} className="text-success-400" />;
                badgeColor = "bg-success-500/10 text-success-400 border-success-500/20";
              } else if (file.operation_type === "DELETE") {
                icon = <Minus size={14} className="text-danger-400" />;
                badgeColor = "bg-danger-500/10 text-danger-400 border-danger-500/20";
              } else if (file.operation_type === "WRITE") {
                icon = <FilePenLine size={14} className="text-warning-400" />;
                badgeColor = "bg-warning-500/10 text-warning-400 border-warning-500/20";
              } else if (file.operation_type === "MOVE" || file.operation_type === "RENAME") {
                icon = <ArrowRight size={14} className="text-brand-400" />;
                badgeColor = "bg-brand-500/10 text-brand-400 border-brand-500/20";
              }

              return (
                <motion.li 
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  key={idx} 
                  className="flex flex-col gap-2 bg-surface-800 border border-white/5 p-4 rounded-xl hover:bg-surface-700/50 transition-colors"
                >
                  <div className="flex items-center gap-3 font-mono text-sm">
                    <div className={cn("p-1.5 rounded-md border", badgeColor)}>
                      {icon}
                    </div>
                    <span className="text-white truncate" title={file.original_path}>{file.original_path}</span>
                    {file.resulting_path && (
                      <>
                        <ArrowRight size={14} className="text-text-muted shrink-0" />
                        <span className="text-white truncate" title={file.resulting_path}>{file.resulting_path}</span>
                      </>
                    )}
                  </div>
                  
                  <div className="flex flex-wrap gap-4 text-[11px] font-bold uppercase tracking-widest text-text-muted ml-10">
                    <span className="flex items-center gap-1.5 bg-surface-900 px-2 py-1 rounded border border-white/5">
                      Op: <span className={cn(badgeColor.split(' ')[0], badgeColor.split(' ')[1], "px-1 rounded")}>{file.operation_type}</span>
                    </span>
                    
                    {file.original_hash && (
                      <span className="flex items-center gap-1.5 bg-surface-900 px-2 py-1 rounded border border-white/5">
                        Hash: <span className="text-text-main font-mono lowercase tracking-normal">{file.original_hash.substring(0,8)}...</span>
                      </span>
                    )}
                    
                    <span className="flex items-center gap-1.5 bg-surface-900 px-2 py-1 rounded border border-white/5">
                      Rollback: 
                      <span className={cn(
                        "px-1 rounded",
                        file.restoration_status === 'RESTORED' ? 'bg-success-500/10 text-success-400' : 'text-text-main'
                      )}>
                        {file.restoration_status}
                      </span>
                    </span>
                  </div>
                </motion.li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
};
