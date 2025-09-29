#!/usr/bin/env python3
"""
Prometheus exporter for the Meinberg LANTIME NTP servers.
"""

from prometheus_client import start_http_server
from loguru import logger
from time import sleep
import argparse
import os
import sys
import shlex

from collector import LANTIMECollector


def parse_args():
    parser = argparse.ArgumentParser(
        description="Prometheus exporter for the Meinberg LANTIME NTP servers"
    )
    parser.add_argument(
        "--username",
        help="Meinberg LANTIME API username",
        type=str,
        default=os.environ.get("LANTIME_PROMETHEUS_USERNAME", ""),
    )
    parser.add_argument(
        "--password",
        help="Meinberg LANTIME API password",
        type=str,
        default=os.environ.get("LANTIME_PROMETHEUS_PASSWORD", ""),
    )
    parser.add_argument(
        "--interval",
        help="Interval between API requests, in seconds",
        type=int,
        default=os.environ.get("LANTIME_PROMETHEUS_INTERVAL", 10),
    )
    parser.add_argument(
        "--port",
        help="Port to listen on",
        type=int,
        default=os.environ.get("LANTIME_PROMETHEUS_PORT", 3000),
    )
    parser.add_argument(
        "URLs",
        nargs="*",
        help="Meinberg LANTIME server name & API URL, e.g. ntp01:https://ntp.example.com/api/ ntp02:http://ntp2.example.com/api/",
    )

    args = parser.parse_args()

    if len(args.URLs) == 0:
        env_urls = os.environ.get("LANTIME_PROMETHEUS_URLS")
        if not env_urls:
            print(
                "Error: Please pass URLS on the command line or in the LANTIME_PROMETHEUS_URLS environmental variable.\n",
                file=sys.stderr,
            )
            parser.print_help()
            sys.exit(1)
        args.URLs = shlex.split(env_urls)

    return args


if __name__ == "__main__":
    args = parse_args()

    collectors = []
    for server in args.URLs:
        name, url = server.partition(":")[::2]
        col = LANTIMECollector(
            name=name, url=url, username=args.username, password=args.password
        )
        collectors.append(col)
        logger.info(f"Initialized collector for {name} ({url})")

    start_http_server(args.port)
    while True:
        for col in collectors:
            try:
                col.collect()
            except Exception as e:
                logger.warning(
                    f"Failed to query REST API for {col.name} ({col.url}): {e}"
                )
        sleep(args.interval)
