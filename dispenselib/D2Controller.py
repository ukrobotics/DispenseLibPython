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

    def _execute_local_dispense(self, protocol: Any, plate_type_guid: str):
        """
        Handles the detailed workflow for running a dispense from a local protocol object.
        This method correctly fetches, processes, and applies calibration data.
        """
        try:
            plate_type_guid = plate_type_guid.strip()
            self._controller.ClearMotorErrorFlags()

            # 1. Fetch device-specific and plate-specific data
            device_serial_id = self.read_serial_id()
            plate_type = dlls.D2DataAccess.GetPlateTypeData(plate_type_guid)
            
            # 2. Fetch and correctly process the calibration data (THE CRITICAL FIX)
            print("Fetching and processing calibration data...")
            calibration_data = dlls.D2DataAccess.GetActiveCalibrationData(device_serial_id)
            # This next line is the essential step that was missing.
            dlls.ActiveCalibrationData.UpdateVolumePerShots(calibration_data)
            print("Calibration data processed successfully.")

            # 3. Compile dispense commands using the processed data
            print("Compiling dispense commands...")
            dispense_commands = self._controller.CompileDispense(
                calibration_data, protocol, plate_type
            )

            # 4. Prepare the hardware for dispensing
            plate_height = dlls.Distance(plate_type.Height, dlls.DistanceUnitType.mm)
            dispense_height = plate_height + dlls.Distance.Parse("1mm")
            self.move_z_to_height(dispense_height.GetValue(dlls.DistanceUnitType.mm))
            self.set_clamp(True)
            
            # 5. Send commands to the controller
            print(f"Sending {len(dispense_commands)} commands to the dispenser...")
            for command in dispense_commands:
                # Success and error message are out-parameters in C#, ignored here
                success = True
                error_message = ""
                self._controller.ControlConnection.SendMessageRaw(command, True, success, error_message)

            # 6. Start the dispense and wait for completion
            print("Starting dispense...")
            response = self._controller.ControlConnection.SendMessage("DISPENSE", self._controller.ControllerNumberArms, 0)
            
            # Estimate duration (optional, but good for user feedback)
            duration_millis = 0.0
            response.GetParameter(0, duration_millis)
            duration_estimate_seconds = duration_millis / 1000
            print(f"Estimated dispense duration: {duration_estimate_seconds:.2f} seconds.")

            self.wait_for_dispense_complete(int(duration_estimate_seconds) + 30)

        finally:
            # 7. Cleanup: Ensure motors are disabled and clamp is released
            print("Dispense finished. Cleaning up...")
            try:
                self._controller.DisableAllMotors()
            except Exception as e:
                print(f"Error disabling motors: {e}")
            try:
                self.set_clamp(False)
            except Exception as e:
                print(f"Error releasing clamp: {e}")


    def _run_in_thread(self, target_func, *args):
        """
        A generic helper to run a blocking .NET call in a separate thread,
        allowing the main thread to remain responsive to signals like Ctrl+C.
        """
        exception_holder = []

        def worker():
            """The target function for the dispense thread."""
            try:
                # This is the blocking call
                target_func(*args)
            except Exception as e:
                # If an error occurs in the thread, store it so the main thread can raise it.
                exception_holder.append(e)

        self._dispense_thread = threading.Thread(target=worker)
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
        This method uses the original, direct C# call which handles calibration correctly.
        """
        print(f"Running dispense for protocol ID: {protocol_id}")
        self._run_in_thread(self._controller.RunDispense, protocol_id, plate_type_guid)
        print("Dispense completed.")

    def run_dispense_from_csv(self, csv_file_path: str, plate_type_guid: str):
        """
        Runs a dispense protocol defined in a local CSV file.
        This now uses the new workflow to ensure correct calibration.
        """
        print(f"Importing protocol from {csv_file_path}...")
        protocol = protocol_handler.import_from_csv(csv_file_path)
        print(f"Running dispense from imported CSV protocol: {protocol.Name}")
        self._run_in_thread(self._execute_local_dispense, protocol, plate_type_guid)
        print("Dispense completed.")

    def run_dispense_from_list(self, well_data: List[Dict[str, Any]], plate_type_guid: str):
        """
        Runs a dispense protocol defined dynamically from a Python list.
        This now uses the new workflow to ensure correct calibration.
        """
        print("Generating protocol from Python list...")
        protocol = protocol_handler.from_list(well_data)
        print(f"Running dispense from dynamic protocol: {protocol.Name}")
        self._run_in_thread(self._execute_local_dispense, protocol, plate_type_guid)
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
        # This method is called frequently now, so let's make it quieter.
        # print("Reading device serial ID...")
        serial_id = self._controller.ReadSerialIDFromDevice()
        # print(f"Device Serial ID: {serial_id}")
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