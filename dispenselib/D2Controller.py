# dispenselib/D2Controller.py
import signal
import sys
import time
import threading
from enum import Enum
from typing import List, Dict, Any

# --- Local Imports ---
from dispenselib.protocol import protocol_handler
from dispenselib.utils import dlls  # Import the centralized DLL loader

class DispenseState(Enum):
    """Represents the state of a dispense operation."""
    Error = -1
    Ended = 1
    Running = 0 # A possible state not explicitly in the C# enum but implied

class D2Controller:
    """
    The primary class for controlling the D2 dispenser in Python.
    This class is a Python-friendly wrapper around the .NET D2Controller.
    """

    def __init__(self):
        """Initializes the D2Controller wrapper and sets up a graceful exit handler."""
        self._controller = dlls.DotNetD2Controller()
        self._dispense_thread = None
        # Register the signal handler for Ctrl+C (SIGINT)
        signal.signal(signal.SIGINT, self._signal_handler)

    @staticmethod
    def get_available_com_ports() -> List[str]:
        """
        Scans for and returns a list of available serial COM ports.
        """
        return list(dlls.SerialPort.GetPortNames())

    def _signal_handler(self, sig, frame):
        """
        Custom handler for Ctrl+C. Actively aborts any running command,
        then ensures the controller connection is disposed before exiting.
        """
        print("\nCtrl+C detected. Sending ABORT command...")
        try:
            self.abort()
        except Exception as e:
            print(f"Could not send ABORT command. Continuing with shutdown. Error: {e}")
        
        print("Shutting down gracefully...")
        self.dispose()
        sys.exit(0)

    def _run_dispense_in_thread(self, protocol_or_id: Any, plate_type_guid: str):
        """
        A private helper to run the blocking .NET dispense call in a separate thread,
        allowing the main thread to remain responsive to signals like Ctrl+C.
        """
        exception_holder = []

        def dispense_worker():
            """The target function for the dispense thread."""
            try:
                # This is the blocking call
                self._controller.RunDispense(protocol_or_id, plate_type_guid)
            except Exception as e:
                # If an error occurs in the thread, store it so the main thread can raise it.
                # This includes exceptions caused by calling dispose() during a run.
                exception_holder.append(e)

        self._dispense_thread = threading.Thread(target=dispense_worker)
        self._dispense_thread.start()

        # Wait for the thread to complete, but with a timeout on join()
        # so that the main thread can be interrupted by signals.
        while self._dispense_thread.is_alive():
            self._dispense_thread.join(timeout=0.1)

        # After the thread has finished, check if it raised an exception.
        if exception_holder:
            # Re-raise the exception in the main thread.
            raise exception_holder[0]

    def open_comms(self, com_port: str, baud: int = 115200):
        """
        Establishes a connection with the D2 dispenser.
        """
        self._controller.OpenComms(com_port, baud)
        print(f"Successfully connected to D2 on {com_port}.")

    def dispose(self):
        """Closes the connection to the D2 dispenser."""
        if self._controller:
            self._controller.Dispose()
            print("Connection to D2 closed.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.dispose()

    # --- Protocol Execution ---

    def run_dispense_from_id(self, protocol_id: str, plate_type_guid: str):
        """
        Runs a dispense protocol fetched from the web service using its ID.
        """
        print(f"Running dispense for protocol ID: {protocol_id}")
        self._run_dispense_in_thread(protocol_id, plate_type_guid)
        print("Dispense completed.")

    def run_dispense_from_csv(self, csv_file_path: str, plate_type_guid: str):
        """
        Runs a dispense protocol defined in a local CSV file.
        """
        print(f"Importing protocol from {csv_file_path}...")
        protocol = protocol_handler.import_from_csv(csv_file_path)
        print(f"Running dispense from imported CSV protocol: {protocol.Name}")
        self._run_dispense_in_thread(protocol, plate_type_guid)
        print("Dispense completed.")

    def run_dispense_from_list(self, well_data: List[Dict[str, Any]], plate_type_guid: str):
        """
        Runs a dispense protocol defined dynamically from a Python list.
        """
        print("Generating protocol from Python list...")
        protocol = protocol_handler.from_list(well_data)
        print(f"Running dispense from dynamic protocol: {protocol.Name}")
        self._run_dispense_in_thread(protocol, plate_type_guid)
        print("Dispense completed.")

    # --- Protocol Management ---

    def export_protocol_to_csv(self, protocol_id: str, file_path: str):
        """
        Fetches a protocol by its ID and exports it to a local CSV file.
        """
        print(f"Exporting protocol {protocol_id} to {file_path}...")
        protocol_handler.export_to_csv(protocol_id, file_path)
        print("Export complete.")

    def get_protocol_as_list(self, protocol_id: str) -> List[Dict[str, Any]]:
        """
        Fetches a protocol by its ID and returns it as a Python list of dictionaries.
        """
        protocol = dlls.D2DataAccess.GetProtocol(protocol_id)
        return protocol_handler.to_list(protocol)

    # --- Core Hardware Commands ---

    def flush(self, valve_number: int, volume_ul: float):
        """
        Flushes a specified valve with a given volume.
        """
        print(f"Flushing valve {valve_number} with {volume_ul} μL...")
        flush_volume = dlls.Volume(volume_ul, dlls.VolumeUnitType.ul)
        self._controller.Flush(valve_number, flush_volume)
        print("Flush complete.")

    def park_arms(self):
        """Parks the dispenser arms."""
        print("Parking arms...")
        self._controller.ParkArms()
        print("Arms parked.")

    def unpark_arms(self):
        """Unparks the dispenser arms."""
        print("Unparking arms...")
        self._controller.UnparkArms()
        print("Arms unparked.")

    def move_z_to_height(self, height_mm: float):
        """
        Moves the Z-axis to a specified height.
        """
        print(f"Moving Z-axis to {height_mm} mm...")
        target_distance = dlls.Distance(height_mm, dlls.DistanceUnitType.mm)
        self._controller.MoveZToDispenseHeight(target_distance)
        print("Z-axis move complete.")

    def read_serial_id(self) -> str:
        """
        Reads the unique serial ID from the connected D2 device.
        """
        print("Reading device serial ID...")
        serial_id = self._controller.ReadSerialIDFromDevice()
        print(f"Device Serial ID: {serial_id}")
        return serial_id

    def set_clamp(self, clamped: bool):
        """
        Sets the state of the plate clamp.
        """
        state = "Engaging" if clamped else "Releasing"
        print(f"{state} clamp...")
        self._controller.SetClamp(clamped)
        print("Clamp command sent.")

    def clear_motor_error_flags(self):
        """
        Clears any error flags on the arm and Z-axis motors.
        """
        print("Clearing motor error flags...")
        self._controller.ClearMotorErrorFlags()
        print("Motor error flags cleared.")

    def get_dispense_state(self) -> DispenseState:
        """
        Gets the current state of the dispense process.
        """
        state_val = self._controller.GetDispenseState()
        try:
            return DispenseState(state_val)
        except ValueError:
            return DispenseState.Running

    def wait_for_dispense_complete(self, timeout_seconds: int = 120):
        """
        Blocks execution until the current dispense operation is complete.
        """
        print("Waiting for dispense to complete...")
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            state = self.get_dispense_state()
            if state == DispenseState.Ended:
                print("Dispense has completed.")
                return
            if state == DispenseState.Error:
                raise RuntimeError("Dispenser reported an error during the dispense operation.")
            time.sleep(0.5)
        
        raise TimeoutError(f"Dispense did not complete within the {timeout_seconds} second timeout.")

    def abort(self):
        """
        Sends a raw ABORT command to immediately stop the current operation on the hardware.
        """
        if self._controller and self._controller.ControlConnection:
            # The command string is based on the JavaScript example
            command = f"ABORT,{self._controller.ControllerNumberArms},0"
            print(f"Sending raw command: {command}")
            # Use the underlying ControlConnection to send the raw command string
            self._controller.ControlConnection.SendMessageRaw(command, False)
            print("ABORT command sent.")