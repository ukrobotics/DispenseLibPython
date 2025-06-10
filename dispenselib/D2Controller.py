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
import traceback
from enum import Enum
from typing import List

# Set up path to the DLLs
try:
    dll_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "utils"))
    sys.path.append(dll_dir)

    # Load core .NET assemblies
    clr.AddReference("System")
    clr.AddReference("UKRobotics.Common")
    clr.AddReference("UKRobotics.MotorControllerLib")
    clr.AddReference("UKRobotics.D2.DispenseLib")

    # Import the main namespaces/assemblies to access their types
    import UKRobotics.Common as UKRCommon
    import UKRobotics.MotorControllerLib as UKRMotorControllerLib
    import UKRobotics.D2.DispenseLib as UKRD2DispenseLib
    from System import TimeSpan, DateTime, Threading, Net
    from UKRobotics.Common.Maths import DistanceUnitType
    from UKRobotics.D2.DispenseLib.Common import SBSWellAddress
    from UKRobotics.D2.DispenseLib import D2Constants

    # Force .NET to use modern TLS for web requests
    Net.ServicePointManager.SecurityProtocol = Net.SecurityProtocolType.Tls12

except Exception as e:
    # --- THE FIX IS HERE ---
    # Removed the complex Dummy class. Now, if an import fails,
    # the script will print the true error and exit.
    print(f"A critical error occurred while loading .NET assemblies: {e}")
    print("Please ensure the .NET DLLs are in the correct directory and that 'pythonnet' is installed.")
    traceback.print_exc()
    sys.exit(1) # Exit the script immediately
    # --- END OF FIX ---

