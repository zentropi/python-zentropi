import subprocess
from zentropi import Agent

a = Agent('intel-backlight')


@a.on_event('intel-backlight')
async def backlight(frame):
    value = frame.data.get("value")
    subprocess.run(['intel_backlight', str(value)])


a.run(
    'ws://localhost:26514/',
    token='test-token',
)
