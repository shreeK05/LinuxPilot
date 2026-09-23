import React from 'react';
import { translateTaskState, type ConversationStep } from '../utils/taskStateToConversation';
import { CheckCircle2, CircleDashed, AlertCircle, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react';

interface TaskConversationProps {
  task: any;
  auditEvents: any[];
  onAdvancedDetailsToggle: () => void;
  showAdvanced: boolean;
}

export const TaskConversation: React.FC<TaskConversationProps> = ({
  task,
  auditEvents,
  onAdvancedDetailsToggle,
  showAdvanced
}) => {
  const steps = translateTaskState(task.status, auditEvents);

  const getStepIcon = (state: ConversationStep['state']) => {
    switch(state) {
      case 'completed': return <CheckCircle2 size={24} className="text-green-500" />;
      case 'active': return <CircleDashed size={24} className="text-blue-500 animate-spin-slow" />;
      case 'warning': return <AlertTriangle size={24} className="text-amber-500" />;
      case 'error': return <AlertCircle size={24} className="text-red-500" />;
      default: return <CircleDashed size={24} className="text-slate-300" />;
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto animation-fade-in mt-8">
      {/* Initial Prompt Bubble */}
      <div className="flex justify-end mb-8">
        <div className="bg-blue-600 text-white rounded-2xl rounded-tr-sm px-6 py-4 shadow-sm max-w-[80%]">
          <p className="text-sm font-medium opacity-70 mb-1">You</p>
          <p className="text-lg leading-relaxed">{task.goal}</p>
        </div>
      </div>

      {/* LinuxPilot Response Area */}
      <div className="flex gap-4 mb-8">
        <div className="flex-shrink-0 mt-1">
          <div className="w-10 h-10 bg-slate-900 rounded-xl flex items-center justify-center text-white shadow-md">
            <span className="font-bold text-lg">LP</span>
          </div>
        </div>
        <div className="flex-1 bg-white border border-slate-200 rounded-2xl rounded-tl-sm shadow-sm overflow-hidden">
          <div className="p-6">
            <p className="text-sm font-medium text-slate-500 mb-6">
              {task.status === 'COMPLETED' ? 'Task completed successfully' :
               task.status === 'FAILED' ? 'Task failed' :
               task.status === 'WAITING_APPROVAL' ? 'Waiting for your approval' :
               'LinuxPilot is processing your request'}
            </p>

            <div className="space-y-6">
              {steps.map((step, idx) => (
                <div key={step.id} className="flex gap-4 relative">
                  {/* Connecting line */}
                  {idx < steps.length - 1 && (
                    <div className="absolute left-[11px] top-8 bottom-[-24px] w-0.5 bg-slate-100"></div>
                  )}

                  <div className="flex-shrink-0 bg-white z-10 pt-0.5">
                    {getStepIcon(step.state)}
                  </div>

                  <div className="flex-1 pb-1">
                    <p className={`text-base font-medium ${step.state === 'active' ? 'text-blue-900' : 'text-slate-700'}`}>
                      {step.label}
                    </p>
                    {step.message && (
                      <p className={`mt-1 text-sm ${step.state === 'error' ? 'text-red-600' : step.state === 'warning' ? 'text-amber-600' : 'text-slate-500'}`}>
                        {step.message}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div
            className="bg-slate-50 px-6 py-3 border-t border-slate-100 flex items-center justify-between cursor-pointer hover:bg-slate-100 transition-colors"
            onClick={onAdvancedDetailsToggle}
          >
            <span className="text-sm font-medium text-slate-600">Advanced Details</span>
            {showAdvanced ? <ChevronUp size={18} className="text-slate-400" /> : <ChevronDown size={18} className="text-slate-400" />}
          </div>
        </div>
      </div>
    </div>
  );
};
