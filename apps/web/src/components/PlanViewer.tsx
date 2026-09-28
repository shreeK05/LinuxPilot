import type { FC } from 'react';
import { motion } from 'framer-motion';
import { Network, ArrowRight } from 'lucide-react';
import { cn } from '../utils/cn';

interface ActionDefinition {
  action_type: string;
  parameters: any;
  risk_level: number;
}

interface PlanStep {
  step_id: string;
  logical_step_id?: string;
  name: string;
  dependencies: string[];
  action: ActionDefinition;
  status?: string;
  result?: any;
  verification?: any;
}

interface ExecutionPlan {
  plan_id: string;
  version?: number;
  replan_count?: number;
  steps: PlanStep[];
  risk_level: number;
}

interface PlanViewerProps {
  plan: ExecutionPlan | null;
}

const getRiskStyle = (level: number) => {
  switch(level) {
    case 0: return 'text-success-400 bg-success-500/10 border-success-500/20';
    case 1: return 'text-brand-400 bg-brand-500/10 border-brand-500/20';
    case 2: return 'text-warning-400 bg-warning-500/10 border-warning-500/20';
    case 3: return 'text-orange-400 bg-orange-500/10 border-orange-500/20';
    case 4: return 'text-danger-400 bg-danger-500/10 border-danger-500/20';
    default: return 'text-text-muted bg-surface-700/50 border-white/10';
  }
};

const getRiskLabel = (level: number) => {
  switch(level) {
    case 0: return 'LEVEL_0_READ';
    case 1: return 'LEVEL_1_LOW';
    case 2: return 'LEVEL_2_REVERSIBLE';
    case 3: return 'LEVEL_3_HIGH_IMPACT';
    case 4: return 'LEVEL_4_DESTRUCTIVE';
    default: return 'UNKNOWN';
  }
};

const getStatusStyle = (status?: string) => {
  if (!status || status === 'Not executed') return 'text-surface-400 bg-surface-800/50 border-surface-700';
  if (status === 'SUCCESS' || status === 'COMPLETED') return 'text-success-400 bg-success-500/10 border-success-500/30';
  if (status === 'FAILED') return 'text-danger-400 bg-danger-500/10 border-danger-500/30';
  if (status === 'EXECUTING') return 'text-brand-400 bg-brand-500/10 border-brand-500/30';
  return 'text-surface-400 bg-surface-800/50 border-surface-700';
};

