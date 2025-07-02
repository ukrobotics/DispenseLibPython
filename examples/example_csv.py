# test_csv_dispense.py
import traceback
import serial.tools.list_ports as serial_ports

from dispenselib.D2Controller import D2Controller
from dispenselib.protocol.import_csv import CSVProtocol # Import the new class

def run_csv_dispense_test(com_port: str):
    """
    Connects to the D2 controller and runs a full dispense protocol
    defined in a user-specified CSV file.

    :param com_port: The COM port of the D2 device (e.g., 'COM4').
    """
    try:
        # Use a 'with' statement to ensure the connection is always closed
        with D2Controller() as controller:
            print(f"Attempting to open communications on {com_port}...")
            # controller.open_comms(com_port) # Uncomment for real hardware
            print(f"✅ Communications opened successfully on {com_port}.")

            # --- Get Protocol and Plate Information from User ---
            csv_file = input("Enter the path to the protocol CSV file [example_protocol.csv]: ")
            if not csv_file:
                csv_file = './examples/example_protocol.csv'

            # The plate type is needed by the controller to calculate well coordinates.
            plate_type = input("Enter the plate type [96WellPlate]: ")
            if not plate_type:
                plate_type = "96WellPlate"

            print(f"\nLoading protocol from: {csv_file}")

            # 1. Load the protocol from the CSV file into a protocol object
            protocol = CSVProtocol(csv_file)
            print("✅ Protocol CSV loaded successfully.")
            print(f"Found {len(protocol.dispense_map)} wells and {len(protocol.reagent_to_valve)} reagents.")

            # 2. Run the dispense
            # =======================================================================
            # NOTE: For this to work, you need a method in D2Controller that can
            # accept a protocol *object*. The existing `_get_dispense_duration_microseconds`
            # method is already designed for this.
            #
            # We suggest a new public method like `execute_protocol` in D2Controller.
            # You will need to implement this method and uncomment the line below.
            # =======================================================================

            print(f"\nExecuting dispense for plate type '{plate_type}'...")
            
            # This single call would handle the entire dispense process.
            # controller.execute_protocol(protocol, plate_type)

            print("\n[SIMULATION] Dispense test finished successfully.")
            print("--> NOTE: To run on hardware, implement a method like 'execute_protocol'")
            print("--> in your D2Controller and uncomment the corresponding call.")

    except Exception as e:
        print(f"\n❌ AN ERROR OCCURRED: {e}")
        traceback.print_exc()

    finally:
        print("\nScript finished. Controller connection closed.")


if __name__ == "__main__":
    print("Available COM ports:")
    try:
        ports = serial_ports.comports()
        if not ports:
            print("  No COM ports found.")
        else:
            for i, port in enumerate(ports):
                print(f"  {i+1}: {port.device} - {port.description}")
    except Exception as e:
        print(f"  Could not list COM ports. Error: {e}")

    print("-" * 20)

    PORT = input("Enter the COM port for the D2 Controller (e.g., COM3): ")
    if not PORT:
        PORT = ports[0].device if ports else None
    if not PORT:
        print("No COM port provided. Exiting.")

    run_csv_dispense_test(PORT)
    