from dispenselib.D2Controller import D2Controller

PROTOCOL_ID = "d338f60cb0d79fb0d16c00966f373a58"
PLATE_ID = "3c0cdfed-19f9-430f-89e2-29ff7c5f1f20"

with D2Controller() as D2:
    COM_PORTS = D2.get_available_com_ports()

    print(COM_PORTS)
    D2.open_comms(com_port=COM_PORTS[0])

    D2.run_dispense_from_id(PROTOCOL_ID, PLATE_ID)