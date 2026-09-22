import type { FC } from 'react';

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
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm mb-8 overflow-hidden">
      <div className="bg-gray-50 px-4 py-3 border-b border-gray-200 flex justify-between items-center">
        <div>
          <h3 className="text-sm font-semibold text-gray-800">Snapshot & Changes</h3>
          <p className="text-xs text-gray-500 mt-1">Status: {snapshot.status} {snapshot.rollback_status ? `(${snapshot.rollback_status})` : ''}</p>
        </div>
        <div>
          <button 
            onClick={onRollback}
            disabled={isRollingBack || snapshot.status === 'ROLLED_BACK'}
            className="bg-red-50 text-red-600 hover:bg-red-100 px-3 py-1.5 rounded text-xs font-semibold disabled:opacity-50 transition-colors"
          >
            {isRollingBack ? 'Rolling back...' : (snapshot.status === 'ROLLED_BACK' ? 'Rolled Back' : 'Manual Rollback')}
          </button>
        </div>
      </div>
      <div className="p-4">
        {snapshot.files.length === 0 ? (
          <p className="text-sm text-gray-500 italic">No filesystem changes recorded.</p>
        ) : (
          <ul className="space-y-3">
            {snapshot.files.map((file, idx) => {
              let icon = "•";
              let color = "text-gray-500";
              
              if (file.operation_type === "CREATE") {
                icon = "+";
                color = "text-green-600";
              } else if (file.operation_type === "DELETE") {
                icon = "-";
                color = "text-red-600";
              } else if (file.operation_type === "WRITE") {
                icon = "~";
                color = "text-yellow-600";
              } else if (file.operation_type === "MOVE" || file.operation_type === "RENAME") {
                icon = "→";
                color = "text-blue-600";
              }

              return (
                <li key={idx} className="flex flex-col gap-1 text-sm bg-gray-50 p-2 rounded">
                  <div className="flex items-center gap-2 font-mono">
                    <span className={`font-bold ${color} w-4 text-center`}>{icon}</span>
                    <span className="text-gray-700 truncate">{file.original_path}</span>
                    {file.resulting_path && (
                      <>
                        <span className="text-gray-400">→</span>
                        <span className="text-gray-700 truncate">{file.resulting_path}</span>
                      </>
                    )}
                  </div>
                  <div className="flex gap-4 text-xs text-gray-500 ml-6">
                    {file.original_hash && <span title="SHA-256">Hash: {file.original_hash.substring(0,8)}...</span>}
                    <span>Op: {file.operation_type}</span>
                    <span>Rollback Status: <span className={file.restoration_status === 'RESTORED' ? 'text-green-600 font-medium' : ''}>{file.restoration_status}</span></span>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
};
