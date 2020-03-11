from zentropi import Agent

a = Agent('test-agent')


@a.on_event('startup')
async def startup(frame):
    await a.event('hello')


@a.on_event('hello')
async def hello(frame):
    print('Hello, world.')
    a.stop()


a.run(
    'ws://localhost:26514/',
    'test-token',
)
