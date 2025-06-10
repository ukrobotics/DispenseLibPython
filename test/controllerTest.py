# file: test_d2.py

from dispense.controller import D2Controller

def main():
    # Replace COM3 with your actual port
    port = "COM3"

    try:
        print("Initializing D2 Controller...")
        controller = D2Controller(port)

        print("Controller initialized.")
        
        # Test some behavior (hypothetical)
        print("Moving Z Axis to position 10.0...")
        controller.move_z_axis(10.0)

        print("Done.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'controller' in locals():
            controller.dispose()
            print("Controller disposed.")

if __name__ == "__main__":
    main()
