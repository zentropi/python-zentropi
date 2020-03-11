import asyncio
import random
from tkinter import *

from zentropi import Agent

a = Agent('switch')

def stop_agent(*_):
    a.shutdown_event.set()

btn = None
btn_state = False

def button_toggle():
    global btn_state
    if btn_state:
        btn_state = False
        print('switch off')
        btn.configure(text='off')
        a.spawn(a.event('switch-off'))
    else:
        btn_state = True
        print('switch on')
        btn.configure(text='on')
        a.spawn(a.event('switch-on'))


async def setup_gui():
    root = Tk()
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    window = Frame(root)
    window.grid(row=0, column=0, sticky=(N, S, E, W))
    window.columnconfigure(0, weight=1)
    window.rowconfigure(0, weight=1)
    global btn
    btn = Button(window, text='off', command=button_toggle)
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
async def switch_on(frame):
    global btn_state
    btn_state = True
    print('switch on')
    btn.configure(text='on')


@a.on_event('switch-off')
async def switch_off(frame):
    global btn_state
    btn_state = False
    print('switch off')
    btn.configure(text='off')


@a.on_event('startup')
async def start(frame):
    root = await setup_gui()
    a.spawn(tk_loop(root))


a.run(
    'ws://localhost:26514/',
    token='test-token',
)
