import traceback
from dispenselib.D2Controller import D2Controller

def run_test_dispense(com_port: str):
    """
    Connects to the D2 controller and runs a full dispense protocol from a web ID.
    
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
            protocol_id = input("Enter the protocol ID (e.g., d338f60cb0d79fb0d16c00966f373a58): ").strip()
            if not protocol_id:
                print("No protocol ID provided. Aborting.")
                return

            # Default to a standard 96-well plate if no input is provided
            plate_type_id = input("Enter the plate type ID (default: 96-well plate): ").strip()
            if not plate_type_id:
                plate_type_id = "3c0cdfed-19f9-430f-89e2-29ff7c5f1f20"

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
    # Use the controller's built-in static method to find available COM ports.
    print("Available COM ports:")
    try:
        available_ports = D2Controller.get_available_com_ports()
        if available_ports:
            for port in available_ports:
                print(port)
        else:
            print("No COM ports found. Please ensure the D2 dispenser is connected.")
            exit() # Exit if no ports are found
    except Exception as e:
        print(f"Could not list COM ports. Error: {e}")
        exit()

    print("\nPlease ensure the D2 dispenser is connected to your computer.")
    com_port_input = input("Enter the COM port for the D2 dispenser: ").strip()
    
    if not com_port_input:
        print("No COM port provided. Exiting.")
        exit()
    
    run_test_dispense(com_port_input)
