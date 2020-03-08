from zentropi import Agent

a = Agent('test-agent')


@a.on_interval('test-interval', 0.5)
async def hello_interval(frame):
    if frame.data.get('count') == 4:
        a.stop()
    else:
        print('Hello, world!')


a.run()