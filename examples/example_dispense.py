import traceback
import serial.tools.list_ports as serial_ports

from dispenselib.D2Controller import D2Controller

def run_test_dispense(com_port: str):
    """
    Connects to the D2 controller and runs a full dispense protocol.
    
    :param com_port: The COM port of the D2 device (e.g., 'COM4').
    """
    # Using a 'with' statement ensures the connection is always closed, even if errors occur.
    try:
        with D2Controller() as controller:
            print(f"Attempting to open communications on {com_port}...")
            controller.open_comms(com_port)
            print("Communications opened successfully.")

            # --- Protocol and Plate Information ---
            # These are example IDs. Replace with your actual IDs from the web application.
            # fallback to "994fc5a85580ff1423a5c2b7646311a6" if no input is provided.
            protocol_id = input("Enter the protocol ID: ")  # Example: "994fc5a85580ff1423a5c2b7646311a6"
            if not protocol_id:
                protocol_id = "994fc5a85580ff1423a5c2b7646311a6"
            plate_type_id = input("Enter the plate type ID: ")  # Example: "ad49c4c6-669a-41d5-9c66-d972ccde8e1a"
            if not plate_type_id:
                plate_type_id = "ad49c4c6-669a-41d5-9c66-d972ccde8e1a"

            print(f"Loading protocol: {protocol_id} and plate type: {plate_type_id}...")

            # This single call now handles the entire dispense process.
            controller.run_dispense_from_id(protocol_id, plate_type_id)
            
            print("\nDispense test finished successfully.")

    except Exception as e:
        print(f"\nAN ERROR OCCURRED: {e}")
        traceback.print_exc()
    
    finally:
        print("\nScript finished. The controller connection should be closed automatically by the 'with' statement.")


if __name__ == "__main__":
    # print all available COM ports
    print("Available COM ports:")
    ports = serial_ports.comports()
    if ports:
        for port in ports:
            print(port.device)
    else:
        print("No COM ports found.")

    print("\nPlease ensure the D2 dispenser is connected to your computer.")
    PORT = input("Enter the COM port for the D2 dispenser (e.g., 'COM4'): ").strip()
    if not PORT:
        PORT = ports[0].device if ports else None
    if not PORT:
        print("No COM port provided. Exiting.")
    
    run_test_dispense(PORT)