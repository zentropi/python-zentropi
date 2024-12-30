from zentropi import Agent

a = Agent("test-agent")


@a.on_interval("test", 2)
async def test():
    await a.event("test")


@a.on_event("test")
async def hello(frame):
    space_name = frame.meta.get("space").get("name")
    print(f"Hello, {space_name}.")


a.run(
    "ws://localhost:26514/",
    token="test-token",
)
