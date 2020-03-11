import asyncio
from tkinter import *

from zentropi import Agent

btn = None
shutdown_event = asyncio.Event()
a = Agent('led')


def stop_agent(*_):
    a.shutdown_event.set()


async def setup_gui():
    root = Tk()
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    window = Frame(root)
    window.grid(row=0, column=0, sticky=(N, S, E, W))
    window.columnconfigure(0, weight=1)
    window.rowconfigure(0, weight=1)
    global btn
    btn = Label(window, text='off', background="#888888")
    btn.grid(row=0, column=0, sticky=(N, S, E, W))
    menu = Menu(root)
    root.config(menu=menu)
    menu.add_command(label='Exit', command=stop_agent)
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


@a.on_event('switch-on')
async def lef_on(frame):
    print('led on')
    btn.configure(background="#00aa00", text="on")
    await a.event('led-on')


@a.on_event('switch-off')
async def led_off(frame):
    print('led off')
    btn.configure(background="#888888", text="off")
    await a.event('led-off')


@a.on_event('startup')
async def start(frame):
    root = await setup_gui()
    a.spawn(tk_loop(root))


a.run(
    'ws://localhost:26514/',
    token='test-token',
)
