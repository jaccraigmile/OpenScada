#!/usr/bin/env python3
"""A small Modbus/TCP process simulator for the OpenPLC lab."""

from __future__ import annotations

import argparse
import socketserver
import struct
import threading
import time
from dataclasses import dataclass, field


INPUT_COUNT = 6
COIL_COUNT = 5
DEFAULT_MODBUS_PORT = 502


@dataclass
class Process:
    unit_id: int = 1
    emitter_interval: float = 5.0
    lock: threading.Lock = field(default_factory=threading.Lock)
    door_closed: bool = True
    start_button_until: float = 0.0
    box_position: float | None = None
    box_held: bool = False
    boxes_removed: int = 0
    auto_emitter: bool = True
    last_emission: float = field(default_factory=time.monotonic)
    coils: list[bool] = field(default_factory=lambda: [False] * COIL_COUNT)
    z_down: bool = False
    z_transition_until: float = 0.0
    robot_angle: float = 0.0
    rotation_transition_until: float = 0.0

    def read_inputs(self) -> list[bool]:
        with self.lock:
            now = time.monotonic()
            return [
                now < self.start_button_until,
                self.door_closed,
                self.box_position is not None and self.box_position >= 1.0,
                self.z_down and self.box_position is not None and self.robot_angle < 0.1,
                now < self.z_transition_until,
                now < self.rotation_transition_until,
            ]

    def read_coils(self, address: int, count: int) -> list[bool]:
        with self.lock:
            return self.coils[address : address + count]

    def write_coils(self, address: int, values: list[bool]) -> None:
        with self.lock:
            self.coils[address : address + len(values)] = values

    def set_start_button(self) -> None:
        with self.lock:
            self.start_button_until = time.monotonic() + 0.25

    def set_door(self, closed: bool) -> None:
        with self.lock:
            self.door_closed = closed

    def set_auto_emitter(self, enabled: bool) -> None:
        with self.lock:
            self.auto_emitter = enabled

    def add_box(self) -> bool:
        with self.lock:
            if self.box_position is not None:
                return False
            self.box_position = 0.0
            return True

    def status(self) -> str:
        inputs = self.read_inputs()
        coils = self.read_coils(0, COIL_COUNT)
        with self.lock:
            box = "none" if self.box_position is None else f"{self.box_position:.2f}"
            return (
                f"door={'closed' if self.door_closed else 'open'} "
                f"box_position={box} box_held={self.box_held} "
                f"removed={self.boxes_removed} auto_emitter={self.auto_emitter}\n"
                f"inputs={inputs} coils={coils}"
            )

    def step(self, now: float, dt: float) -> None:
        with self.lock:
            if self.auto_emitter and self.box_position is None:
                if now - self.last_emission >= self.emitter_interval:
                    self.box_position = 0.0
                    self.last_emission = now

            if not self.door_closed:
                return

            conveyor, grab, extend_z, rotate_cw, rotate_ccw = self.coils

            if extend_z != self.z_down:
                self.z_down = extend_z
                self.z_transition_until = now + 0.35

            if rotate_cw and not rotate_ccw and self.robot_angle < 1.0:
                self.robot_angle = min(1.0, self.robot_angle + dt / 0.8)
                self.rotation_transition_until = now + 0.15
            elif rotate_ccw and not rotate_cw and self.robot_angle > 0.0:
                self.robot_angle = max(0.0, self.robot_angle - dt / 0.8)
                self.rotation_transition_until = now + 0.15

            if (
                grab
                and self.z_down
                and self.robot_angle < 0.1
                and self.box_position is not None
                and self.box_position >= 1.0
            ):
                self.box_held = True
                self.box_position = None

            if not grab and self.box_held and not self.z_down and self.robot_angle >= 0.9:
                self.box_held = False
                self.boxes_removed += 1

            if conveyor and self.box_position is not None:
                self.box_position += dt * 0.25
                if self.box_position > 1.5:
                    self.box_position = None


def _exception_response(function: int, code: int) -> bytes:
    return bytes((function | 0x80, code))


