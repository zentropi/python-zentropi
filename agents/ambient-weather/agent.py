import asyncio
import os
import logging
from typing import List

from quart import Quart, request, render_template, Response
from zentropi import Agent
import arrow
import json

from database import WeatherDB, WeatherData
from sparkline import generate_sparkline

AGENT_NAME = "ambient_weather"
ENDPOINT = os.environ.get("ENDPOINT")
TIMEZONE = os.environ.get("TIMEZONE")
TOKEN = os.environ.get(f"{AGENT_NAME.upper()}_TOKEN")
PASSKEY = os.environ.get("AMBIENT_WEATHER_PASSKEY")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
# logger.addHandler(logging.FileHandler(f"{AGENT_NAME}.log"))

agent = Agent(AGENT_NAME)
app = Quart(__name__, static_folder="static", template_folder="templates")


@app.template_filter("humanize")
def humanize_filter(timestamp):
    """Convert timestamp to human readable format."""
    return arrow.get(timestamp).humanize()


# Initialize database connection
db = WeatherDB()

# Add this after other global variables
subscribers = set()


async def broadcast(data):
    if "weather" in data:
        data["weather"]["timestamp_humanized"] = humanize_filter(
            data["weather"]["date_utc"]
        )
    for queue in subscribers:
        await queue.put(data)


@agent.on_event("startup")
async def start(_frame):
    logger.info(f"Starting {AGENT_NAME} agent")
    await agent.emit("ohai")


@agent.on_event("shutdown")
async def stop(_frame):
    logger.info(f"Stopping {AGENT_NAME} agent")


@app.before_serving
async def startup():
    await db.connect()
    asyncio.create_task(agent.start(ENDPOINT, token=TOKEN, handle_signals=False))


@app.after_serving
async def shutdown():
    await db.close()
    agent.stop()


@app.route("/events")
async def events():
    queue = asyncio.Queue()
    subscribers.add(queue)

    async def stream():
        try:
            while True:
                data = await queue.get()
                yield f"data: {json.dumps(data)}\n\n"
        finally:
            subscribers.remove(queue)

    return Response(stream(), mimetype="text/event-stream")


@app.route("/data")
async def weather_webhook():
    args = request.args.to_dict()
    if args["PASSKEY"] != PASSKEY:
        logger.error(f"Invalid passkey: {args['PASSKEY']}")
        return {"status": "error", "message": "Invalid passkey"}, 401
    try:
        weather = WeatherData.from_dict(args)
        await db.store_weather(weather)

        # Get last 24h data for sparklines
        history = await db.get_history(24, 360)
        metrics = {
            "temperature_out": [],
            "temperature_in": [],
            "humidity_out": [],
            "humidity_in": [],
            "wind_speed": [],
            "wind_gust": [],
            "pressure_rel": [],
            "pressure_abs": [],
            "rain_hourly": [],
            "rain_event": [],
            "uv_index": [],
            "solar_radiation": [],
        }

        for entry in reversed(history):
            for metric in metrics:
                metrics[metric].append(entry[metric])

        sparklines = {
            metric: generate_sparkline(values) for metric, values in metrics.items()
        }

        # Broadcast the update
        await broadcast(
            {
                "weather": weather.to_dict(),
                "sparklines": sparklines,
            }
        )

        await agent.emit(
            "current-weather",
            data=weather.to_dict(),
        )
        logger.info(f"Received weather data: {weather.to_dict()}")
        return {"status": "ok"}
    except (KeyError, ValueError) as e:
        logger.error(f"Invalid weather data: {e}")
        return {"status": "error", "message": str(e)}, 400


@app.route("/")
async def index():
    history = await db.get_history(24, 360)

    # Data for sparklines
    metrics = {
        "temperature_out": [],
        "temperature_in": [],
        "humidity_out": [],
        "humidity_in": [],
        "wind_speed": [],
        "wind_gust": [],
        "pressure_rel": [],
        "pressure_abs": [],
        "rain_hourly": [],
        "rain_event": [],
        "uv_index": [],
        "solar_radiation": [],
    }

    for entry in reversed(history):
        for metric in metrics:
            metrics[metric].append(entry[metric])

    sparklines = {
        metric: generate_sparkline(values) for metric, values in metrics.items()
    }

    current = history[0] if history else None

    groups = [
        {
            "title": "Temperature",
            "metrics": [
                {
                    "label": "Outside",
                    "key": "temperature_out",
                    "unit": "°C",
                    "format_value": True,
                },
                {
                    "label": "Inside",
                    "key": "temperature_in",
                    "unit": "°C",
                    "format_value": True,
                },
            ],
        },
        {
            "title": "Sun",
            "metrics": [
                {
                    "label": "UV Index",
                    "key": "uv_index",
                    "unit": "UV",
                    "format_value": False,
                },
                {
                    "label": "Solar Radiation",
                    "key": "solar_radiation",
                    "unit": "W/m²",
                    "format_value": True,
                },
            ],
        },
        {
            "title": "Wind",
            "metrics": [
                {
                    "label": "Speed",
                    "key": "wind_speed",
                    "unit": "km/h",
                    "format_value": True,
                },
                {
                    "label": "Gust",
                    "key": "wind_gust",
                    "unit": "km/h",
                    "format_value": True,
                },
            ],
        },
        {
            "title": "Rain",
            "metrics": [
                {
                    "label": "Hourly",
                    "key": "rain_hourly",
                    "unit": "mm",
                    "format_value": True,
                },
                {
                    "label": "Event",
                    "key": "rain_event",
                    "unit": "mm",
                    "format_value": True,
                },
            ],
        },
        {
            "title": "Humidity",
            "metrics": [
                {
                    "label": "Outside",
                    "key": "humidity_out",
                    "unit": "%",
                    "format_value": False,
                },
                {
                    "label": "Inside",
                    "key": "humidity_in",
                    "unit": "%",
                    "format_value": False,
                },
            ],
        },
        {
            "title": "Pressure",
            "metrics": [
                {
                    "label": "Relative",
                    "key": "pressure_rel",
                    "unit": "hPa",
                    "format_value": True,
                },
                {
                    "label": "Absolute",
                    "key": "pressure_abs",
                    "unit": "hPa",
                    "format_value": True,
                },
            ],
        },
    ]

    return await render_template(
        "index.html", current=current, sparklines=sparklines, groups=groups
    )


@app.route("/manifest.json")
async def manifest():
    return await app.send_static_file("manifest.json")


@app.route("/service-worker.js")
async def service_worker():
    response = await app.send_static_file("service-worker.js")
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Content-Type"] = "application/javascript"
    return response


app.run(host="0.0.0.0", port=8022)
