# MIT License
#
# Copyright (c) 2021 UK ROBOTICS
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, a to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# ____________________________________________________________________________
#
# For support - please contact us at www.ukrobotics.com
#

import clr
import os
import sys
import time
import math
import threading
from enum import Enum
from typing import List

# Set up path to the DLLs
try:
    dll_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dlls"))
    sys.path.append(dll_dir)

    # Load core .NET assemblies
    clr.AddReference("UKRobotics.Common")
    clr.AddReference("UKRobotics.MotorControllerLib")
    clr.AddReference("UKRobotics.D2.DispenseLib")

    # Import the main namespaces/assemblies to access their types
    import UKRobotics.Common as UKRCommon
    import UKRobotics.MotorControllerLib as UKRMotorControllerLib
    import UKRobotics.D2.DispenseLib as UKRD2DispenseLib
    from System import TimeSpan, DateTime
    
    # --- CHANGE IS HERE ---
    # Add an explicit import for the enum to prevent pathing errors.
    from UKRobotics.Common.Maths import DistanceUnitType
    # --- END OF CHANGE ---

except Exception as e:
    print(f"Failed to load .NET assemblies: {e}")
    print("Please ensure the DLLs are in the correct directory and pythonnet is installed.")
    # Define dummy classes to allow script to be parsed without the DLLs
    class Dummy:
        def __getattr__(self, name):
            if name == 'ControllerParam': return Dummy()
            return lambda *args, **kwargs: Dummy()
    UKRCommon, UKRMotorControllerLib, UKRD2DispenseLib = Dummy(), Dummy(), Dummy()
    TimeSpan, DateTime, DistanceUnitType = None, None, None


