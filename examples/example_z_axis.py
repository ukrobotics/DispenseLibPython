import time
import traceback
import serial.tools.list_ports as serial_ports

# 1. Import the main controller. This initializes the .NET runtime.
from dispenselib.D2Controller import D2Controller

# 2. Now that the runtime is initialized, import any required .NET types.
#    The C# namespaces are available as if they were Python modules.
from UKRobotics.Common.Maths import Distance

def run_z_axis_test(com_port: str):
    """
    Connects to the D2 controller and tests Z-axis movement.
    
    :param com_port: The COM port of the D2 device (e.g., 'COM4').
    """
    try:
        with D2Controller() as controller:
            print(f"Attempting to open communications on {com_port}...")
            controller.open_comms(com_port)
            print("Communications opened successfully.")

            # It's good practice to clear any pre-existing errors
            controller.clear_motor_error_flags()
            
            # --- Test 1: Move to 50mm ---
            height_50 = Distance.Parse("50mm")
            print(f"\nMoving Z-axis to {height_50}...")
            controller.move_z_to_dispense_height(height_50)
            time.sleep(1)

            # --- Test 2: Move to 20mm ---
            height_20 = Distance.Parse("20mm")
            print(f"\nMoving Z-axis to {height_20}...")
            controller.move_z_to_dispense_height(height_20)
            time.sleep(1)
            
            # --- Return to a safe position ---
            # For clarity, defining the 10mm height separately
            height_10 = Distance.Parse("10mm")
            print(f"\nReturning to {height_10}...")
            controller.move_z_to_dispense_height(height_10)

            # Park the arms for safety when done with testing.
            controller.park_arms()

            print("\nZ-axis test finished successfully.")

    except Exception as e:
        print(f"\nAN ERROR OCCURRED: {e}")
        traceback.print_exc()
    
    finally:
        print("\nScript finished. The controller connection is closed automatically by the 'with' statement.")


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
    
    run_z_axis_test(PORT)