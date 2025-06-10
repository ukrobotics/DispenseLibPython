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
    PORT = "COM4"
    
    run_z_axis_test(PORT)

