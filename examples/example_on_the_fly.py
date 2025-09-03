from dispenselib.D2Controller import D2Controller

CSV_PATH = "example_protocol_0.5.csv"
PLATE_ID = "3c0cdfed-19f9-430f-89e2-29ff7c5f1f20"
FINAL_VOLUME = 12 # ul
SET_VOLUME = 0.5 # ul

D2 = D2Controller()
COM_PORTS = D2.get_available_com_ports()

print(COM_PORTS)
D2.open_comms(com_port=COM_PORTS[0])

# run the 0.5 ul dispense until the final volume is reached
step = 0
while step < FINAL_VOLUME:
    print(f"Dispensing {step}/{FINAL_VOLUME} ul")
    D2.run_dispense_from_csv(CSV_PATH, PLATE_ID)
    step += SET_VOLUME