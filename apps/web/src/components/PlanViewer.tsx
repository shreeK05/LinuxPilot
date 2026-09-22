import type { FC } from 'react';

interface ActionDefinition {
  action_type: string;
  parameters: any;
  risk_level: number;
}

interface PlanStep {
  step_id: string;
  name: string;
  dependencies: string[];
  action: ActionDefinition;
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

const getRiskColor = (level: number) => {
  switch(level) {
    case 0: return 'bg-green-100 text-green-800';
    case 1: return 'bg-blue-100 text-blue-800';
    case 2: return 'bg-yellow-100 text-yellow-800';
    case 3: return 'bg-orange-100 text-orange-800';
    case 4: return 'bg-red-100 text-red-800';
    default: return 'bg-gray-100 text-gray-800';
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

export const PlanViewer: FC<PlanViewerProps> = ({ plan }) => {
  if (!plan || !plan.steps || plan.steps.length === 0) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 text-center text-gray-500">
        No execution plan available yet.
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      <div className="bg-gray-50 px-4 py-3 border-b border-gray-200 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
        <div>
            <h3 className="font-semibold text-gray-800">Execution Plan DAG</h3>
            {(plan.version !== undefined && plan.version > 1) && (
              <span className="text-sm font-medium text-purple-600 ml-0 sm:ml-2">
                Version {plan.version} (Replans: {plan.replan_count}/2)
              </span>
            )}
        </div>
        <span className={`px-2 py-1 rounded text-xs font-medium ${getRiskColor(plan.risk_level)}`}>
          Max Risk: {getRiskLabel(plan.risk_level)}
        </span>
      </div>
      <div className="p-4 space-y-4">
        {plan.steps.map((step, idx) => (
          <div key={step.step_id} className="relative pl-8">
            {/* simple visual line for DAG sequence */}
            {idx !== plan.steps.length - 1 && (
              <div className="absolute left-3 top-8 bottom-0 w-px bg-gray-300 -mb-8"></div>
            )}
            <div className="absolute left-1.5 top-2 w-3 h-3 rounded-full bg-blue-500 border-2 border-white shadow-sm z-10"></div>
            
            <div className="bg-gray-50 rounded border border-gray-100 p-3 hover:shadow-sm transition-shadow">
              <div className="flex justify-between items-start mb-2">
                <div>
                  <span className="text-xs font-mono text-gray-400 block mb-0.5">{step.step_id}</span>
                  <h4 className="font-medium text-gray-800">{step.name}</h4>
                </div>
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${getRiskColor(step.action.risk_level)}`}>
                  {getRiskLabel(step.action.risk_level)}
                </span>
              </div>
              
              <div className="text-sm text-gray-600 font-mono bg-white p-2 rounded border border-gray-100 mt-2">
                {step.action.action_type}
              </div>
              
              {step.dependencies.length > 0 && (
                <div className="mt-2 text-xs text-gray-500">
                  <span className="font-medium">Depends on:</span> {step.dependencies.join(', ')}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
