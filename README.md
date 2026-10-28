# OpenScada

## Python replacement for Factory I/O

[`factoryio_simulator.py`](./factoryio_simulator.py) provides a lightweight,
headless substitute for the Factory I/O scene and Modbus TCP driver described
in parts 3 and 4 of the virtual industrial cybersecurity lab. It uses only the
Python standard library and remains compatible with OpenPLC as the Modbus
client; the simulator does not replace OpenPLC or its control logic.

Run it with Python 3:

```sh
sudo python3 factoryio_simulator.py --host <simulator-vm-scada-ip> --port 502 --unit-id 1
```

In the Proxmox lab, run the simulator in its own Linux VM with a virtual
network interface attached to the `scada` VXLAN VNet. Give that VM a stable
address on the same reachable network as the OpenPLC VM. Replace
`<simulator-vm-scada-ip>` with that address; binding to it keeps Modbus
listening on the lab interface rather than every VM interface. The simulator
VM does not need a Windows host, port forwarding, or a path through pfSense
when OpenPLC and the simulator are connected to the same VNet.

On the simulator VM, install or use Python 3, copy this repository to the VM,
and run the command above from the repository directory. Binding the standard
Modbus port 502 on Linux requires elevated privileges, hence `sudo`. For an
unprivileged run, choose an unused port above 1024 (for example `1502`) and
configure OpenPLC to use that same port.

In OpenPLC's generic Modbus TCP slave device, set the remote IP to the
simulator VM's `scada` address, port to `502`, unit ID to `1`, six discrete
inputs starting at address 0, and five coils starting at address 0. There are
no registers. Allow TCP port 502 through the simulator VM's firewall from the
lab devices that need access. For Wireshark or other lab analysis from an
attacker VM, attach that VM to the same `scada` VNet and capture on its VNet
interface.

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

Run its tests with:

```sh
python3 -m unittest
```
