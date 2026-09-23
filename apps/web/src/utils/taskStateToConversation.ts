export interface ConversationStep {
  id: string;
  label: string;
  state: 'pending' | 'active' | 'completed' | 'error' | 'warning';
  message?: string;
}

export function translateTaskState(
  status: string,
  events: { type: string; status?: string; payload?: any }[]
): ConversationStep[] {
  const steps: ConversationStep[] = [];

  // 1. Goal Understood
  const understood = events.find(e => e.type === 'GOAL_UNDERSTOOD');
  if (understood) {
    steps.push({
      id: 'understand',
      label: 'Understanding your request',
      state: 'completed'
    });
  } else if (status === 'UNDERSTANDING' || status === 'IDLE') {
    steps.push({
      id: 'understand',
      label: 'Understanding your request...',
      state: 'active'
    });
    return steps;
  }

  // 2. Planning
  const planCreated = events.find(e => e.type === 'PLAN_CREATED');
  if (planCreated) {
    steps.push({
      id: 'plan',
      label: 'Creating a safe execution plan',
      state: 'completed'
    });
  } else if (status === 'PLANNING' || status === 'REPLANNING') {
    steps.push({
      id: 'plan',
      label: 'Creating a safe execution plan...',
      state: 'active'
    });
    return steps;
  }

  // 3. Safety Check
  const policyCheck = events.find(e => e.type === 'POLICY_CHECKED');
  if (status === 'WAITING_APPROVAL') {
    steps.push({
      id: 'safety',
      label: 'Safety check paused',
      state: 'warning',
      message: 'This task requires your explicit approval to proceed.'
    });
    return steps; // Halt rendering future steps
  } else if (policyCheck) {
    steps.push({
      id: 'safety',
      label: 'Safety check passed',
      state: 'completed'
    });
  } else if (status === 'POLICY_CHECK') {
    steps.push({
      id: 'safety',
      label: 'Checking safety policies...',
      state: 'active'
    });
    return steps;
  }

  // 4. Execution
  const actionStarted = events.find(e => e.type === 'ACTION_STARTED');
  const actionExecuted = [...events].reverse().find(e => e.type === 'ACTION_EXECUTED');

  if (status === 'EXECUTING') {
    steps.push({
      id: 'execute',
      label: actionStarted?.payload?.action_type
        ? `Running ${actionStarted.payload.action_type}...`
        : 'Executing plan...',
      state: 'active',
      message: actionStarted?.payload?.description
    });
    return steps;
  } else if (actionExecuted && status !== 'RETRYING') {
    steps.push({
      id: 'execute',
      label: 'Executed plan',
      state: 'completed'
    });
  } else if (status === 'RETRYING') {
    steps.push({
      id: 'execute',
      label: 'Encountered an issue, retrying...',
      state: 'warning'
    });
    return steps;
  }

  // 5. Verification
  if (status === 'VERIFYING') {
    steps.push({
      id: 'verify',
      label: 'Verifying results...',
      state: 'active'
    });
    return steps;
  }

  // 6. Rollback
  if (status === 'ROLLING_BACK') {
    steps.push({
      id: 'rollback',
      label: 'Restoring previous state...',
      state: 'warning'
    });
    return steps;
  } else if (status === 'ROLLED_BACK') {
    steps.push({
      id: 'rollback',
      label: 'Rolled back safely',
      state: 'warning',
      message: 'LinuxPilot restored your system to its previous state.'
    });
    return steps;
  }

  // Final states
  if (status === 'COMPLETED') {
    const verified = events.find(e => e.type === 'VERIFICATION_COMPLETED');
    if (verified) {
      steps.push({
        id: 'verify',
        label: 'Verified results',
        state: 'completed'
      });
    }
    steps.push({
      id: 'done',
      label: 'Task completed successfully',
      state: 'completed'
    });
  } else if (status === 'FAILED') {
    steps.push({
      id: 'done',
      label: 'Task failed',
      state: 'error',
      message: 'LinuxPilot encountered an unrecoverable error.'
    });
  }

  return steps;
}