def process_pdu(process: Process, pdu: bytes) -> bytes:
    if not pdu:
        return b""

    function = pdu[0]
    if function in (1, 2):
        if len(pdu) != 5:
            return _exception_response(function, 3)
        address, count = struct.unpack(">HH", pdu[1:])
        if count < 1 or count > 2000:
            return _exception_response(function, 3)
        limit = COIL_COUNT if function == 1 else INPUT_COUNT
        if address + count > limit:
            return _exception_response(function, 2)
        values = (
            process.read_coils(address, count)
            if function == 1
            else process.read_inputs()[address : address + count]
        )
        packed = bytearray((count + 7) // 8)
        for index, value in enumerate(values):
            if value:
                packed[index // 8] |= 1 << (index % 8)
        return bytes((function, len(packed))) + packed

    if function == 5:
        if len(pdu) != 5:
            return _exception_response(function, 3)
        address, value = struct.unpack(">HH", pdu[1:])
        if address >= COIL_COUNT:
            return _exception_response(function, 2)
        if value not in (0x0000, 0xFF00):
            return _exception_response(function, 3)
        process.write_coils(address, [value == 0xFF00])
        return pdu

    if function == 15:
        if len(pdu) < 6:
            return _exception_response(function, 3)
        address, count, byte_count = struct.unpack(">HHB", pdu[1:6])
        if count < 1 or count > 1968 or byte_count != (count + 7) // 8:
            return _exception_response(function, 3)
        if len(pdu) != 6 + byte_count:
            return _exception_response(function, 3)
        if address + count > COIL_COUNT:
            return _exception_response(function, 2)
        values = [
            bool(pdu[6 + index // 8] & (1 << (index % 8)))
            for index in range(count)
        ]
        process.write_coils(address, values)
        return bytes((function,)) + struct.pack(">HH", address, count)

    return _exception_response(function, 1)


class ModbusHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        while True:
            header = self._receive_exactly(6)
            if header is None:
                return
            transaction, protocol, length = struct.unpack(">HHH", header)
            if protocol != 0 or length < 2 or length > 254:
                return
            body = self._receive_exactly(length)
            if body is None:
                return
            unit_id, pdu = body[0], body[1:]
            response_pdu = (
                process_pdu(self.server.process, pdu)
                if unit_id == self.server.process.unit_id
                else _exception_response(pdu[0] if pdu else 0, 11)
            )
            response_body = bytes((unit_id,)) + response_pdu
            response_header = struct.pack(">HHH", transaction, 0, len(response_body))
            self.request.sendall(response_header + response_body)

    def _receive_exactly(self, count: int) -> bytes | None:
        data = bytearray()
        while len(data) < count:
            chunk = self.request.recv(count - len(data))
            if not chunk:
                return None
            data.extend(chunk)
        return bytes(data)


class ModbusServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address: tuple[str, int], process: Process):
        self.process = process
        super().__init__(address, ModbusHandler)


def run_simulation(process: Process, tick: float) -> None:
    last = time.monotonic()
    while True:
        time.sleep(tick)
        now = time.monotonic()
        process.step(now, now - last)
        last = now


def run_cli(process: Process) -> None:
    print("Commands: start, box, door open|close, auto on|off, status, help, quit")
    while True:
        try:
            command = input("sim> ").strip().lower().split()
        except EOFError:
            return
        if not command:
            continue
        if command == ["quit"]:
            return
        if command == ["help"]:
            print("start: pulse the start button; box: add a box at the emitter")
            print("door open|close: set the safety door; auto on|off: emitter mode")
            print("status: show process I/O; quit: stop the simulator")
        elif command == ["start"]:
            process.set_start_button()
            print("Start button pulsed.")
        elif command == ["box"]:
            print("Box added." if process.add_box() else "A box is already in the process.")
        elif command[:1] == ["door"] and len(command) == 2 and command[1] in ("open", "close"):
            process.set_door(command[1] == "close")
            print(f"Safety door {command[1]}.")
        elif command[:1] == ["auto"] and len(command) == 2 and command[1] in ("on", "off"):
            process.set_auto_emitter(command[1] == "on")
            print(f"Emitter {'enabled' if command[1] == 'on' else 'disabled'}.")
        elif command == ["status"]:
            print(process.status())
        else:
            print("Unknown command. Type 'help' for available commands.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="0.0.0.0", help="bind address (default: all interfaces)")
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_MODBUS_PORT,
        help=f"Modbus/TCP port (default: {DEFAULT_MODBUS_PORT})",
    )
    parser.add_argument("--unit-id", type=int, default=1, help="Modbus unit ID (default: 1)")
    parser.add_argument("--emitter-interval", type=float, default=5.0, help="seconds between automatic boxes")
    args = parser.parse_args()
    if not 0 <= args.unit_id <= 247:
        parser.error("--unit-id must be between 0 and 247")
    if args.emitter_interval <= 0:
        parser.error("--emitter-interval must be positive")

    process = Process(unit_id=args.unit_id, emitter_interval=args.emitter_interval)
    server = ModbusServer((args.host, args.port), process)
    print(
        f"Modbus/TCP listening on {args.host}:{args.port}, unit ID {args.unit_id}. "
        "Configure OpenPLC to read 6 discrete inputs and write 5 coils."
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    threading.Thread(target=run_simulation, args=(process, 0.05), daemon=True).start()
    try:
        run_cli(process)
    except KeyboardInterrupt:
        print()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