class D2Controller:
    """
    The primary class for controlling the D2 dispenser in Python.
    """

    class DispenseState(Enum):
        Error = -1
        Ended = 1

    class ValveCommandState(Enum):
        Idle = 0
        Pending = 1

    VALVE_COUNT = 2
    SERIAL_ID_PARAM_ID = int(UKRMotorControllerLib.ControllerParam.UserData1) + 60

    def __init__(self, controller_number_z_axis=2, axis_number_z_axis=1, controller_axis_count=2):
        self.controller_number_arms = 1
        self.controller_number_z_axis = controller_number_z_axis
        self.axis_number_z_axis = axis_number_z_axis
        self.controller_axis_count = controller_axis_count
        self.control_connection = None
        self.controller_arms = None
        self.controller_z = None
        self.z_axis = None
        self.arm1 = None
        self.arm2 = None

    def open_comms(self, com_port, baud=115200):
        self.control_connection = UKRMotorControllerLib.ControlConnection(com_port, baud)
        self.controller_arms = UKRMotorControllerLib.Controller(self.control_connection, self.controller_number_arms, self.controller_axis_count)
        self.controller_z = UKRMotorControllerLib.Controller(self.control_connection, self.controller_number_z_axis, self.controller_axis_count)
        self.z_axis = self.controller_z.GetAxis(self.axis_number_z_axis)
        self.arm1 = self.controller_arms.GetAxis(1)
        self.arm2 = self.controller_arms.GetAxis(2)

    def dispose(self):
        if self.control_connection:
            try:
                self.control_connection.Dispose()
            except Exception as e:
                print(f"Error disposing control connection: {e}")
        self.control_connection = None
        self.controller_arms = None
        self.controller_z = None
        self.z_axis = None
        self.arm1 = None
        self.arm2 = None

    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.dispose()

    def read_serial_id_from_device(self) -> str:
        return self.controller_arms.ReadString(self.SERIAL_ID_PARAM_ID)

    def run_dispense(self, protocol_id: str, plate_type_guid: str):
        try:
            plate_type_guid = plate_type_guid.strip()
            protocol_id = protocol_id.strip()
            self.clear_motor_error_flags()
            device_serial_id = self.read_serial_id_from_device()
            plate_type = UKRD2DispenseLib.DataAccess.D2DataAccess.GetPlateTypeData(plate_type_guid)
            thread_results = {'dispense_commands': None}
            def data_access_task():
                thread_results['dispense_commands'] = self.compile_dispense(device_serial_id, protocol_id, plate_type)
            def z_and_clamp_task():
                # --- CHANGE IS HERE ---
                # Use the directly imported DistanceUnitType enum
                plate_height = UKRCommon.Maths.Distance(plate_type.Height, DistanceUnitType.mm)
                # --- END OF CHANGE ---
                dispense_height = plate_height + UKRCommon.Maths.Distance.Parse("1mm")
                self.move_z_to_dispense_height(dispense_height)
                self.set_clamp(True)
            data_access_thread = threading.Thread(target=data_access_task)
            z_and_clamp_thread = threading.Thread(target=z_and_clamp_task)
            data_access_thread.start()
            z_and_clamp_thread.start()
            data_access_thread.join()
            z_and_clamp_thread.join()
            dispense_commands = thread_results['dispense_commands']
            for command in dispense_commands:
                success, error_message = self.control_connection.SendMessageRaw(command, True)
                if not success: raise Exception(f"Failed to send dispense command: {error_message}")
            duration_estimate = self._start_dispense()
            self.wait_for_dispense_complete(duration_estimate)
        finally:
            try: self.disable_all_motors()
            except Exception as e: print(f"Error disabling motors: {e}")
            try: self.set_clamp(False)
            except Exception as e: print(f"Error releasing clamp: {e}")

    # In D2Controller.py, replace the existing move_z_to_dispense_height with this one.

    # In D2Controller.py, replace the existing move_z_to_dispense_height with this one.

    def move_z_to_dispense_height(self, dispense_height: 'UKRCommon.Maths.Distance'):
        """
        Move the valve head to the given dispense height relative to the base of the plate.
        Blocks until move is complete and will auto-home the Z-axis if required.
        :param dispense_height: The height to move to.
        """
        # --- Start of New Diagnostic Function ---
        print("\n--- Z-AXIS MOVE LOG START ---")
        
        # We use ReadBoolean on the IAxis object as it's the only read method confirmed to work.
        is_homed = self.z_axis.ReadBoolean(UKRMotorControllerLib.ControllerParam.IsHomed)
        print(f"[DIAGNOSTIC PRE-MOVE] Is Z-axis homed? {is_homed}")
        
        if not is_homed:
            print("[HOMING] Z-axis not homed. Initiating homing sequence...")
            self.z_axis.Home()
            print("[HOMING] Waiting for homing completion...")
            self.z_axis.WaitForIsHomed(TimeSpan.FromSeconds(40))
            print("[HOMING] Homing complete.")

        height_microns = int(round(dispense_height.GetValue(DistanceUnitType.um)))
        print(f"[COMMAND] Target height: {dispense_height} ({height_microns} um)")

        # Check settled status before the move command is sent
        is_settled_before = self.z_axis.ReadBoolean(UKRMotorControllerLib.ControllerParam.IsPositionSettled)
        print(f"[DIAGNOSTIC PRE-MOVE] IsPositionSettled: {is_settled_before}")

        print(f"[COMMAND] Sending MOVE_Z to controller...")
        self.control_connection.SendMessage("MOVE_Z", self.controller_number_z_axis, self.axis_number_z_axis, height_microns)
        print("[COMMAND] MOVE_Z command sent.")

        # Insert a significant delay to ensure the motor has started its move
        # and its state has been updated internally.
        print("[DIAGNOSTIC] Pausing for 2 seconds...")
        time.sleep(2)

        # Check the settled status AFTER the diagnostic delay
        is_settled_after_delay = self.z_axis.ReadBoolean(UKRMotorControllerLib.ControllerParam.IsPositionSettled)
        print(f"[DIAGNOSTIC POST-DELAY] IsPositionSettled: {is_settled_after_delay}")

        print("[WAIT] Now calling the library's WaitForPositionSettledAndInRange function...")

        self.z_axis.WaitForPositionSettledAndInRange(TimeSpan.FromSeconds(30))
        print("[WAIT] Call to WaitForPositionSettledAndInRange has returned.")

        # Check the final settled status
        is_settled_after_wait = self.z_axis.ReadBoolean(UKRMotorControllerLib.ControllerParam.IsPositionSettled)
        print(f"[DIAGNOSTIC POST-WAIT] IsPositionSettled: {is_settled_after_wait}")
        print("--- Z-AXIS MOVE LOG END ---\n")
        # --- End of New Diagnostic Function ---

    def _get_well_xy(self, plate_type: 'UKRD2DispenseLib.Labware.PlateTypeData', well: 'UKRD2DispenseLib.Labware.SBSWellAddress') -> 'UKRCommon.Maths.XYPoint':
        # --- CHANGE IS HERE ---
        # Use the directly imported DistanceUnitType enum
        pitch = UKRCommon.Maths.Distance(plate_type.WellPitch, DistanceUnitType.mm)
        x_offset_a1 = UKRCommon.Maths.Distance(plate_type.XOffsetA1, DistanceUnitType.mm)
        y_offset_a1 = UKRCommon.Maths.Distance(plate_type.YOffsetA1, DistanceUnitType.mm)
        # --- END OF CHANGE ---
        x = x_offset_a1 + (pitch * well.Column)
        y = y_offset_a1 + (pitch * well.Row)
        return UKRCommon.Maths.XYPoint(x, y)
    
    # Other methods (omitted for brevity but are unchanged) ...
    def flush(self, valve_number: int, flush_volume: 'UKRCommon.Maths.Volume'):
        try:
            self.clear_motor_error_flags()
            self.park_arms()
            self.move_z_to_dispense_height(UKRCommon.Maths.Distance.Parse("10mm"))
            self.disable_all_motors()
            device_serial_id = self.read_serial_id_from_device()
            calibration_data = UKRD2DispenseLib.DataAccess.D2DataAccess.GetActiveCalibrationData(device_serial_id)
            open_time_usecs = calibration_data.GetCalibrationForValveNumber(valve_number).VolumeToOpenTime(flush_volume)
            command = self.create_valve_command(valve_number, open_time_usecs, 1, 0)
            success, error_message = self.control_connection.SendMessageRaw(command, True)
            if not success:
                raise Exception(error_message)
            timeout_ms = (open_time_usecs / 1000) + 250
            self.await_idle_valve_state(TimeSpan.FromMilliseconds(timeout_ms))
        finally:
            try: self.disable_all_motors()
            except Exception as e: print(f"Error disabling motors during flush: {e}")
            try: self.set_clamp(False)
            except Exception as e: print(f"Error releasing clamp during flush: {e}")

    def await_idle_valve_state(self, timeout: 'TimeSpan'):
        timeout_at = DateTime.Now + timeout
        while True:
            response, success, error_message = self.control_connection.SendMessageRaw(f"GET_VALVE_STATE,{self.controller_number_arms},0", True)
            if not success: raise Exception(f"Failed to get valve state: {error_message}")
            param_success, value = response.GetParameter(0)
            if param_success:
                state = self.ValveCommandState(value)
                if state == self.ValveCommandState.Idle: break
            if DateTime.Now > timeout_at: raise Exception("Timeout waiting for valve idle state")
            time.sleep(0.1)

    def fire_valve(self, valve_number: int, open_time_usecs: int):
        command = self.create_valve_command(valve_number, open_time_usecs, 1, 0)
        success, error_message = self.control_connection.SendMessageRaw(command, True)
        if not success: raise Exception(error_message)

    def set_clamp(self, clamped: bool):
        command_value = 1 if clamped else 0
        self.control_connection.SendMessage("CLAMP", self.controller_number_z_axis, 0, command_value)

    def park_arms(self):
        self.clear_motor_error_flags()
        self.control_connection.SendMessage("PARK", self.controller_number_arms, 0)
        time.sleep(0.5)
        self.arm1.WaitForPositionSettledAndInRange(TimeSpan.FromSeconds(20))
        self.arm2.WaitForPositionSettledAndInRange(TimeSpan.FromSeconds(20))
        self.disable_arms()

    def unpark_arms(self):
        self.clear_motor_error_flags()
        self.control_connection.SendMessage("UNPARK", self.controller_number_arms, 0)
        time.sleep(0.5)
        self.arm1.WaitForPositionSettledAndInRange(TimeSpan.FromSeconds(20))
        self.arm2.WaitForPositionSettledAndInRange(TimeSpan.FromSeconds(20))

    def disable_z(self):
        self.z_axis.SetMode(UKRMotorControllerLib.AxisControllerMode.Disabled)

    def disable_arms(self):
        self.arm1.SetMode(UKRMotorControllerLib.AxisControllerMode.Disabled)
        self.arm2.SetMode(UKRMotorControllerLib.AxisControllerMode.Disabled)

    def disable_all_motors(self):
        self.disable_z()
        self.disable_arms()

    def clear_motor_error_flags(self):
        self.z_axis.Write(UKRMotorControllerLib.ControllerParam.ErrorCode, 0)
        self.arm1.Write(UKRMotorControllerLib.ControllerParam.ErrorCode, 0)
        self.arm2.Write(UKRMotorControllerLib.ControllerParam.ErrorCode, 0)
        
    def _start_dispense(self) -> 'TimeSpan':
        response = self.control_connection.SendMessage("DISPENSE", self.controller_number_arms, 0)
        success, duration_millis = response.GetParameter(0)
        if not success: raise Exception("Failed to start dispense or get duration estimate.")
        return TimeSpan.FromMilliseconds(duration_millis)

    def wait_for_dispense_complete(self, timeout: 'TimeSpan'):
        timeout_at = DateTime.Now + timeout + TimeSpan.FromSeconds(30)
        while DateTime.Now < timeout_at:
            state = self.get_dispense_state()
            if state == self.DispenseState.Error: raise Exception("A dispense error occurred. Check arms for obstructions, plate height, and hose length. See https://ukrobotics.tech/docs/d2dispenser/troubleshooting/")
            if state == self.DispenseState.Ended: return
            time.sleep(0.1)
        raise Exception("Timeout waiting for dispense to finish")

    def get_dispense_state(self) -> DispenseState:
        response_message = self.control_connection.SendMessage("GET_DISPENSE_STATE", self.controller_number_arms, 0)
        success, value = response_message.GetParameter(0)
        if not success: return self.DispenseState.Error
        return self.DispenseState(value)

    def _get_dispense_well_delta_microns(self, well_count: int) -> int:
        return 250 if well_count > 384 else 750

    def compile_dispense(self, device_serial_id_or_cal_data, protocol_id_or_data, plate_type) -> List[str]:
        if isinstance(device_serial_id_or_cal_data, str):
            calibration = UKRD2DispenseLib.DataAccess.D2DataAccess.GetActiveCalibrationData(device_serial_id_or_cal_data)
        else:
            calibration = device_serial_id_or_cal_data
        if isinstance(protocol_id_or_data, str):
            protocol = UKRD2DispenseLib.DataAccess.D2DataAccess.GetProtocol(protocol_id_or_data)
        else:
            protocol = protocol_id_or_data
        well_count = plate_type.WellCount
        commands = [f"CLR_VALVE_WELL,{self.controller_number_arms},0"]
        dispense_well_delta_microns = self._get_dispense_well_delta_microns(well_count)
        for valve_number in range(1, self.VALVE_COUNT + 1):
            reverse_line = False
            well_lines = self._get_well_sequence_lines(well_count)
            for well_line in well_lines:
                if not well_line: continue
                request_parts = [f"VALVE_WELL,{self.controller_number_arms},0,{valve_number},{dispense_well_delta_microns},{len(well_line)}"]
                x_approach_direction = 1 if reverse_line else -1
                if reverse_line: well_line.reverse()
                non_zero_dispense_on_line = False
                for well in well_line:
                    xy = self._get_well_xy(plate_type, well)
                    duration_microseconds = self._get_dispense_duration_microseconds(valve_number, calibration, well, protocol)
                    well_request_string = (f"{int(round(xy.X.GetValue(DistanceUnitType.um)))},"
                                           f"{int(round(xy.Y.GetValue(DistanceUnitType.um)))},"
                                           f"{x_approach_direction},{duration_microseconds},1")
                    request_parts.append(well_request_string)
                    if duration_microseconds > 0: non_zero_dispense_on_line = True
                if non_zero_dispense_on_line:
                    commands.append(",".join(request_parts))
                    reverse_line = not reverse_line
        return commands

    def _get_dispense_duration_microseconds(self, valve_number: int, active_calibration_data, well, protocol) -> int:
        calibration = active_calibration_data.GetCalibrationForValveNumber(valve_number)
        dispense_volume = protocol.GetDispenseVolume(well, valve_number)
        duration_microseconds = 0
        if dispense_volume > UKRD2DispenseLib.Common.D2Constants.MinDispenseVolume:
            duration_microseconds = calibration.VolumeToOpenTime(dispense_volume)
        return duration_microseconds

    def _get_well_sequence_lines(self, well_count: int) -> List[List]:
        success, row_count, column_count = UKRD2DispenseLib.Labware.SBSWellAddress.GetRowAndColumnCountForWellCount(well_count, 0, 0)
        if not success: raise ValueError(f"Invalid well count for plate: {well_count}")
        well_lines = []
        for row_index in range(row_count):
            line_wells_net = UKRD2DispenseLib.Labware.SBSWellAddress.GetColumnAddressIterator(well_count, row_index)
            well_lines.append(list(line_wells_net))
        return well_lines
        
    def create_valve_command(self, valve_number: int, open_time_usecs: int, shot_count: int, inter_shot_time_usecs: int) -> str:
        return (f"VALVE,{self.controller_number_arms},0,"
                f"{valve_number},{open_time_usecs},{shot_count},{inter_shot_time_usecs}")



