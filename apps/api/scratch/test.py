import sys
import shlex
import os
sys.path.append(os.getcwd())
from app.agent.sandbox.subprocess_runner import SafeSubprocessRunner
runner = SafeSubprocessRunner()
SafeSubprocessRunner.ALLOWED_COMMANDS.add(sys.executable.replace('\\', '/'))
cmd_str = f"{sys.executable.replace(chr(92), '/')} -c \"print('test string')\""
cmd = shlex.split(cmd_str)
print("CMD:", cmd)
res = runner.run(cmd)
print("RESULT:", res.success, res.output, res.error)
