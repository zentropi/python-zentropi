from zentropi import Agent

a = Agent("webgallery")


@a.on_interval("make-request", 5)
async def make_request():
    try:
        data = await a.request("whoami", timeout=1)
        print(f"My name is {data["name"]}")
    except TimeoutError:
        print("No response from server")
    finally:
        a.stop()


@a.on_request("whoami", rate_limits=["1/10s"])
async def whoami(frame):
    data = dict(name=a.name)
    await a.send(frame.reply(name=frame.name, data=data))


a.run(
    "ws://localhost:26514/",
    "test-token",
)
