import aiosqlite
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List


@dataclass
class WeatherData:
    """Weather data with all values stored in metric units:
    - temperature: celsius
    - wind_speed, wind_gust: kilometers per hour
    - rain: millimeters
    - pressure: hectopascals
    """

    station_type: str
    date_utc: datetime
    temperature_out: float  # °C
    humidity_out: int  # %
    temperature_in: float  # °C
    humidity_in: int  # %
    wind_dir: int  # degrees
    wind_speed: float  # km/h
    wind_gust: float  # km/h
    max_daily_gust: float  # km/h
    uv_index: int  # 0-12
    solar_radiation: float  # W/m²
    rain_hourly: float  # mm
    rain_event: float  # mm
    rain_daily: float  # mm
    rain_weekly: float  # mm
    rain_monthly: float  # mm
    rain_yearly: float  # mm
    rain_total: float  # mm
    pressure_rel: float  # hPa
    pressure_abs: float  # hPa
    battery_ok: bool  # True if battery is OK

    @classmethod
    def from_dict(cls, data: dict) -> "WeatherData":
        def f_to_c(f: str) -> float:
            return round((float(f) - 32) * 5 / 9, 2)

        def mph_to_kmh(mph: str) -> float:
            return round(float(mph) * 1.60934, 2)

        def in_to_mm(inches: str) -> float:
            return round(float(inches) * 25.4, 2)

        def in_hg_to_hpa(inches: str) -> float:
            return round(float(inches) * 33.8639, 2)

        return cls(
            station_type=data["stationtype"],
            date_utc=datetime.strptime(data["dateutc"], "%Y-%m-%d %H:%M:%S"),
            temperature_out=f_to_c(data["tempf"]),
            humidity_out=int(data["humidity"]),
            wind_speed=mph_to_kmh(data["windspeedmph"]),
            wind_gust=mph_to_kmh(data["windgustmph"]),
            max_daily_gust=mph_to_kmh(data["maxdailygust"]),
            wind_dir=int(data["winddir"]),
            uv_index=int(data["uv"]),
            solar_radiation=float(data["solarradiation"]),
            rain_hourly=in_to_mm(data["hourlyrainin"]),
            rain_event=in_to_mm(data["eventrainin"]),
            rain_daily=in_to_mm(data["dailyrainin"]),
            rain_weekly=in_to_mm(data["weeklyrainin"]),
            rain_monthly=in_to_mm(data["monthlyrainin"]),
            rain_yearly=in_to_mm(data["yearlyrainin"]),
            rain_total=in_to_mm(data["totalrainin"]),
            battery_ok=data["battout"] == "1",
            temperature_in=f_to_c(data["tempinf"]),
            humidity_in=int(data["humidityin"]),
            pressure_rel=in_hg_to_hpa(data["baromrelin"]),
            pressure_abs=in_hg_to_hpa(data["baromabsin"]),
        )

    @property
    def temperature_out_str(self) -> str:
        return f"{self.temperature_out:.1f}°C"

    @property
    def temperature_in_str(self) -> str:
        return f"{self.temperature_in:.1f}°C"

    @property
    def wind_speed_str(self) -> str:
        return f"{self.wind_speed:.1f} km/h"

    @property
    def wind_gust_str(self) -> str:
        return f"{self.wind_gust:.1f} km/h"

    @property
    def max_daily_gust_str(self) -> str:
        return f"{self.max_daily_gust:.1f} km/h"

    @property
    def wind_dir_str(self) -> str:
        return f"{self.wind_dir}°"

    @property
    def pressure_rel_str(self) -> str:
        return f"{self.pressure_rel:.1f} hPa"

    @property
    def pressure_abs_str(self) -> str:
        return f"{self.pressure_abs:.1f} hPa"

    @property
    def rain_hourly_str(self) -> str:
        return f"{self.rain_hourly:.1f} mm"

    @property
    def rain_event_str(self) -> str:
        return f"{self.rain_event:.1f} mm"

    @property
    def rain_daily_str(self) -> str:
        return f"{self.rain_daily:.1f} mm"

    @property
    def rain_weekly_str(self) -> str:
        return f"{self.rain_weekly:.1f} mm"

    @property
    def rain_monthly_str(self) -> str:
        return f"{self.rain_monthly:.1f} mm"

    @property
    def rain_yearly_str(self) -> str:
        return f"{self.rain_yearly:.1f} mm"

    @property
    def rain_total_str(self) -> str:
        return f"{self.rain_total:.1f} mm"

    @property
    def humidity_out_str(self) -> str:
        return f"{self.humidity_out}%"

    @property
    def humidity_in_str(self) -> str:
        return f"{self.humidity_in}%"

    @property
    def solar_radiation_str(self) -> str:
        return f"{self.solar_radiation:.1f} W/m²"

    def to_dict(self) -> dict:
        """Return a dictionary containing both raw values and formatted strings."""
        base_dict = {
            "station_type": self.station_type,
            "date_utc": self.date_utc.isoformat(),
            "temperature_out": self.temperature_out,
            "temperature_out_str": self.temperature_out_str,
            "humidity_out": self.humidity_out,
            "humidity_out_str": self.humidity_out_str,
            "temperature_in": self.temperature_in,
            "temperature_in_str": self.temperature_in_str,
            "humidity_in": self.humidity_in,
            "humidity_in_str": self.humidity_in_str,
            "wind_speed": self.wind_speed,
            "wind_speed_str": self.wind_speed_str,
            "wind_gust": self.wind_gust,
            "wind_gust_str": self.wind_gust_str,
            "max_daily_gust": self.max_daily_gust,
            "max_daily_gust_str": self.max_daily_gust_str,
            "wind_dir": self.wind_dir,
            "wind_dir_str": self.wind_dir_str,
            "uv_index": self.uv_index,
            "solar_radiation": self.solar_radiation,
            "solar_radiation_str": self.solar_radiation_str,
            "pressure_rel": self.pressure_rel,
            "pressure_rel_str": self.pressure_rel_str,
            "pressure_abs": self.pressure_abs,
            "pressure_abs_str": self.pressure_abs_str,
            "battery_ok": self.battery_ok,
        }

        # Add all rain measurements
        for rain_type in [
            "hourly",
            "event",
            "daily",
            "weekly",
            "monthly",
            "yearly",
            "total",
        ]:
            value = getattr(self, f"rain_{rain_type}")
            str_value = getattr(self, f"rain_{rain_type}_str")
            base_dict[f"rain_{rain_type}"] = value
            base_dict[f"rain_{rain_type}_str"] = str_value

        return base_dict


