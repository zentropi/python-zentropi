import asyncio
from tkinter import *

from zentropi import Agent

a = Agent("switch")


def stop_agent(*_):
    a.shutdown_event.set()


btn = None
btn_state = False


class ToggleSwitch(Canvas):
    def __init__(self, parent, width=100, height=50, pad=4, command=None):
        super().__init__(
            parent, width=width, height=height, bg="#ffffff", bd=0, highlightthickness=0
        )
        self.command = command
        self.switch_on = False
        self._pos = pad

        # Track dimensions
        self.width = width
        self.height = height
        self.pad = pad

        # Colors
        self.track_on_color = "#22c55e"
        self.track_off_color = "#e2e8f0"
        self.thumb_color = "#ffffff"
        self.thumb_off_color = "#94a3b8"

        # Create track and thumb
        self.track = self.create_rounded_rect(
            self.pad,
            self.pad,
            self.width - self.pad,
            self.height - self.pad,
            self.height // 2,
            fill=self.track_off_color,
        )

        thumb_size = self.height - (self.pad * 2)
        self.thumb = self.create_oval(
            self._pos,
            self.pad,
            self._pos + thumb_size,
            self.height - self.pad,
            fill=self.thumb_off_color,
            outline=self.thumb_off_color,
        )

        # Bind events
        self.bind("<Button-1>", self.toggle)

    def create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1 + radius,
            y1,
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    async def animate(self, target_pos):
        current_pos = self._pos
        steps = 10
        step_size = (target_pos - current_pos) / steps

        for _ in range(steps):
            self._pos += step_size
            self.coords(
                self.thumb,
                self._pos,
                self.pad,
                self._pos + (self.height - self.pad * 2),
                self.height - self.pad,
            )
            await asyncio.sleep(0.02)

    def toggle(self, event=None):
        self.switch_on = not self.switch_on
        target_pos = (
            self.width - (self.height - self.pad) - self.pad
            if self.switch_on
            else self.pad
        )

        # Update colors immediately
        self.itemconfig(
            self.track,
            fill=self.track_on_color if self.switch_on else self.track_off_color,
        )
        self.itemconfig(
            self.thumb,
            fill=self.thumb_color if self.switch_on else self.thumb_off_color,
            outline=self.thumb_color if self.switch_on else self.thumb_off_color,
        )

        # Start animation
        asyncio.create_task(self.animate(target_pos))

        if self.command:
            self.command()


def button_toggle():
    global btn_state
    if btn_state:
        btn_state = False
        print("switch off")
        asyncio.create_task(a.event("switch-off"))
    else:
        btn_state = True
        print("switch on")
        asyncio.create_task(a.event("switch-on"))


async def setup_gui():
    root = Tk()
    root.title("Switch Simulator")
    root.minsize(200, 200)
    root.configure(bg="#ffffff")
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    window = Frame(root, padx=20, pady=20, bg="#ffffff")
    window.grid(row=0, column=0, sticky=(N, S, E, W))
    window.columnconfigure(0, weight=1)
    window.rowconfigure(0, weight=1)

    global btn
    btn = ToggleSwitch(window, width=100, height=50, command=button_toggle)
    btn.grid(row=0, column=0, padx=10, pady=10)

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
async def switch_on(frame):
    global btn_state
    if not btn_state:
        btn_state = True
        print("switch on")
        btn.toggle()


@a.on_event("switch-off")
async def switch_off(frame):
    global btn_state
    if btn_state:
        btn_state = False
        print("switch off")
        btn.toggle()


@a.on_event("startup")
async def start(frame):
    root = await setup_gui()
    a.spawn("tk_loop", tk_loop(root))


a.run(
    "ws://localhost:26514/",
    token="test-token",
)
