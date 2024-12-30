import asyncio
from tkinter import *

from zentropi import Agent

btn = None
shutdown_event = asyncio.Event()
a = Agent("led")


def stop_agent(*_):
    a.shutdown_event.set()


async def setup_gui():
    root = Tk()
    root.title("LED Simulator")
    root.minsize(200, 200)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    window = Frame(root, padx=20, pady=20)
    window.grid(row=0, column=0, sticky=(N, S, E, W))
    window.columnconfigure(0, weight=1)
    window.rowconfigure(0, weight=1)

    global btn
    btn = Label(
        window,
        text="OFF",
        background="#444444",
        foreground="#ffffff",
        font=("Helvetica", 16, "bold"),
        pady=40,
        relief="raised",
        borderwidth=2,
    )
    btn.grid(row=0, column=0, sticky=(N, S, E, W), padx=10, pady=10)

    menu = Menu(root)
    root.config(menu=menu)
    menu.add_command(label="Exit", command=stop_agent)
    root.bind("<Control-q>", stop_agent)
    return root


async def tk_loop(root, interval=0.05):
    try:
        while True:
            root.update()
            await asyncio.sleep(interval)
    except TclError as e:
        if "application has been destroyed" not in e.args[0]:
            raise


@a.on_event("switch-on")
async def led_on(frame):
    print("led on")
    btn.configure(background="#22c55e", foreground="#ffffff", text="ON")
    await a.event("led-on")


@a.on_event("switch-off")
async def led_off(frame):
    print("led off")
    btn.configure(background="#444444", foreground="#ffffff", text="OFF")
    await a.event("led-off")


@a.on_event("startup")
async def start(frame):
    root = await setup_gui()
    a.spawn("tk_loop", tk_loop(root))


a.run(
    "ws://localhost:26514/",
    token="test-token",
)
