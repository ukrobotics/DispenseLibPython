# examples/example_csv.py
import traceback
import os
from dispenselib.D2Controller import D2Controller

def export_protocol(controller: D2Controller):
    """
    Prompts the user for a protocol ID and a file path, then exports the protocol to a CSV file.
    Note: This operation does not require a connection to the robot, only an internet connection.
    """
    print("\n--- Export Protocol to CSV ---")
    try:
        protocol_id = input("Enter the Protocol ID to export from the web app: ").strip()
        if not protocol_id:
            print("Protocol ID is required. Aborting.")
            return

        default_filename = f"protocol_{protocol_id}.csv"
        file_path = input(f"Enter the path to save the CSV file (e.g., C:\\protocols\\{default_filename}): ").strip()
        if not file_path:
            file_path = default_filename
        
        # Ensure the directory exists
        dir_name = os.path.dirname(file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        print(f"Exporting protocol '{protocol_id}' to '{file_path}'...")
        controller.export_protocol_to_csv(protocol_id, file_path)
        print("\nExport completed successfully.")

    except Exception as e:
        print(f"\nAN ERROR OCCURRED during export: {e}")
        traceback.print_exc()


def run_from_csv(controller: D2Controller, com_port: str):
    """
    Prompts for a CSV file path and plate ID, then runs the dispense.
    This operation requires a connection to the robot.
    """
    print("\n--- Run Dispense from CSV ---")
    try:
        csv_path = input("Enter the full path to the protocol CSV file: ").strip()
        if not os.path.exists(csv_path):
            print(f"Error: File not found at '{csv_path}'. Aborting.")
            return

        # Standard 96-well plate GUID is used as a default
        plate_type_id = input("Enter the plate type ID (default: 96-well plate): ").strip()
        if not plate_type_id:
            plate_type_id = "3c0cdfed-19f9-430f-89e2-29ff7c5f1f20"
        
        print(f"Attempting to open communications on {com_port}...")
        controller.open_comms(com_port)
        print("Communications opened successfully.")

        print(f"Running dispense from '{os.path.basename(csv_path)}' on plate type '{plate_type_id}'...")
        controller.run_dispense_from_csv(csv_path, plate_type_id)
        
        print("\nDispense from CSV finished successfully.")

    except Exception as e:
        print(f"\nAN ERROR OCCURRED during dispense: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    # Using a 'with' statement ensures the connection is always closed, even if errors occur.
    with D2Controller() as main_controller:
        while True:
            print("\n--- D2 CSV Example Menu ---")
            print("1. Export a Protocol from the Web to a CSV file")
            print("2. Run a Dispense from a local CSV file")
            print("3. Exit")
            choice = input("Please select an option (1, 2, or 3): ").strip()

            if choice == '1':
                export_protocol(main_controller)
            
            elif choice == '2':
                print("\nAvailable COM ports:")
                available_ports = D2Controller.get_available_com_ports()
                if available_ports:
                    for port in available_ports:
                        print(port)
                else:
                    print("No COM ports found. Please ensure the device is connected.")
                    continue
                
                com_port_input = input("Enter the COM port for the D2 dispenser: ").strip()
                if not com_port_input:
                    print("No COM port provided. Aborting.")
                    continue
                
                run_from_csv(main_controller, com_port_input)

            elif choice == '3':
                print("Exiting.")
                break
            
            else:
                print("Invalid choice. Please try again.")
    
    print("\nScript finished.")
