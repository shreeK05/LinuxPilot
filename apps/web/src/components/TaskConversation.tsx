import React from 'react';
import { translateTaskState, type ConversationStep } from '../utils/taskStateToConversation';
import { CheckCircle2, CircleDashed, AlertCircle, AlertTriangle, ChevronDown, ChevronUp, Terminal } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '../utils/cn';

interface TaskConversationProps {
  task: any;
  auditEvents: any[];
  onAdvancedDetailsToggle: () => void;
  showAdvanced: boolean;
  plan?: any;
}

export const TaskConversation: React.FC<TaskConversationProps> = ({
  task,
  auditEvents,
  onAdvancedDetailsToggle,
  showAdvanced,
  plan
}) => {
  const steps = translateTaskState(task.status, auditEvents);

  const getStepIcon = (state: ConversationStep['state']) => {
    switch(state) {
      case 'completed': return <CheckCircle2 size={24} className="text-success-500" />;
      case 'active': return <CircleDashed size={24} className="text-brand-500 animate-spin-slow glow-primary rounded-full" />;
      case 'warning': return <AlertTriangle size={24} className="text-warning-500" />;
      case 'error': return <AlertCircle size={24} className="text-danger-500 glow-danger rounded-full" />;
      default: return <CircleDashed size={24} className="text-surface-600" />;
    }
  };

  let finalResult: string | null = null;
  if (task.status === 'COMPLETED') {
    const completedActions = auditEvents.filter(e => e.event_type === 'ACTION_COMPLETED' && e.status === 'SUCCESS');
    if (completedActions.length > 0) {
      const lastAction = completedActions[completedActions.length - 1];
      if (lastAction.metadata && lastAction.metadata.output) {
        const out = lastAction.metadata.output;
        if (typeof out === 'string') {
          finalResult = out;
        } else if (out.stdout) {
          finalResult = out.stdout;
        } else {
          finalResult = JSON.stringify(out, null, 2);
        }
      }
    }
    
    if (!finalResult && plan?.steps?.length > 0) {
      const lastStep = plan.steps[plan.steps.length - 1];
      if (lastStep.result) {
        if (typeof lastStep.result === 'string') {
          finalResult = lastStep.result;
        } else if (lastStep.result.stdout) {
          finalResult = lastStep.result.stdout;
        } else {
          finalResult = JSON.stringify(lastStep.result, null, 2);
        }
      }
    }
  }

  return (
    <div className="w-full max-w-2xl mx-auto mt-8">
      {/* Initial Prompt Bubble */}
      <motion.div 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex justify-end mb-8"
      >
        <div className="bg-brand-600 text-white rounded-3xl rounded-tr-sm px-6 py-4 shadow-lg shadow-brand-500/20 max-w-[85%] border border-brand-500/50">
          <p className="text-xs font-semibold text-brand-200 uppercase tracking-widest mb-1.5">You</p>
          <p className="text-lg leading-relaxed">{task.goal}</p>
        </div>
      </motion.div>

      {/* LinuxPilot Response Area */}
      <motion.div 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="flex gap-4 mb-8"
      >
        <div className="flex-shrink-0 mt-1">
          <div className="w-10 h-10 bg-surface-900 border border-brand-500/30 rounded-xl flex items-center justify-center text-brand-400 shadow-md glow-primary">
            <Terminal size={20} />
          </div>
        </div>
        
        <div className="flex-1 glass-card rounded-2xl rounded-tl-sm shadow-xl overflow-hidden border-surface-700">
          <div className="p-6 sm:p-8">
            <div className="flex items-center gap-3 mb-8 pb-4 border-b border-white/5">
              <span className={cn(
                "relative flex h-3 w-3",
                task.status === 'COMPLETED' ? "hidden" : "flex"
              )}>
                {task.status !== 'FAILED' && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-75"></span>}
                <span className={cn(
                  "relative inline-flex rounded-full h-3 w-3",
                  task.status === 'FAILED' ? "bg-danger-500" : "bg-brand-500"
                )}></span>
              </span>
              <p className="text-sm font-semibold text-text-muted uppercase tracking-widest">
                {task.status === 'COMPLETED' ? 'Task completed successfully' :
                 task.status === 'FAILED' ? 'Task failed' :
                 task.status === 'WAITING_APPROVAL' ? 'Waiting for your approval' :
                 'LinuxPilot is processing your request'}
              </p>
            </div>

            <div className="space-y-6 relative">
              {/* Connecting line background */}
              <div className="absolute left-[11px] top-4 bottom-4 w-px bg-surface-700/50 z-0"></div>
              
              <AnimatePresence initial={false}>
                {steps.map((step, idx) => (
                  <motion.div 
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.1 }}
                    key={step.id} 
                    className="flex gap-5 relative z-10"
                  >
                    <div className="flex-shrink-0 bg-surface-900 rounded-full mt-0.5 relative z-10 border-4 border-surface-900">
                      {getStepIcon(step.state)}
                    </div>

                    <div className="flex-1 pb-2">
                      <p className={cn(
                        "text-base font-medium transition-colors",
                        step.state === 'active' ? "text-white" : 
                        step.state === 'completed' ? "text-text-main" : "text-text-muted"
                      )}>
                        {step.label}
                      </p>
                      {step.message && (
                        <p className={cn(
                          "mt-1.5 text-sm leading-relaxed",
                          step.state === 'error' ? 'text-danger-400' : 
                          step.state === 'warning' ? 'text-warning-400' : 'text-text-muted'
                        )}>
                          {step.message}
                        </p>
                      )}
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>

            {finalResult && (
              <motion.div 
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-8 pt-6 border-t border-white/5"
              >
                <h4 className="text-xs font-semibold text-text-muted uppercase tracking-widest mb-3">Final Result</h4>
                <div className="bg-surface-900/50 rounded-lg p-4 font-mono text-sm text-text-main overflow-x-auto border border-surface-700">
                  {finalResult.trim()}
                </div>
              </motion.div>
            )}
          </div>

          <div
            className="bg-surface-800/80 px-6 py-4 border-t border-white/5 flex items-center justify-between cursor-pointer hover:bg-surface-700 transition-colors"
            onClick={onAdvancedDetailsToggle}
          >
            <span className="text-sm font-medium text-text-muted">Advanced Details</span>
            {showAdvanced ? <ChevronUp size={18} className="text-text-muted" /> : <ChevronDown size={18} className="text-text-muted" />}
          </div>
        </div>
      </motion.div>
    </div>
  );
};

