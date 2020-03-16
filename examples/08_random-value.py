import random
from zentropi import Agent

a = Agent('random-value')


@a.on_interval('random-value', 2)
async def random_value():
    await a.event(
        'random-value', 
        value=random.choice(range(20, 80)))


a.run(
    'ws://localhost:26514/',
    token='dfa50132fcea4105a69cba3c1424429b',
)
