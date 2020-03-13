import subprocess
from zentropi import Agent

a = Agent('translate-events')


@a.on_event('*')
async def translate_events(frame):
    if frame.name == 'random-value':
        await a.event('intel-backlight', **frame.data)


a.run(
    'ws://localhost:26514/',
    token='test-token',
)
