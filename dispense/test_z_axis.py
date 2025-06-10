import os
import sys
import time

# --- Setup .NET imports ---
# Ensure D2Controller.py and the 'dlls' folder are accessible.
# This assumes 'test_z_axis.py' is in the same directory as 'D2Controller.py'
# and the 'dlls' folder is in the parent directory.
try:
    # Add the DLL directory to the path
    dll_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dlls"))
    sys.path.append(dll_dir)
    
    # Import the controller and required .NET types
    from D2Controller import D2Controller
    import clr
    clr.AddReference("UKRobotics.Common")
    from UKRobotics.Common.Maths import Distance, DistanceUnitType
    from System import TimeSpan
except ImportError as e:
    print(f"Error importing necessary modules: {e}")
    print("Please ensure D2Controller.py is in the same directory and the 'dlls' folder is correctly located.")
    sys.exit(1)
except Exception as e:
    print(f"Failed to load .NET assemblies: {e}")
    print("Please ensure the DLLs are in the correct directory and pythonnet is installed.")
    sys.exit(1)


def run_z_axis_test(com_port: str):
    """
    Connects to the D2 controller and tests Z-axis movement.
    
    :param com_port: The COM port of the D2 device (e.g., 'COM3').
    """
    print("Initializing D2 Controller for Z-axis test...")
    # Use a 'with' statement to ensure dispose() is called automatically
    try:
        with D2Controller() as controller:
            print(f"Attempting to open communications on {com_port}...")
            controller.open_comms(com_port)
            print("Communications opened successfully.")

            # It's good practice to clear any pre-existing errors
            print("Clearing any existing motor error flags...")
            controller.clear_motor_error_flags()

            # The Z-axis must be homed before it can be moved to an absolute position.
            # The move_z_to_dispense_height method handles this automatically.

            # --- Test 1: Move to 10mm ---
            height_50 = Distance.Parse("50mm")
            print(f"\nMoving Z-axis to {height_50}...")
            controller.move_z_to_dispense_height(height_50)
            print("Move to 10mm complete. Waiting for 3 seconds...")
            time.sleep(3)

            # --- Test 2: Move to 20mm ---
            height_20 = Distance.Parse("20mm")
            print(f"\nMoving Z-axis to {height_20}...")
            controller.move_z_to_dispense_height(height_20)
            print("Move to 20mm complete. Waiting for 3 seconds...")
            time.sleep(3)
            
            # --- Return to a safe position ---
            print("\nReturning to 10mm...")
            controller.move_z_to_dispense_height(height_50)
            print("Move to 10mm complete.")

            # It's good practice to park the arms when done.
            print("\nParking arms for safety...")
            controller.park_arms()
            print("Arms parked.")

            print("\nZ-axis test finished successfully.")

    except Exception as e:
        print(f"\nAN ERROR OCCURRED: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\nScript finished. Controller connection should be closed.")


if __name__ == "__main__":
    # !!! IMPORTANT !!!
    # REPLACE 'COM3' with the actual COM port for your D2 dispenser.
    # On Windows, it will be 'COMx' (e.g., 'COM3').
    # On Linux, it might be '/dev/ttyACMx' or '/dev/ttyUSBx'.
    PORT = "COM4"
    
    run_z_axis_test(PORT)

