import sys
import os
import time
import traceback

try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dispense_dir = os.path.join(current_dir, "..", "dispenselib")
    sys.path.append(dispense_dir)
    from D2Controller import D2Controller

except ImportError:
    print("Error: D2Controller.py not found.")
    print("Please ensure your directory structure is correct and your virtual environment is active.")
    sys.exit(1)


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
            protocol_id = "994fc5a85580ff1423a5c2b7646311a6"
            plate_type_id = "ad49c4c6-669a-41d5-9c66-d972ccde8e1a" # Example: Corning 96 Well Plate 360 µL Flat

            print(f"Loading protocol: {protocol_id} and plate type: {plate_type_id}...")
            
            # This single call now handles the entire dispense process.
            controller.run_dispense(protocol_id, plate_type_id)
            
            print("\nDispense test finished successfully.")

    except Exception as e:
        print(f"\nAN ERROR OCCURRED: {e}")
        traceback.print_exc()
    
    finally:
        print("\nScript finished. The controller connection should be closed automatically by the 'with' statement.")


if __name__ == "__main__":
    # !!! IMPORTANT !!!
    # REPLACE 'COM4' with the actual COM port for your D2 dispenser.
    PORT = "COM4"
    
    run_test_dispense(PORT)