# Example usage:
if __name__ == '__main__':
    # This is an example of how you might use the D2Controller.
    # You will need to replace 'COM3', the protocol ID, and the plate type GUID
    # with the actual values for your setup.
    
    # NOTE: The .NET DLLs must be in the correct location for this to work.
    
    controller = D2Controller()
    try:
        # COM port on Windows, or e.g. '/dev/ttyUSB0' on Linux
        com_port = 'COM3' 
        print(f"Attempting to open comms on {com_port}...")
        controller.open_comms(com_port)
        print("Comms opened successfully.")
        
        serial_id = controller.read_serial_id_from_device()
        print(f"Device Serial ID: {serial_id}")
        
        # --- Example: Run a full dispense protocol ---
        # Replace with your actual IDs
        protocol_id = "your-protocol-id-guid" 
        plate_type_guid = "your-plate-type-guid"
        
        print(f"\nRunning dispense for protocol '{protocol_id}' on plate '{plate_type_guid}'...")
        # controller.run_dispense(protocol_id, plate_type_guid)
        print("Dispense complete.")

        # --- Example: Flush a valve ---
        valve_to_flush = 1
        # Volume uses the .NET Volume class from the UKRobotics.Common library
        flush_vol = UKRCommon.Maths.Volume.Parse("100ul")
        print(f"\nFlushing valve {valve_to_flush} with {flush_vol}...")
        # controller.flush(valve_to_flush, flush_vol)
        print("Flush complete.")
        
        # --- Example: Manual motor control ---
        print("\nParking arms...")
        controller.park_arms()
        print("Arms parked.")
        
        time.sleep(2)
        
        print("\nUnparking arms...")
        controller.unpark_arms()
        print("Arms unparked.")


    except Exception as e:
        print(f"\nAn error occurred: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        print("\nDisposing controller...")
        controller.dispose()
        print("Controller disposed.")
