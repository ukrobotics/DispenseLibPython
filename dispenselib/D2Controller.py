# dispenselib/D2Controller.py
import signal
import sys
import time
import threading
from enum import Enum
from typing import List, Dict, Any, Optional
import logging

# --- Local Imports ---
from dispenselib.protocol import protocol_handler
from dispenselib.utils import dlls
from UKRobotics.D2.DispenseLib.Calibration import ActiveCalibrationData

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

class DispenseState(Enum):
    """Represents the state of a dispense operation."""
    Error = -1
    Ended = 1
    Running = 0

class D2Controller:
    """
    The primary class for controlling the D2 dispenser in Python.
    This class is a Python-friendly wrapper around the .NET D2Controller.
    """

    def __init__(self):
        """Initializes the D2Controller wrapper and sets up a graceful exit handler."""
        self._controller = dlls.DotNetD2Controller()
        self._dispense_thread = None
        signal.signal(signal.SIGINT, self._signal_handler)

    @staticmethod
    def get_available_com_ports() -> List[str]:
        """
        Scans for and returns a list of available serial COM ports.
        """
        return list(dlls.SerialPort.GetPortNames())

    def _signal_handler(self, sig, frame):
        """
        Custom handler for Ctrl+C. Actively aborts any running command.
        """
        log.warning("\nCtrl+C detected. Sending ABORT command...")
        try:
            self.abort()
        except Exception as e:
            log.error(f"Could not send ABORT command. Continuing with shutdown. Error: {e}")
        
        log.info("Shutting down gracefully...")
        self.dispose()
        sys.exit(0)

    def _execute_local_dispense(self, protocol: Any, plate_type_guid: str, calibration_data: Optional[ActiveCalibrationData] = None):
        actual_duration_s = 0.0
        estimated_duration_ms = 0.0
        try:
            plate_type = dlls.D2DataAccess.GetPlateTypeData(plate_type_guid)
            
            processed_calibration_data = calibration_data
            if not processed_calibration_data:
                device_serial_id = self.read_serial_id()
                processed_calibration_data = dlls.D2DataAccess.GetActiveCalibrationData(device_serial_id)
                dlls.ActiveCalibrationData.UpdateVolumePerShots(processed_calibration_data)

            log.info("Compiling dispense commands using .NET library...")
            dispense_commands = self._controller.CompileDispense(
                processed_calibration_data, 
                protocol, 
                plate_type
            )

            plate_height = dlls.Distance(plate_type.Height, dlls.DistanceUnitType.mm)
            dispense_height = plate_height + dlls.Distance.Parse("1mm")
            self.move_z_to_height(dispense_height.GetValue(dlls.DistanceUnitType.mm))
            self.set_clamp(True)
            
            for command in dispense_commands:
                self._controller.ControlConnection.SendMessageRaw(command, True)

            response = self._controller.ControlConnection.SendMessage("DISPENSE", self._controller.ControllerNumberArms, 0)
            response.GetParameter(0, estimated_duration_ms)

            start_time = time.time()
            self.wait_for_dispense_complete(int(estimated_duration_ms / 1000) + 30)
            actual_duration_s = time.time() - start_time
        finally:
            log.info("Dispense finished. Cleaning up...")
            try: self._controller.DisableAllMotors()
            except Exception as e: log.error(f"Error disabling motors: {e}")
            try: self.set_clamp(False)
            except Exception as e: log.error(f"Error releasing clamp: {e}")
        
        return estimated_duration_ms, actual_duration_s

    def _run_in_thread(self, target_func, *args, **kwargs):
        result_holder, exception_holder = [], []
        def worker():
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
        self._controller.OpenComms(com_port, baud)
        log.info(f"Successfully connected to D2 on {com_port}.")

    def dispose(self):
        if self._controller:
            self._controller.Dispose()
            log.info("Connection to D2 closed.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.dispose()

    def run_dispense_from_id(self, protocol_id: str, plate_type_guid: str):
        log.info(f"Running dispense for protocol ID: {protocol_id}")
        self._run_in_thread(self._controller.RunDispense, protocol_id, plate_type_guid)
        log.info("Dispense completed.")

    def run_dispense_from_csv(self, csv_file_path: str, plate_type_guid: str, calibration_data: Optional[ActiveCalibrationData] = None):
        log.info(f"Importing protocol from {csv_file_path}...")
        protocol = protocol_handler.import_from_csv(csv_file_path)
        log.info(f"Running dispense from imported CSV protocol: {protocol.Name}")
        result = self._run_in_thread(self._execute_local_dispense, protocol, plate_type_guid, calibration_data=calibration_data)
        log.info("Dispense completed.")
        return result

    def run_dispense_from_list(self, well_data: List[Dict[str, Any]], plate_type_guid: str, calibration_data: Optional[ActiveCalibrationData] = None):
        log.info("Generating protocol from Python list...")
        protocol = protocol_handler.from_list(well_data)
        log.info(f"Running dispense from dynamic protocol: {protocol.Name}")
        result = self._run_in_thread(self._execute_local_dispense, protocol, plate_type_guid, calibration_data=calibration_data)
        log.info("Dispense completed.")
        return result

    def read_serial_id(self) -> str:
        return self._controller.ReadSerialIDFromDevice()

    def set_clamp(self, clamped: bool):
        state = "Engaging" if clamped else "Releasing"
        log.info(f"{state} clamp...")
        self._controller.SetClamp(clamped)

    def move_z_to_height(self, height_mm: float):
        """
        Moves the Z-axis to a specified height using the original C# method.
        """
        log.info(f"Moving Z-axis to {height_mm} mm...")
        target_distance = dlls.Distance(height_mm, dlls.DistanceUnitType.mm)
        self._controller.MoveZToDispenseHeight(target_distance)

    def wait_for_dispense_complete(self, timeout_seconds: float):
        try:
            log.info(f"Waiting for dispense to complete (C# timeout activated)...")
            timeout_span = dlls.TimeSpan.FromSeconds(timeout_seconds)
            self._controller.WaitForDispenseComplete(timeout_span)
            log.info("Dispense has completed.")
        except Exception as e:
            raise RuntimeError(f"An error occurred while waiting for dispense to complete: {e}")

    def abort(self):
        if self._controller and self._controller.ControlConnection:
            command = f"ABORT,{self._controller.ControllerNumberArms},0"
            log.info(f"Sending raw command: {command}")
            self._controller.ControlConnection.SendMessageRaw(command, False)
            log.info("ABORT command sent.")