from dispenselib.D2Controller import D2Controller

CSV_PATH = "example_protocol.csv"
PLATE_ID = "3c0cdfed-19f9-430f-89e2-29ff7c5f1f20"

with D2Controller() as D2:
    COM_PORTS = D2.get_available_com_ports()

    print(COM_PORTS)
    D2.open_comms(com_port=COM_PORTS[0])

    D2.run_dispense_from_csv(CSV_PATH, PLATE_ID)