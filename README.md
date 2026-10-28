# OpenScada

## Python replacement for Factory I/O

[`factoryio_simulator.py`](./factoryio_simulator.py) provides a lightweight,
headless substitute for the Factory I/O scene and Modbus TCP driver described
in parts 3 and 4 of the virtual industrial cybersecurity lab. It uses only the
Python standard library and remains compatible with OpenPLC as the Modbus
client; the simulator does not replace OpenPLC or its control logic.

Run it with Python 3:

```sh
sudo python3 factoryio_simulator.py --host 192.168.88.100 --port 502 --unit-id 1
```

This matches the part 0 VirtualBox layout: run the simulator on the host
machine, with its VirtualBox Host-Only adapter at `192.168.88.100`, and leave
the PLC VM on the same Host-Only network behind the pfSense LAN. The simulator
binds to all interfaces by default; `--host 192.168.88.100` restricts it to the
lab adapter. On Linux, binding the Factory I/O-compatible port 502 requires
elevated privileges, hence `sudo`; on systems that permit unprivileged binding
or when running as administrator, omit it as appropriate.

In OpenPLC's generic Modbus TCP slave device, set the remote IP to
`192.168.88.100`, port to `502`, unit ID to `1`, six discrete inputs starting
at address 0, and five coils starting at address 0. There are no registers.
If you chose a different Host-Only address in VirtualBox, use that address
both for the simulator's `--host` and as the OpenPLC device's remote IP. Ensure
the host firewall allows TCP port 502 from the lab subnet; no port forwarding
or NAT is needed between the PLC VM and host-only adapter.

### I/O map

Addresses are zero-based. Inputs are read with Modbus function 02 and outputs
are written as coils with function 05 or 15.

| Address | Direction | Signal | Meaning |
| --- | --- | --- | --- |
| 0 | Discrete input | StartButton | CLI `start` pulses this input for 250 ms |
| 1 | Discrete input | SafetyDoorClosed | 1 means closed; 0 means open |
| 2 | Discrete input | BoxAtSensor | Box at the conveyor pickup point |
| 3 | Discrete input | RobotDetected | Robot is down at the pickup point over a box |
| 4 | Discrete input | MovingZ | Z axis is transitioning |
| 5 | Discrete input | Rotating | Robot is rotating |
| 0 | Coil | Conveyor | Advance the box toward the pickup point |
| 1 | Coil | Grab | Pick up or release the box |
| 2 | Coil | ExtendZ | Extend the arm; 0 retracts it |
| 3 | Coil | RotateCW | Rotate the arm toward the drop point |
| 4 | Coil | RotateCCW | Return the arm toward the conveyor |

The simulator creates a box automatically every five seconds by default. Its
interactive prompt also supports `start`, `box`, `door open`, `door close`,
`auto on`, `auto off`, and `status`. A box moves while the conveyor coil is
energized, is picked when the arm is down at the pickup point with `Grab`
energized, and is counted as removed when released at the drop point. Opening
the safety door pauses process motion.

This is a small behavioral model rather than a 3D scene or a safety-rated
industrial simulation. It is intended for lab learning and protocol
integration, not for controlling physical equipment.

### Modbus traffic analysis lab

The simulator supports the Modbus exchanges examined in the
[Wireshark tutorial](https://rodrigocantera.com/en/dissecting-openplc-modbus-tcp-communications-with-wireshark/):
OpenPLC can poll six discrete inputs with function 02 and write the five
actuator coils with function 15. The simulator echoes each request's
transaction identifier. Modbus/TCP traffic is unencrypted and this simulator
does not authenticate clients, so capture only on an isolated, authorized lab
network. In Wireshark, filter with `tcp.port == 502` (or the port selected
with `--port`).

The [Scapy packet-injection tutorial](https://rodrigocantera.com/en/modbus-tcp-packet-injection-with-scapy/)
also depends on TCP session sequence state; a syntactically valid Modbus
request by itself does not bypass the operating system's TCP checks. This
simulator uses a normal TCP socket and does not provide a packet-injection
utility or bypass. Conduct any packet-injection exercises only in an isolated
lab you own or are authorized to test.

Run its tests with:

```sh
python3 -m unittest
```