class D2Controller:
    """
    The primary class for controlling the D2 dispenser in Python.
    """
    class DispenseState(Enum):
        Error = -1
        Running = 0
        Ended = 1
    class ValveCommandState(Enum): Idle, Pending = 0, 1
    VALVE_COUNT = 2

    def __init__(self, ctl_z_num=2, axis_z_num=1, ctl_axis_count=2):
        self.controller_number_arms = 1
        self.controller_number_z_axis = ctl_z_num
        self.axis_number_z_axis = axis_z_num
        self.controller_axis_count = ctl_axis_count
        final_id_int = int(UKRMotorControllerLib.ControllerParam.UserData1) + 60
        # Using the specific constructor signature you provided
        self.SERIAL_ID_PARAM_ID = UKRMotorControllerLib.ControllerParam(final_id_int, True)
        self.control_connection = self.controller_arms = self.controller_z = self.z_axis = self.arm1 = self.arm2 = None

    def open_comms(self, com_port, baud=115200):
        self.control_connection = UKRMotorControllerLib.ControlConnection(com_port, baud)
        self.controller_arms = UKRMotorControllerLib.Controller(self.control_connection, self.controller_number_arms, self.controller_axis_count)
        self.controller_z = UKRMotorControllerLib.Controller(self.control_connection, self.controller_number_z_axis, self.controller_axis_count)
        self.z_axis = self.controller_z.GetAxis(self.axis_number_z_axis)
        self.arm1 = self.controller_arms.GetAxis(1)
        self.arm2 = self.controller_arms.GetAxis(2)

    def dispose(self):
        if self.control_connection:
            try: self.control_connection.Dispose()
            except Exception as e: print(f"Error disposing control connection: {e}")
        self.control_connection = self.controller_arms = self.controller_z = self.z_axis = self.arm1 = self.arm2 = None

    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): self.dispose()

    def read_serial_id_from_device(self) -> str:
        return self.controller_arms.ReadString(self.SERIAL_ID_PARAM_ID)

    def move_z_to_dispense_height(self, dispense_height: 'UKRCommon.Maths.Distance'):
        if not self.z_axis.ReadBoolean(UKRMotorControllerLib.ControllerParam.IsHomed):
            self.home_z_axis()
        height_microns = int(round(dispense_height.GetValue(DistanceUnitType.um)))
        print(f"Moving Z-axis to {dispense_height} ({height_microns} um)...")
        self.control_connection.SendMessage("MOVE_Z", self.controller_number_z_axis, self.axis_number_z_axis, height_microns)
        try:
            Threading.Thread.BeginThreadAffinity()
            self.z_axis.WaitForPositionSettledAndInRange(TimeSpan.FromSeconds(30))
        finally:
            Threading.Thread.EndThreadAffinity()
        print(f"Move to {dispense_height} complete.")

    def home_z_axis(self):
        print("Homing Z-axis...")
        self.z_axis.Home()
        try:
            Threading.Thread.BeginThreadAffinity()
            self.z_axis.WaitForIsHomed(TimeSpan.FromSeconds(40))
        finally:
            Threading.Thread.EndThreadAffinity()
        print("Homing complete.")

    def park_arms(self):
        self.clear_motor_error_flags()
        print("Parking arms...")
        self.control_connection.SendMessage("PARK", self.controller_number_arms, 0)
        try:
            Threading.Thread.BeginThreadAffinity()
            self.arm1.WaitForPositionSettledAndInRange(TimeSpan.FromSeconds(20))
            self.arm2.WaitForPositionSettledAndInRange(TimeSpan.FromSeconds(20))
        finally:
            Threading.Thread.EndThreadAffinity()
        self.disable_arms()
        print("Arms parked.")

    # Restored function
    def unpark_arms(self):
        self.clear_motor_error_flags()
        print("Unparking arms...")
        self.control_connection.SendMessage("UNPARK", self.controller_number_arms, 0)
        try:
            Threading.Thread.BeginThreadAffinity()
            self.arm1.WaitForPositionSettledAndInRange(TimeSpan.FromSeconds(20))
            self.arm2.WaitForPositionSettledAndInRange(TimeSpan.FromSeconds(20))
        finally:
            Threading.Thread.EndThreadAffinity()
        print("Arms unparked.")

    def run_dispense(self, protocol_id: str, plate_type_guid: str):
        try:
            plate_type_guid = plate_type_guid.strip()
            protocol_id = protocol_id.strip()
            self.clear_motor_error_flags()
            device_serial_id = self.read_serial_id_from_device()
            plate_type = UKRD2DispenseLib.DataAccess.D2DataAccess.GetPlateTypeData(plate_type_guid)
            thread_results = {'dispense_commands': None, 'exception': None}
            def safe_task_wrapper(task_func, name):
                try:
                    task_func()
                except Exception as e:
                    thread_results['exception'] = (name, e, traceback.format_exc())
            def data_access_task():
                thread_results['dispense_commands'] = self.compile_dispense(device_serial_id, protocol_id, plate_type)
            def z_and_clamp_task():
                plate_height = UKRCommon.Maths.Distance(plate_type.Height, DistanceUnitType.mm)
                dispense_height = plate_height + UKRCommon.Maths.Distance.Parse("1mm")
                self.move_z_to_dispense_height(dispense_height)
                self.set_clamp(True)
            data_access_thread = threading.Thread(target=safe_task_wrapper, args=(data_access_task, "data_access"))
            z_and_clamp_thread = threading.Thread(target=safe_task_wrapper, args=(z_and_clamp_task, "z_and_clamp"))
            data_access_thread.start()
            z_and_clamp_thread.start()
            data_access_thread.join()
            z_and_clamp_thread.join()
            if thread_results['exception']:
                name, e, tb = thread_results['exception']
                raise Exception(f"An error occurred in thread '{name}': {e}\n{tb}")
            dispense_commands = thread_results['dispense_commands']
            for command in dispense_commands:
                _, success, error_message = self.control_connection.SendMessageRaw(command, True)
                if not success:
                    raise Exception(f"Failed to send dispense command: {error_message}")
            duration_estimate = self._start_dispense()
            self.wait_for_dispense_complete(duration_estimate)
        finally:
            try: self.disable_all_motors()
            except Exception as e: print(f"Error disabling motors: {e}")
            try: self.set_clamp(False)
            except Exception as e: print(f"Error releasing clamp: {e}")

    # Restored function
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
            _, success, error_message = self.control_connection.SendMessageRaw(command, True)
            if not success:
                raise Exception(error_message)
            timeout_ms = (open_time_usecs / 1000) + 250
            self.await_idle_valve_state(TimeSpan.FromMilliseconds(timeout_ms))
        finally:
            try: self.disable_all_motors()
            except Exception as e: print(f"Error disabling motors during flush: {e}")
            try: self.set_clamp(False)
            except Exception as e: print(f"Error releasing clamp during flush: {e}")

    # Restored function
    def await_idle_valve_state(self, timeout: 'TimeSpan'):
        timeout_at = DateTime.Now + timeout
        try:
            Threading.Thread.BeginThreadAffinity()
            while True:
                response, success, error_message = self.control_connection.SendMessageRaw(
                    f"GET_VALVE_STATE,{self.controller_number_arms},0", True)
                if not success:
                     raise Exception(f"Failed to get valve state: {error_message}")
                
                # --- THE FIX IS HERE ---
                # This GetParameter call also returns only a single integer value.
                value = response.GetParameter(0)
                state = self.ValveCommandState(value)
                # --- END OF FIX ---
                
                if state == self.ValveCommandState.Idle:
                    break
                if DateTime.Now > timeout_at:
                    raise Exception("Timeout waiting for valve idle state")
                time.sleep(0.1)
        finally:
            Threading.Thread.EndThreadAffinity()


    # Restored function
    def fire_valve(self, valve_number: int, open_time_usecs: int):
        command = self.create_valve_command(valve_number, open_time_usecs, 1, 0)
        _, success, error_message = self.control_connection.SendMessageRaw(command, True)
        if not success:
            raise Exception(error_message)

    def wait_for_dispense_complete(self, timeout: 'TimeSpan'):
        timeout_at = DateTime.Now + timeout + TimeSpan.FromSeconds(30)
        try:
            Threading.Thread.BeginThreadAffinity()
            while DateTime.Now < timeout_at:
                state = self.get_dispense_state()
                if state == self.DispenseState.Error:
                    raise Exception("A dispense error occurred. See https://ukrobotics.tech/docs/d2dispenser/troubleshooting/")
                if state == self.DispenseState.Ended:
                    return
                time.sleep(0.1)
        finally:
            Threading.Thread.EndThreadAffinity()
        raise Exception("Timeout waiting for dispense to finish")

    # Restored function
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
                # This logic is different in C# and needs careful translation
                # C# builds one very long string. Python is more efficient building a list and joining later.
                request_parts = [f"VALVE_WELL,{self.controller_number_arms},0,{valve_number},{dispense_well_delta_microns},{len(well_line)}"]
                x_approach_direction = 1 if reverse_line else -1
                if reverse_line:
                    well_line.reverse()
                non_zero_dispense_on_line = False
                for well in well_line:
                    xy = self._get_well_xy(plate_type, well)
                    duration_microseconds = self._get_dispense_duration_microseconds(valve_number, calibration, well, protocol)
                    well_request_string = (f"{int(round(xy.X.GetValue(DistanceUnitType.um)))},"
                                           f"{int(round(xy.Y.GetValue(DistanceUnitType.um)))},"
                                           f"{x_approach_direction},"
                                           f"{duration_microseconds},"
                                           "1")
                    request_parts.append(well_request_string)
                    if duration_microseconds > 0:
                        non_zero_dispense_on_line = True
                if non_zero_dispense_on_line:
                    commands.append(",".join(request_parts))
                    reverse_line = not reverse_line
        return commands

    def _get_well_sequence_lines(self, well_count: int) -> List[List]:
        row_count, column_count = SBSWellAddress.GetRowAndColumnCountForWellCount(well_count, 0, 0)
        well_lines = []
        for row_index in range(row_count):
            line_wells_net = SBSWellAddress.GetColumnAddressIterator(well_count, row_index)
            well_lines.append(list(line_wells_net))
        return well_lines

    def clear_motor_error_flags(self):
        self.z_axis.Write(UKRMotorControllerLib.ControllerParam.ErrorCode, 0)
        self.arm1.Write(UKRMotorControllerLib.ControllerParam.ErrorCode, 0)
        self.arm2.Write(UKRMotorControllerLib.ControllerParam.ErrorCode, 0)
    def disable_arms(self):
        self.arm1.SetMode(UKRMotorControllerLib.AxisControllerMode.Disabled)
        self.arm2.SetMode(UKRMotorControllerLib.AxisControllerMode.Disabled)
    def disable_z(self):
        self.z_axis.SetMode(UKRMotorControllerLib.AxisControllerMode.Disabled)
    def disable_all_motors(self):
        self.disable_z()
        self.disable_arms()
    def set_clamp(self, clamped: bool):
        self.control_connection.SendMessage("CLAMP", self.controller_number_z_axis, 0, 1 if clamped else 0)
    def _start_dispense(self) -> 'TimeSpan':
        response = self.control_connection.SendMessage("DISPENSE", self.controller_number_arms, 0)
        
        # --- THE FIX IS HERE ---
        # This specific GetParameter call returns only a single value (the duration),
        # not a (success, value) tuple.
        duration_millis = response.GetParameter(0)
        # --- END OF FIX ---

        # We assume success if no exception was thrown by SendMessage.
        return TimeSpan.FromMilliseconds(duration_millis)
   # In D2Controller.py

    def get_dispense_state(self) -> DispenseState:
        response_message = self.control_connection.SendMessage("GET_DISPENSE_STATE", self.controller_number_arms, 0)
        value = response_message.GetParameter(0)
        return self.DispenseState(value)
    def _get_dispense_well_delta_microns(self, well_count: int) -> int:
        return 250 if well_count > 384 else 750
    def _get_well_xy(self, plate_type: 'UKRD2DispenseLib.Labware.PlateTypeData', well: 'SBSWellAddress') -> 'UKRCommon.Maths.XYPoint':
        pitch = UKRCommon.Maths.Distance(plate_type.WellPitch, DistanceUnitType.mm)
        x_offset_a1 = UKRCommon.Maths.Distance(plate_type.XOffsetA1, DistanceUnitType.mm)
        y_offset_a1 = UKRCommon.Maths.Distance(plate_type.YOffsetA1, DistanceUnitType.mm)
        x = x_offset_a1 + (pitch * well.Column)
        y = y_offset_a1 + (pitch * well.Row)
        return UKRCommon.Maths.XYPoint(x, y)
    def _get_dispense_duration_microseconds(self, valve_number: int, active_calibration_data, well, protocol) -> int:
        calibration = active_calibration_data.GetCalibrationForValveNumber(valve_number)
        dispense_volume = protocol.GetDispenseVolume(well, valve_number)
        duration_microseconds = 0
        if dispense_volume > D2Constants.MinDispenseVolume:
            duration_microseconds = calibration.VolumeToOpenTime(dispense_volume)
        return duration_microseconds
    # Restored function
    def create_valve_command(self, valve_number: int, open_time_usecs: int, shot_count: int, inter_shot_time_usecs: int) -> str:
        return (f"VALVE,{self.controller_number_arms},0,"
                f"{valve_number},"
                f"{open_time_usecs},"
                f"{shot_count},"
                f"{inter_shot_time_usecs}")