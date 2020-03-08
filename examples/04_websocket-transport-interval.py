from zentropi import Agent

a = Agent('test-agent')


@a.on_interval('test', 2)
async def test(frame):
    await a.event('test')


@a.on_event('test')
async def hello(frame):
    print('Hello, world.')


a.run('ws://localhost:26514/', 'test-token')
