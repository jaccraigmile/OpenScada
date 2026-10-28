import socket
import struct
import threading
import unittest

from factoryio_simulator import (
    COIL_COUNT,
    DEFAULT_MODBUS_PORT,
    INPUT_COUNT,
    ModbusServer,
    Process,
    process_pdu,
)


class ModbusProcessTests(unittest.TestCase):
    def setUp(self):
        self.process = Process(auto_emitter=False)

    def test_reads_six_discrete_inputs(self):
        response = process_pdu(self.process, b"\x02\x00\x00\x00\x06")

        self.assertEqual(len(response), 3)
        self.assertEqual(response[0], 2)
        self.assertEqual(response[1], 1)
        self.assertEqual(response[2] & 0b00000010, 0b00000010)

    def test_reads_and_writes_coils(self):
        response = process_pdu(self.process, b"\x05\x00\x00\xff\x00")
        read_response = process_pdu(self.process, b"\x01\x00\x00\x00\x05")

        self.assertEqual(response, b"\x05\x00\x00\xff\x00")
        self.assertEqual(read_response, b"\x01\x01\x01")
        self.assertEqual(len(self.process.read_coils(0, COIL_COUNT)), COIL_COUNT)

    def test_writes_multiple_coils(self):
        response = process_pdu(self.process, b"\x0f\x00\x00\x00\x05\x01\x15")

        self.assertEqual(response, b"\x0f\x00\x00\x00\x05")
        self.assertEqual(
            self.process.read_coils(0, COIL_COUNT),
            [True, False, True, False, True],
        )

    def test_rejects_addresses_outside_tutorial_io_map(self):
        self.assertEqual(
            process_pdu(self.process, b"\x02\x00\x06\x00\x01"),
            b"\x82\x02",
        )
        self.assertEqual(
            process_pdu(self.process, b"\x01\x00\x05\x00\x01"),
            b"\x81\x02",
        )
        self.assertEqual(len(self.process.read_inputs()), INPUT_COUNT)

    def test_process_box_moves_and_is_detected(self):
        self.process.add_box()
        self.process.write_coils(0, [True])
        self.process.step(10.0, 4.0)

        self.assertTrue(self.process.read_inputs()[2])

    def test_open_door_prevents_process_motion(self):
        self.process.add_box()
        self.process.write_coils(0, [True])
        self.process.set_door(False)
        self.process.step(10.0, 4.0)

        self.assertEqual(self.process.box_position, 0.0)

    def test_server_handles_openplc_modbus_tcp_request(self):
        server = ModbusServer(("127.0.0.1", 0), self.process)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            with socket.create_connection(server.server_address, timeout=2) as client:
                request = struct.pack(">HHHB", 0x1234, 0, 6, 1)
                client.sendall(request + b"\x02\x00\x00\x00\x06")
                response = client.recv(64)
            self.assertEqual(
                response,
                struct.pack(">HHHB", 0x1234, 0, 4, 1) + b"\x02\x01\x02",
            )
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()

    def test_factory_io_default_modbus_port(self):
        self.assertEqual(DEFAULT_MODBUS_PORT, 502)


if __name__ == "__main__":
    unittest.main()
