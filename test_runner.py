"""Automated validation tests for the virtual embedded device."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import Callable

from device_simulator import VirtualEmbeddedDevice


@dataclass
class TestResult:
    """Store the outcome of one validation test."""

    test_id: str
    name: str
    result: str
    details: str


def execute_test(
    test_id: str,
    name: str,
    test_function: Callable[[], tuple[bool, str]],
) -> TestResult:
    """Execute one test while safely handling unexpected errors."""
    try:
        passed, details = test_function()
        result = "PASS" if passed else "FAIL"
        return TestResult(test_id, name, result, details)
    except Exception as error:
        return TestResult(test_id, name, "ERROR", str(error))


def main() -> None:
    """Run the complete embedded-device validation suite."""
    device = VirtualEmbeddedDevice(seed=42)
    results: list[TestResult] = []

    def test_ping() -> tuple[bool, str]:
        response = device.handle_command("PING")
        passed = response["status"] == "OK" and response["message"] == "PONG"
        return passed, f"Response: {response}"

    def test_device_information() -> tuple[bool, str]:
        response = device.handle_command("DEVICE_INFO")
        passed = (
            response["status"] == "OK"
            and response["firmware_version"] == "1.0.0"
            and response["simulator"] is True
        )
        return passed, f"Response: {response}"

    def test_gpio_high() -> tuple[bool, str]:
        set_response = device.handle_command("SET_GPIO 1")
        read_response = device.handle_command("READ_GPIO")
        passed = (
            set_response["status"] == "OK"
            and read_response["gpio_state"] == 1
        )
        return passed, f"Set: {set_response}; Read: {read_response}"

    def test_gpio_low() -> tuple[bool, str]:
        set_response = device.handle_command("SET_GPIO 0")
        read_response = device.handle_command("READ_GPIO")
        passed = (
            set_response["status"] == "OK"
            and read_response["gpio_state"] == 0
        )
        return passed, f"Set: {set_response}; Read: {read_response}"

    def test_invalid_gpio_value() -> tuple[bool, str]:
        response = device.handle_command("SET_GPIO 5")
        passed = response["status"] == "ERROR"
        return passed, f"Response: {response}"

    def test_nominal_sensor_range() -> tuple[bool, str]:
        device.handle_command("CLEAR_FAULTS")
        response = device.handle_command("READ_SENSORS")
        temperature = response["temperature_c"]
        voltage = response["supply_voltage_v"]
        passed = (
            response["status"] == "OK"
            and 15.0 <= temperature <= 40.0
            and 3.0 <= voltage <= 3.6
        )
        return passed, (
            f"Temperature={temperature} C, "
            f"Supply voltage={voltage} V"
        )

    def test_disconnected_sensor_detection() -> tuple[bool, str]:
        device.handle_command("INJECT_FAULT SENSOR_DISCONNECTED")
        response = device.handle_command("READ_SENSORS")
        device.handle_command("CLEAR_FAULTS")
        passed = (
            response["status"] == "ERROR"
            and response["error"] == "Sensor not detected"
        )
        return passed, f"Response: {response}"

    def test_overtemperature_detection() -> tuple[bool, str]:
        device.handle_command("INJECT_FAULT OVERTEMPERATURE")
        response = device.handle_command("READ_SENSORS")
        device.handle_command("CLEAR_FAULTS")
        temperature = response["temperature_c"]
        passed = temperature > 85.0
        return passed, f"Injected temperature={temperature} C"

    def test_undervoltage_detection() -> tuple[bool, str]:
        device.handle_command("INJECT_FAULT UNDERVOLTAGE")
        response = device.handle_command("READ_SENSORS")
        device.handle_command("CLEAR_FAULTS")
        voltage = response["supply_voltage_v"]
        passed = voltage < 3.0
        return passed, f"Injected supply voltage={voltage} V"

    def test_heartbeat_counter() -> tuple[bool, str]:
        first = device.handle_command("HEARTBEAT")
        second = device.handle_command("HEARTBEAT")
        passed = second["count"] == first["count"] + 1
        return passed, f"First={first['count']}, Second={second['count']}"

    test_definitions = [
        ("TC-001", "Communication ping", test_ping),
        ("TC-002", "Device information", test_device_information),
        ("TC-003", "Set and read GPIO high", test_gpio_high),
        ("TC-004", "Set and read GPIO low", test_gpio_low),
        ("TC-005", "Reject invalid GPIO value", test_invalid_gpio_value),
        ("TC-006", "Nominal sensor range", test_nominal_sensor_range),
        (
            "TC-007",
            "Disconnected sensor detection",
            test_disconnected_sensor_detection,
        ),
        (
            "TC-008",
            "Overtemperature fault detection",
            test_overtemperature_detection,
        ),
        (
            "TC-009",
            "Undervoltage fault detection",
            test_undervoltage_detection,
        ),
        ("TC-010", "Heartbeat counter", test_heartbeat_counter),
    ]

    print("\nVIRTUAL EMBEDDED DEVICE VALIDATION")
    print("=" * 60)

    for test_id, name, function in test_definitions:
        result = execute_test(test_id, name, function)
        results.append(result)
        print(f"{result.test_id}: {result.name:<38} {result.result}")

    with open("test_results.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Test ID", "Test Name", "Result", "Details"])

        for result in results:
            writer.writerow(
                [
                    result.test_id,
                    result.name,
                    result.result,
                    result.details,
                ]
            )

    passed_count = sum(result.result == "PASS" for result in results)
    failed_count = sum(result.result == "FAIL" for result in results)
    error_count = sum(result.result == "ERROR" for result in results)

    print("=" * 60)
    print(f"Passed: {passed_count}")
    print(f"Failed: {failed_count}")
    print(f"Errors: {error_count}")
    print(f"Total:  {len(results)}")
    print("\nDetailed results saved to test_results.csv")

    if failed_count > 0 or error_count > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