class WeatherDB:
    def __init__(self, db_path: str = "weather.db"):
        self.db_path = db_path
        self._db = None

    async def connect(self):
        self._db = await aiosqlite.connect(self.db_path)
        await self._create_tables()

    async def close(self):
        if self._db:
            await self._db.close()

    async def _create_tables(self):
        await self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS weather_metrics (
                timestamp DATETIME PRIMARY KEY,
                temperature_out REAL,
                humidity_out INTEGER,
                temperature_in REAL,
                humidity_in INTEGER,
                wind_dir INTEGER,
                wind_speed REAL,
                wind_gust REAL,
                max_daily_gust REAL,
                uv_index INTEGER,
                solar_radiation REAL,
                rain_hourly REAL,
                rain_event REAL,
                rain_daily REAL,
                rain_weekly REAL,
                rain_monthly REAL,
                rain_yearly REAL,
                rain_total REAL,
                pressure_rel REAL,
                pressure_abs REAL,
                battery_ok BOOLEAN
            )
        """
        )
        await self._db.commit()

    async def store_weather(self, weather):
        query = """
            INSERT INTO weather_metrics VALUES (
                :timestamp, :temperature_out, :humidity_out, :temperature_in,
                :humidity_in, :wind_dir, :wind_speed, :wind_gust, :max_daily_gust,
                :uv_index, :solar_radiation, :rain_hourly, :rain_event, :rain_daily,
                :rain_weekly, :rain_monthly, :rain_yearly, :rain_total,
                :pressure_rel, :pressure_abs, :battery_ok
            )
        """
        await self._db.execute(
            query,
            {
                "timestamp": weather.date_utc.isoformat(),
                "temperature_out": weather.temperature_out,
                "humidity_out": weather.humidity_out,
                "temperature_in": weather.temperature_in,
                "humidity_in": weather.humidity_in,
                "wind_dir": weather.wind_dir,
                "wind_speed": weather.wind_speed,
                "wind_gust": weather.wind_gust,
                "max_daily_gust": weather.max_daily_gust,
                "uv_index": weather.uv_index,
                "solar_radiation": weather.solar_radiation,
                "rain_hourly": weather.rain_hourly,
                "rain_event": weather.rain_event,
                "rain_daily": weather.rain_daily,
                "rain_weekly": weather.rain_weekly,
                "rain_monthly": weather.rain_monthly,
                "rain_yearly": weather.rain_yearly,
                "rain_total": weather.rain_total,
                "pressure_rel": weather.pressure_rel,
                "pressure_abs": weather.pressure_abs,
                "battery_ok": weather.battery_ok,
            },
        )
        await self._db.commit()

    async def get_history(self, hours: int = 24, points: int = 300) -> list[dict]:
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

        count_query = "SELECT COUNT(*) FROM weather_metrics WHERE timestamp > ?"
        async with self._db.execute(count_query, (since,)) as cursor:
            total_rows = (await cursor.fetchone())[0]

        if total_rows <= points:
            # If we have fewer rows than requested points, return all rows
            query = "SELECT * FROM weather_metrics WHERE timestamp > ? ORDER BY timestamp DESC"
            params = (since,)
        else:
            # Calculate the step size to get evenly distributed points
            step = total_rows / points
            # Select evenly distributed rows
            query = """
                WITH numbered AS (
                    SELECT *, ROW_NUMBER() OVER (ORDER BY timestamp DESC) - 1 as row_num 
                    FROM weather_metrics 
                    WHERE timestamp > ?
                )
                SELECT * FROM numbered 
                WHERE CAST(row_num AS FLOAT) % ? < 1 
                ORDER BY timestamp DESC
            """
            params = (since, step)

        async with self._db.execute(query, params) as cursor:
            columns = [desc[0] for desc in cursor.description]
            rows = await cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
