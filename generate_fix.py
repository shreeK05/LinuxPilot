import base64

with open(r'd:\3rd Year I Sem\LinuxPilot\apps\api\app\agent\orchestrator.py', 'rb') as f:
    orch_b64 = base64.b64encode(f.read()).decode('utf-8')

with open(r'd:\3rd Year I Sem\LinuxPilot\apps\api\app\agent\actions\registry.py', 'rb') as f:
    reg_b64 = base64.b64encode(f.read()).decode('utf-8')

script = f'''import base64
with open('app/agent/actions/registry.py', 'wb') as f:
    f.write(base64.b64decode(b"{reg_b64}"))
with open('app/agent/orchestrator.py', 'wb') as f:
    f.write(base64.b64decode(b"{orch_b64}"))
print("Files successfully restored!")
'''
with open(r'd:\3rd Year I Sem\LinuxPilot\fix_script.txt', 'w', encoding='utf-8') as f:
    f.write(script)
