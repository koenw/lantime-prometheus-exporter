from urllib.request import urlopen
from typing import Any
import json

from loguru import logger
import prometheus_client
from prometheus_client import Info, Gauge


prometheus_client.REGISTRY.unregister(prometheus_client.GC_COLLECTOR)
prometheus_client.REGISTRY.unregister(prometheus_client.PLATFORM_COLLECTOR)
prometheus_client.REGISTRY.unregister(prometheus_client.PROCESS_COLLECTOR)


class LANTIMECollector:
    version = Info("version", "System version", ["server"])
    version.labels(["server"])

    serial = Info("serial_number", "Serial number", ["server"])
    model = Info("model", "Meinberg LANTIME model", ["server"])
    hostname = Info("hostname", "hostname", ["server"])
    firmware_version = Info("firmware-version", "Running firmware version", ["server"])
    position = Info("position", "GPS position", ["server"])
    cpuload1 = Gauge("cpu_load_1m", "Average CPU load over the past minute", ["server"])
    cpuload5 = Gauge(
        "cpu_load_5m", "Average CPU load over the past 5 minutes", ["server"]
    )
    cpuload15 = Gauge(
        "cpu_load_15m", "Average CPU load over the past 15 minutes", ["server"]
    )
    memory_total = Gauge(
        "memory_total_kilobytes", "Total amount of installed memory", ["server"]
    )
    memory_free = Gauge("memory_free_kilobytes", "Amount of free memory", ["server"])
    uptime = Gauge("uptime_seconds", "Time since last boot", ["server"])
    last_config_change = Gauge(
        "time_since_last_config_change_seconds",
        "Time since last config change",
        ["server"],
    )
    est_time_quality = Info("est_time_quality", "Estimated time quality", ["server"])
    clock_status = Info("clock_status", "Status of the clock signal", ["server"])
    osc_status = Info("osc_status", "Status of the oscillator", ["server"])
    receiver_status = Info("receiver_status", "Status of the gnss receiver", ["server"])
    satellites_in_view = Gauge(
        "satellites_in_view_total", "Number of satellites in view", ["server"]
    )
    good_satellites = Gauge(
        "good-satellites_total", "Number of usable satellites in view", ["server"]
    )
    gps_satellites_in_use = Gauge(
        "gps_satellites_in_use_total", "Number of GPS satellites in use", ["server"]
    )
    galileo_satellites_in_use = Gauge(
        "galileo_satellites_in_use_total",
        "Number of galileo satellites in use",
        ["server"],
    )

    def __init__(self, name: str, url: str, username: str, password: str):
        self.name = name
        self.url = url
        self.username = username
        self.password = password

    def fetch(self) -> dict[str, Any]:
        """Fetch the device status from the Meinberg LANTIME REST API"""
        with urlopen(self.url) as page:
            data = json.loads(page.read().decode())
            return data

    def update_metrics(self, data: dict[str, Any]):
        sys_info = data.get("system-information", {})
        system = data.get("data", {}).get("status", {}).get("system", {})

        # self.version.info({'version': sys_info.get("version", "")}, server=self.name)
        self.version.labels(self.name).info({"version": sys_info.get("version", "")})
        self.serial.labels(self.name).info(
            {"serial": sys_info.get("serial-number", "")}
        )
        self.model.labels(self.name).info({"model": sys_info.get("model", "")})
        self.hostname.labels(self.name).info({"hostname": sys_info.get("hostname", "")})
        self.position.labels(self.name).info({"position": system.get("position", "")})

        cpuload = system.get("cpuload", "").split(" ")
        try:
            cpuload1 = float(cpuload[0])
            cpuload5 = float(cpuload[1])
            cpuload15 = float(cpuload[2])
        except:
            cpuload1 = 0.0
            cpuload5 = 0.0
            cpuload15 = 0.0
        self.cpuload1.labels(self.name).set(cpuload1)
        self.cpuload5.labels(self.name).set(cpuload5)
        self.cpuload15.labels(self.name).set(cpuload15)

        memory = system.get("memory", "").split(" ")
        (memory_total,) = memory[0:1] or [0]
        (memory_free,) = memory[4:5] or [0]
        self.memory_total.labels(self.name).set(memory_total)
        self.memory_free.labels(self.name).set(memory_free)

        self.uptime.labels(self.name).set(system.get("uptime", 0))
        self.last_config_change.labels(self.name).set(
            system.get("last-config-change", 0)
        )
        self.firmware_version.labels(self.name).info(
            {"firmware_version": system.get("firmware", {}).get("running", "")}
        )

        hw_slots = (
            data.get("data", {}).get("status", {}).get("chassis0", {}).get("slots", [])
        )
        (clk,) = [
            c.get("module", {}) for c in hw_slots if c.get("slot-type", "") == "clk"
        ][0:1] or [0]

        self.est_time_quality.labels(self.name).info(
            {"est_time_quality": clk.get("sync-status", {}).get("est-time-quality", "")}
        )
        self.clock_status.labels(self.name).info(
            {
                "clock_status": clk.get("sync-status", {})
                .get("clock-status", {})
                .get("clock", "")
            }
        )
        self.osc_status.labels(self.name).info(
            {
                "osc_status": clk.get("sync-status", {})
                .get("clock-status", {})
                .get("oscillator", "")
            }
        )
        self.receiver_status.labels(self.name).info(
            {"receiver_status_info": clk.get("gns", {}).get("receiver-status", "")}
        )

        self.satellites_in_view.labels(self.name).set(
            clk.get("satellites", {}).get("satellites-in-view", 0)
        )
        self.good_satellites.labels(self.name).set(
            clk.get("satellites", {}).get("good-satellites", 0)
        )

        sats = clk.get("satellites", {}).get("gnss", {}).get("satellite-list", [])
        gps_sats = len([s for s in sats if s.get("gnss-type", "") == "gps"])
        gal_sats = len([s for s in sats if s.get("gnss-type", "") == "galileo"])
        self.gps_satellites_in_use.labels(self.name).set(gps_sats)
        self.galileo_satellites_in_use.labels(self.name).set(gal_sats)

    def collect(self):
        data = self.fetch()
        self.update_metrics(data)
        logger.info(f"Updated metrics for {self.name}")
