# dispenselib/D2Controller.py
import signal
import sys
import time
import threading
from enum import Enum
from typing import List, Dict, Any, Optional
import json
import requests
import math

# --- Local Imports ---
from dispenselib.protocol import protocol_handler
from dispenselib.utils import dlls  # Import the centralized DLL loader
from dispenselib.compiler import compile_dispense_from_python
from System import Double
from UKRobotics.D2.DispenseLib.Calibration import ActiveCalibrationData

class DispenseState(Enum):
    """Represents the state of a dispense operation."""
    Error = -1
    Ended = 1
    Running = 0 # A possible state not explicitly in the C# enum but implied

def get_plate_type_data_from_python(guid: str) -> Optional[Any]:
    """
    A pure Python implementation to download and create the PlateTypeData object,
    bypassing all problematic C# I/O and deserialization.
    """
    url = f"https://labware.ukrobotics.app/{guid}.json"
    print(f"Fetching plate data from Python: {url}")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        py_dict = json.loads(response.text)

        # Create an empty .NET PlateTypeData object
        plate_data = dlls.PlateTypeData()

        # Manually assign the properties from the Python dictionary.
        # The pythonnet library will handle converting float to the required decimal type.
        plate_data.Id = py_dict.get("Id")
        plate_data.Name = py_dict.get("Name")
        plate_data.WellCount = int(py_dict.get("WellCount", 0))
        plate_data.WellPitch = py_dict.get("WellPitch", 0.0)
        plate_data.XOffsetA1 = py_dict.get("XOffsetA1", 0.0)
        plate_data.YOffsetA1 = py_dict.get("YOffsetA1", 0.0)
        plate_data.Height = py_dict.get("Height", 0.0)
        plate_data.WellVolume = py_dict.get("WellVolume", 0.0)
        
        return plate_data

    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        print(f"Error processing plate data in Python: {e}")
        raise RuntimeError(f"Could not process plate data for GUID {guid}") from e


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

    def get_dispense_estimate_from_list(self, well_data: List[Dict[str, Any]], plate_type_guid: str, calibration_data: Optional[ActiveCalibrationData] = None) -> Optional[float]:
        """
        Prepares a dispense, starts it to get the time estimate, then immediately aborts.
        """
        print("Generating protocol from Python list for estimation...")
        protocol = protocol_handler.from_list(well_data)
        
        # This can be run in the main thread as it's not a long-running blocking call
        estimated_duration_ms = self._execute_for_estimation(protocol, plate_type_guid, calibration_data)
        
        print("Estimation complete.")
        return estimated_duration_ms

    def _execute_for_estimation(self, protocol: Any, plate_type_guid: str, calibration_data: Optional[ActiveCalibrationData] = None) -> Optional[float]:
        """
        A helper that performs the start-estimate-abort sequence.
        """
        estimated_duration_ms = 0.0
        try:
            plate_type = get_plate_type_data_from_python(plate_type_guid)
            
            processed_calibration_data = calibration_data
            if not processed_calibration_data:
                device_serial_id = self.read_serial_id()
                processed_calibration_data = dlls.D2DataAccess.GetActiveCalibrationData(device_serial_id)
                dlls.ActiveCalibrationData.UpdateVolumePerShots(processed_calibration_data)

            dispense_commands = compile_dispense_from_python(
                self._controller.ControllerNumberArms,
                processed_calibration_data, 
                protocol, 
                plate_type
            )

            plate_height = dlls.Distance(plate_type.Height, dlls.DistanceUnitType.mm)
            dispense_height = plate_height + dlls.Distance.Parse("1mm")
            self.move_z_to_height_from_python(dispense_height.GetValue(dlls.DistanceUnitType.mm))
            self.set_clamp(True)
            
            for command in dispense_commands:
                self._controller.ControlConnection.SendMessageRaw(command, True)

            # Start dispense and immediately get the estimate
            response = self._controller.ControlConnection.SendMessage("DISPENSE", self._controller.ControllerNumberArms, 0)
            if response.ParameterCount > 0:
                estimated_duration_ms = float(response.GetParameter(0)) / 1000
                self.abort()  # Immediately abort after getting the estimate
            else:
                print("Warning: Controller response contained no parameters for estimation.")


            """ self.abort()
            time.sleep(0.5) # Give abort command time to process """

        finally:
            # Cleanup
            print("Cleaning up after estimation...")
            try:
                self._controller.DisableAllMotors()
            except Exception as e:
                print(f"Error disabling motors: {e}")
            try:
                self.set_clamp(False)
            except Exception as e:
                print(f"Error releasing clamp: {e}")
        
        return estimated_duration_ms

    def _execute_local_dispense(self, protocol: Any, plate_type_guid: str, calibration_data: Optional[ActiveCalibrationData] = None):
        """
        Handles the detailed workflow for running a dispense from a local protocol object.
        It can use provided calibration data or fetch the active one from the web.
        """
        actual_duration_s = 0.0
        estimated_duration_ms = 0.0
        try:
            plate_type_guid = plate_type_guid.strip()
            self._controller.ClearMotorErrorFlags()

            # 1. Fetch plate-specific data
            plate_type = get_plate_type_data_from_python(plate_type_guid)
            
            # 2. Use provided calibration data or fetch from the web
            processed_calibration_data = None
            if calibration_data:
                print("Using provided local calibration data.")
                processed_calibration_data = calibration_data
            else:
                print("Fetching and processing active calibration data from the web...")
                device_serial_id = self.read_serial_id()
                processed_calibration_data = dlls.D2DataAccess.GetActiveCalibrationData(device_serial_id)
                dlls.ActiveCalibrationData.UpdateVolumePerShots(processed_calibration_data)
                print("Calibration data processed successfully.")

            # 3. Compile dispense commands
            print("Compiling dispense commands...")
            dispense_commands = compile_dispense_from_python(
                self._controller.ControllerNumberArms,
                processed_calibration_data, 
                protocol, 
                plate_type
            )

            # 4. Prepare hardware
            plate_height = dlls.Distance(plate_type.Height, dlls.DistanceUnitType.mm)
            dispense_height = plate_height + dlls.Distance.Parse("1mm")
            self.move_z_to_height_from_python(dispense_height.GetValue(dlls.DistanceUnitType.mm))
            self.set_clamp(True)
            
            # 5. Send commands
            print(f"Sending {len(dispense_commands)} commands to the dispenser...")
            for command in dispense_commands:
                success = True
                error_message = ""
                self._controller.ControlConnection.SendMessageRaw(command, True, success, error_message)

            # 6. Start dispense and measure time
            print("Starting dispense...")
            response = self._controller.ControlConnection.SendMessage("DISPENSE", self._controller.ControllerNumberArms, 0)
            response.GetParameter(0, estimated_duration_ms)

            start_time = time.time()
            self.wait_for_dispense_complete(int(estimated_duration_ms / 1000) + 30)
            actual_duration_s = time.time() - start_time

        finally:
            # 7. Cleanup
            print("Dispense finished. Cleaning up...")
            try:
                self._controller.DisableAllMotors()
            except Exception as e:
                print(f"Error disabling motors: {e}")
            try:
                self.set_clamp(False)
            except Exception as e:
                print(f"Error releasing clamp: {e}")
        
        return estimated_duration_ms, actual_duration_s


    def _run_in_thread(self, target_func, *args, **kwargs):
        """
        A generic helper to run a blocking .NET call in a separate thread.
        Now supports keyword arguments.
        """
        result_holder = []
        exception_holder = []

        def worker():
            """The target function for the dispense thread."""
            try:
                result = target_func(*args, **kwargs)
                result_holder.append(result)
            except Exception as e:
                exception_holder.append(e)

        self._dispense_thread = threading.Thread(target=worker)
        self._dispense_thread.start()

        while self._dispense_thread.is_alive():
            self._dispense_thread.join(timeout=0.1)

        if exception_holder:
            raise exception_holder[0]
        
        return result_holder[0] if result_holder else None

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
        # This original method doesn't return anything.
        self._run_in_thread(self._controller.RunDispense, protocol_id, plate_type_guid)
        print("Dispense completed.")

    def run_dispense_from_csv(self, csv_file_path: str, plate_type_guid: str, calibration_data: Optional[ActiveCalibrationData] = None):
        """
        Runs a dispense protocol defined in a local CSV file.
        Accepts an optional pre-loaded calibration object.
        """
        print(f"Importing protocol from {csv_file_path}...")
        protocol = protocol_handler.import_from_csv(csv_file_path)
        print(f"Running dispense from imported CSV protocol: {protocol.Name}")
        result = self._run_in_thread(self._execute_local_dispense, protocol, plate_type_guid, calibration_data=calibration_data)
        print("Dispense completed.")
        return result

    def run_dispense_from_list(self, well_data: List[Dict[str, Any]], plate_type_guid: str, calibration_data: Optional[ActiveCalibrationData] = None):
        """
        Runs a dispense protocol defined dynamically from a Python list.
        Accepts an optional pre-loaded calibration object.
        """
        print("Generating protocol from Python list...")
        protocol = protocol_handler.from_list(well_data)
        print(f"Running dispense from dynamic protocol: {protocol.Name}")
        result = self._run_in_thread(self._execute_local_dispense, protocol, plate_type_guid, calibration_data=calibration_data)
        print("Dispense completed.")
        return result

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

    def move_z_to_height_from_python(self, height_mm: float):
        """
        A pure Python re-implementation of the C# MoveZToDispenseHeight method.
        This avoids the final TypeLoadException by performing calculations in Python.
        """
        print(f"Moving Z-axis to {height_mm} mm (Python implementation)...")
        # Use the underlying .NET objects for hardware interaction
        z_axis = self._controller.ZAxis
        
        # 1. Check if homed and home if necessary
        if not z_axis.ReadBoolean(dlls.ControllerParam.IsHomed):
            print("Z-axis not homed. Homing now...")
            z_axis.Home()
            time.sleep(1) # Small wait to ensure homing has started
            z_axis.WaitForIsHomed(dlls.TimeSpan.FromSeconds(40))
            print("Z-axis homing complete.")

        # 2. Calculate height in microns using Python's math
        target_distance = dlls.Distance(height_mm, dlls.DistanceUnitType.mm)
        height_microns = int(round(target_distance.GetValue(dlls.DistanceUnitType.um)))

        # 3. Send the raw move command
        self._controller.ControlConnection.SendMessage(
            "MOVE_Z",
            self._controller.ControllerNumberZAxis,
            self._controller.AxisNumberZAxis,
            height_microns
        )

        # 4. Wait for the move to settle
        z_axis.WaitForPositionSettledAndInRange(dlls.TimeSpan.FromSeconds(30))
        print("Z-axis move complete.")

    def read_serial_id(self) -> str:
        """
        Reads the unique serial ID from the connected D2 device.
        """
        serial_id = self._controller.ReadSerialIDFromDevice()
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

    def wait_for_dispense_complete(self, timeout_seconds: float):
        """
        Blocks until the dispense is complete by calling the original C# method,
        which is more reliable than a Python-based polling loop.
        """
        try:
            print(f"Waiting for dispense to complete (C# timeout activated)...")
            # Create a .NET TimeSpan object from the provided seconds
            timeout_span = dlls.TimeSpan.FromSeconds(timeout_seconds)
            # Call the underlying, robust C# method directly
            self._controller.WaitForDispenseComplete(timeout_span)
            print("Dispense has completed.")
        except Exception as e:
            # Catch exceptions from the C# side (like a timeout) and re-raise as a Python error
            raise RuntimeError(f"An error occurred while waiting for dispense to complete: {e}")

    def abort(self):
        """
        Sends a raw ABORT command to immediately stop the current operation on the hardware.
        """
        if self._controller and self._controller.ControlConnection:
            command = f"ABORT,{self._controller.ControllerNumberArms},0"
            print(f"Sending raw command: {command}")
            self._controller.ControlConnection.SendMessageRaw(command, False)
            print("ABORT command sent.")