export const PlanViewer: FC<PlanViewerProps> = ({ plan }) => {
  if (!plan || !plan.steps || plan.steps.length === 0) {
    return (
      <div className="bg-surface-800 border border-white/5 rounded-xl p-8 text-center text-text-muted">
        <Network size={24} className="mx-auto mb-3 opacity-50" />
        No execution plan available yet.
      </div>
    );
  }

  return (
    <div className="bg-surface-900 border border-white/5 rounded-xl overflow-hidden shadow-xl">
      <div className="bg-surface-800 px-5 py-4 border-b border-white/5 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div>
          <h3 className="font-semibold text-white tracking-wide flex items-center gap-2">
            <Network size={18} className="text-brand-400" />
            Execution Plan DAG
          </h3>
          {(plan.version !== undefined && plan.version > 1) && (
            <span className="text-xs font-semibold text-brand-400 uppercase tracking-widest mt-1 block">
              Version {plan.version} (Replans: {plan.replan_count}/2)
            </span>
          )}
        </div>
        <span className={cn("px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-widest border", getRiskStyle(plan.risk_level))}>
          Max Risk: {getRiskLabel(plan.risk_level)}
        </span>
      </div>
      
      <div className="p-5 sm:p-6 space-y-6">
        {plan.steps.map((step, idx) => (
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.1 }}
            key={step.step_id} 
            className="relative pl-10"
          >
            {/* DAG Line */}
            {idx !== plan.steps.length - 1 && (
              <div className="absolute left-4 top-8 bottom-0 w-0.5 bg-surface-700 -mb-8"></div>
            )}
            
            {/* Node Dot */}
            <div className="absolute left-[13px] top-3 w-2.5 h-2.5 rounded-full bg-brand-500 border border-surface-900 shadow-[0_0_8px_rgba(59,130,246,0.6)] z-10"></div>
            
            <div className="glass-panel rounded-xl p-4 sm:p-5 hover:bg-surface-800/80 hover:border-white/10 transition-colors">
              <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-3 mb-4">
                <div>
                  <div className="flex gap-2 items-center mb-2">
                    <span className="text-[11px] font-bold font-mono text-brand-500 bg-brand-500/10 px-2 py-0.5 rounded uppercase tracking-wider block w-max">
                      {step.logical_step_id || step.step_id}
                    </span>
                    <span className={cn("text-[10px] px-2 py-0.5 rounded font-bold uppercase tracking-widest border", getStatusStyle(step.status))}>
                      {step.status || 'Not executed'}
                    </span>
                  </div>
                  <h4 className="font-semibold text-white">{step.name}</h4>
                </div>
                <span className={cn("text-[10px] px-2 py-1 rounded font-bold uppercase tracking-widest border", getRiskStyle(step.action.risk_level))}>
                  {getRiskLabel(step.action.risk_level)}
                </span>
              </div>
              
              <div className="bg-surface-900/80 rounded-lg p-3 font-mono text-sm border border-surface-700/50 shadow-inner overflow-x-auto">
                <div className="text-brand-300 font-bold mb-1 flex items-center gap-2">
                  <ArrowRight size={14} />
                  {step.action.action_type}
                </div>
                {step.action.parameters && Object.keys(step.action.parameters).length > 0 && (
                  <pre className="text-text-muted mt-2 text-xs leading-relaxed">
                    {JSON.stringify(step.action.parameters, null, 2)}
                  </pre>
                )}
              </div>
              
              {step.result && (
                <div className="mt-4 bg-success-500/5 rounded-lg p-3 border border-success-500/10 shadow-inner overflow-x-auto">
                  <h5 className="text-[10px] font-bold text-success-400 uppercase tracking-widest mb-2">Execution Result</h5>
                  <pre className="text-text-main text-xs font-mono leading-relaxed">
                    {typeof step.result === 'string' ? step.result : JSON.stringify(step.result, null, 2)}
                  </pre>
                </div>
              )}

              {step.verification && step.verification !== 'Not verified' && (
                <div className={cn("mt-4 rounded-lg p-3 border shadow-inner overflow-x-auto", 
                  step.verification.passed ? "bg-success-500/5 border-success-500/10" : "bg-danger-500/5 border-danger-500/10"
                )}>
                  <h5 className={cn("text-[10px] font-bold uppercase tracking-widest mb-2",
                    step.verification.passed ? "text-success-400" : "text-danger-400"
                  )}>
                    Verification {step.verification.passed ? "Passed" : "Failed"}
                  </h5>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
                    <div>
                      <p className="text-text-muted mb-1 text-[10px] uppercase">Expected</p>
                      <pre className="text-text-main">{JSON.stringify(step.verification.expected, null, 2)}</pre>
                    </div>
                    <div>
                      <p className="text-text-muted mb-1 text-[10px] uppercase">Actual</p>
                      <pre className="text-text-main">{JSON.stringify(step.verification.actual, null, 2)}</pre>
                    </div>
                  </div>
                </div>
              )}
              
              {step.dependencies.length > 0 && (
                <div className="mt-4 text-xs font-medium text-text-muted flex items-center gap-2">
                  <span className="uppercase tracking-widest text-surface-500 font-bold text-[10px]">Depends on:</span> 
                  <div className="flex gap-1.5 flex-wrap">
                    {step.dependencies.map(dep => (
                      <span key={dep} className="bg-surface-800 border border-white/5 px-2 py-0.5 rounded text-text-main">
                        {dep}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};
