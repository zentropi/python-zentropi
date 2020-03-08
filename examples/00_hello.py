from zentropi import Agent

a = Agent('test-agent')


@a.on_event('startup')
async def hello(frame):
    print('Hello, world!')
    a.stop()


a.run()
