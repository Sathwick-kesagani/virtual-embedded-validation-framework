"""Virtual embedded device used for automated validation testing.

This module simulates common embedded-device functions, including sensors,
GPIO, firmware information, heartbeat messages, and controlled fault injection.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timezone


class VirtualEmbeddedDevice:
    """Simulate an embedded controller for software-based validation."""

    def __init__(self, seed: int = 42) -> None:
        self.firmware_version = "1.0.0"
        self.device_id = "VED-001"
        self.gpio_state = 0
        self.heartbeat_count = 0
        self.active_fault = "NONE"
        self.random = random.Random(seed)

    @staticmethod
    def timestamp() -> str:
        """Return the current UTC timestamp."""
        return datetime.now(timezone.utc).isoformat()

    def response(self, command: str, status: str, **data: object) -> dict:
        """Create a consistent device response."""
        return {
            "timestamp": self.timestamp(),
            "device_id": self.device_id,
            "command": command,
            "status": status,
            **data,
        }

    def read_sensors(self) -> dict:
        """Return simulated temperature and supply-voltage measurements."""
        if self.active_fault == "SENSOR_DISCONNECTED":
            return self.response(
                "READ_SENSORS",
                "ERROR",
                error="Sensor not detected",
            )

        temperature = round(self.random.uniform(23.0, 27.0), 2)
        voltage = round(self.random.uniform(3.25, 3.35), 3)

        if self.active_fault == "OVERTEMPERATURE":
            temperature = 95.0

        if self.active_fault == "UNDERVOLTAGE":
            voltage = 2.70

        return self.response(
            "READ_SENSORS",
            "OK",
            temperature_c=temperature,
            supply_voltage_v=voltage,
        )

    def handle_command(self, command: str) -> dict:
        """Process a command and return the simulated device response."""
        command = command.strip().upper()
        parts = command.split()

        if not command:
            return self.response("EMPTY", "ERROR", error="Empty command")

        if command == "PING":
            return self.response("PING", "OK", message="PONG")

        if command == "DEVICE_INFO":
            return self.response(
                "DEVICE_INFO",
                "OK",
                firmware_version=self.firmware_version,
                simulator=True,
            )

        if command == "READ_SENSORS":
            return self.read_sensors()

        if command == "READ_GPIO":
            return self.response(
                "READ_GPIO",
                "OK",
                gpio_state=self.gpio_state,
            )

        if len(parts) == 2 and parts[0] == "SET_GPIO":
            if parts[1] not in {"0", "1"}:
                return self.response(
                    "SET_GPIO",
                    "ERROR",
                    error="GPIO value must be 0 or 1",
                )

            self.gpio_state = int(parts[1])
            return self.response(
                "SET_GPIO",
                "OK",
                gpio_state=self.gpio_state,
            )

        if command == "HEARTBEAT":
            self.heartbeat_count += 1
            return self.response(
                "HEARTBEAT",
                "OK",
                count=self.heartbeat_count,
            )

        if len(parts) == 2 and parts[0] == "INJECT_FAULT":
            supported_faults = {
                "SENSOR_DISCONNECTED",
                "OVERTEMPERATURE",
                "UNDERVOLTAGE",
                "TIMEOUT",
            }

            if parts[1] not in supported_faults:
                return self.response(
                    "INJECT_FAULT",
                    "ERROR",
                    error="Unsupported fault type",
                )

            self.active_fault = parts[1]
            return self.response(
                "INJECT_FAULT",
                "OK",
                active_fault=self.active_fault,
            )

        if command == "CLEAR_FAULTS":
            self.active_fault = "NONE"
            return self.response(
                "CLEAR_FAULTS",
                "OK",
                active_fault=self.active_fault,
            )

        if self.active_fault == "TIMEOUT":
            return self.response(
                command,
                "TIMEOUT",
                error="Simulated communication timeout",
            )

        return self.response(
            command,
            "ERROR",
            error="Unknown command",
        )


def main() -> None:
    """Run an interactive command-line interface for the device."""
    device = VirtualEmbeddedDevice()

    print("Virtual Embedded Device Simulator")
    print("Type HELP to view available commands or EXIT to stop.")

    commands = [
        "PING",
        "DEVICE_INFO",
        "READ_SENSORS",
        "READ_GPIO",
        "SET_GPIO 0",
        "SET_GPIO 1",
        "HEARTBEAT",
        "INJECT_FAULT SENSOR_DISCONNECTED",
        "INJECT_FAULT OVERTEMPERATURE",
        "INJECT_FAULT UNDERVOLTAGE",
        "INJECT_FAULT TIMEOUT",
        "CLEAR_FAULTS",
    ]

    while True:
        user_command = input("device> ").strip()

        if user_command.upper() == "EXIT":
            print("Simulator stopped.")
            break

        if user_command.upper() == "HELP":
            print("\n".join(commands))
            continue

        result = device.handle_command(user_command)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
