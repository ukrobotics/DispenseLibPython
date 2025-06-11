import time
import traceback

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
            print("Pausing for 3 seconds...")
            time.sleep(3)

            # --- Test 2: Move to 20mm ---
            height_20 = Distance.Parse("20mm")
            print(f"\nMoving Z-axis to {height_20}...")
            controller.move_z_to_dispense_height(height_20)
            print("Pausing for 3 seconds...")
            time.sleep(3)
            
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
    # !!! IMPORTANT !!!
    # REPLACE 'COM4' with the actual COM port for your D2 dispenser.
    PORT = "COM4"
    
    run_z_axis_test(PORT)