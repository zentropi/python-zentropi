from zentropi import Agent

a = Agent('test-agent')


@a.on_event('startup')
async def startup(frame):
    await a.join('home')


@a.on_interval('test', 0.9)
async def test(frame):
    await a.event('hello')


@a.on_event('hello')
async def hello(frame):
    space_name = frame.meta.get("space").get("name")
    print(f'Hello, {space_name}.')


@a.on_interval('hop_spaces', 1)
async def hop_spaces(frame):
    if frame.data.get('count') == 3:
        await a.leave('home')
        await a.join('work')
    if frame.data.get('count') == 6:
        await a.leave('work')
        await a.join('home')
    if frame.data.get('count') == 9:
        a.stop()


a.run(
    'ws://localhost:26514/',
    token='test-token',
    join_spaces=False,
)
