# dispenselib/compiler.py
import math
from typing import List, Dict, Any

# --- .NET Type Imports ---
# These are needed for type hints and accessing properties on the .NET objects
from UKRobotics.D2.DispenseLib.Calibration import ActiveCalibrationData
from UKRobotics.D2.DispenseLib.Protocol import ProtocolData
from UKRobotics.D2.DispenseLib.Labware import PlateTypeData
from UKRobotics.D2.DispenseLib.Common import SBSWellAddress as DotNetSBSWellAddress
from UKRobotics.Common.Maths import Distance, DistanceUnitType, Volume, VolumeUnitType

# --- Python Constants ---
D2_CONSTANTS_MIN_DISPENSE_VOLUME = Volume(0, VolumeUnitType.ul)
VALVE_COUNT = 2

class PyWellAddress:
    def __init__(self, row: int, column: int):
        self.Row = row
        self.Column = column

def interpolate(x1: float, x2: float, y1: float, y2: float, y_val: float) -> float:
    """
    A pure Python implementation of linear interpolation.
    """
    if y2 == y1:
        return (x1 + x2) / 2.0
    return x1 + ((y_val - y1) * (x2 - x1)) / (y2 - y1)

def volume_to_open_time_from_python(calibration_table: Any, volume: Volume) -> int:
    """
    A pure Python re-implementation of the C# CalibrationTable.VolumeToOpenTime method.
    This avoids the final TypeLoadException by performing interpolation in Python.
    """
    points = list(calibration_table.Points) # Convert .NET List to Python list
    if not points:
        return 0

    # Sort points by VolumePerShot to ensure correct interpolation
    points.sort(key=lambda p: p.VolumePerShot.GetValue(VolumeUnitType.ul))

    first_point = points[0]
    if volume <= first_point.VolumePerShot:
        return 0 # Below the scale, return zero open time

    prev_point = first_point
    for i in range(1, len(points)):
        this_point = points[i]
        if prev_point.VolumePerShot <= volume <= this_point.VolumePerShot:
            # The volume is between these two points, interpolate
            open_time = interpolate(
                float(prev_point.OpenTimeUSecs),
                float(this_point.OpenTimeUSecs),
                prev_point.VolumePerShot.Litres,
                this_point.VolumePerShot.Litres,
                volume.Litres
            )
            return int(round(open_time))
        prev_point = this_point

    # If the volume is above the scale, extrapolate from the last two points
    last_point = points[-1]
    second_last_point = points[-2]
    
    # Calculate flow rate (litres per microsecond) from the top of the scale
    time_diff = float(last_point.OpenTimeUSecs - second_last_point.OpenTimeUSecs)
    volume_diff = last_point.VolumePerShot.Litres - second_last_point.VolumePerShot.Litres
    
    if time_diff == 0: # Avoid division by zero
        return last_point.OpenTimeUSecs

    flow_rate_l_per_us = volume_diff / time_diff
    
    if flow_rate_l_per_us == 0: # Avoid division by zero
        return last_point.OpenTimeUSecs
        
    volume_above_last_point = volume.Litres - last_point.VolumePerShot.Litres
    extra_time_us = volume_above_last_point / flow_rate_l_per_us
    
    return int(round(last_point.OpenTimeUSecs + extra_time_us))

# --- MODIFY THIS EXISTING FUNCTION ---
def get_dispense_volume_from_python(
    protocol: ProtocolData,
    well_name: str,
    valve_number: int
) -> Volume:
    """
    This function now correctly calls the C# GetVolume method on the ProtocolWell object,
    as confirmed by the ProtocolWell.cs source code.
    """
    # protocol.Wells is a .NET List<ProtocolWell>
    for protocol_well in protocol.Wells:
        # The WellName property on the C# object is a string
        if protocol_well.WellName.lower() == well_name.lower():
            # --- THIS IS THE CORRECTED LINE ---
            # Call the public C# method to get the volume for the specified valve
            return protocol_well.GetVolume(valve_number)
            # --- END CORRECTION ---

    # If the well is not found in the protocol, return a zero volume
    return Volume(0, VolumeUnitType.ul)

def get_calibration_for_valve_number_from_python(
    active_calibration_data: ActiveCalibrationData, 
    valve_number: int
) -> Any:
    """
    A pure Python re-implementation of the C# GetCalibrationForValveNumber method.
    This avoids the final TypeLoadException.
    """
    for channel_cal in active_calibration_data.Calibrations:
        if channel_cal.ValveChannelNumber == valve_number:
            # The Calibrations property is a .NET List<T>. We access the first item.
            if channel_cal.Calibrations.Count > 0:
                return channel_cal.Calibrations[0]
            # If the calibration list for this channel is empty, we'll fall through and raise
            break
    
    # If the loop completes without finding the valve, raise a Python error
    raise ValueError(f"Invalid or missing calibration for valve number {valve_number}")

def get_row_and_column_count_from_python(well_count: int) -> tuple[int, int]:
    if well_count == 6: return 2, 3
    if well_count == 12: return 3, 4
    if well_count == 24: return 4, 6
    if well_count == 48: return 6, 8
    if well_count == 96: return 8, 12
    if well_count == 384: return 16, 24
    if well_count == 1536: return 32, 48
    else:
        d = math.sqrt(well_count)
        return int(round(d)), int(round(d))

def get_well_name_from_indices(row_index: int, col_index: int) -> str:
    row_name = ""
    n = row_index
    while n >= 0:
        row_name = chr(ord('A') + n % 26) + row_name
        n = n // 26 - 1
    return f"{row_name}{col_index + 1}"

def get_column_address_iterator_from_python(well_count: int, row_index: int) -> List[PyWellAddress]:
    _, cols = get_row_and_column_count_from_python(well_count)
    line_wells = []
    for col_index in range(cols):
        well_address = PyWellAddress(row=row_index, column=col_index)
        line_wells.append(well_address)
    return line_wells

def get_well_sequence_lines(well_count: int) -> List[List[PyWellAddress]]:
    rows, _ = get_row_and_column_count_from_python(well_count)
    well_lines = []
    for row_index in range(rows):
        line_wells = get_column_address_iterator_from_python(well_count, row_index)
        well_lines.append(line_wells)
    return well_lines

# --- Translated C# Helper Functions ---

def get_dispense_well_delta_microns(well_count: int) -> int:
    return 250 if well_count > 384 else 750

def get_well_xy(plate_type: PlateTypeData, well: PyWellAddress) -> tuple[Distance, Distance]:
    pitch = Distance(plate_type.WellPitch, DistanceUnitType.mm)
    x_offset_a1 = Distance(plate_type.XOffsetA1, DistanceUnitType.mm)
    y_offset_a1 = Distance(plate_type.YOffsetA1, DistanceUnitType.mm)

    x = x_offset_a1 + (pitch * well.Column)
    y = y_offset_a1 + (pitch * well.Row)
    
    return x, y

def get_dispense_duration_microseconds(
    valve_number: int,
    active_calibration_data: ActiveCalibrationData,
    well: PyWellAddress,
    protocol: ProtocolData,
    well_count: int
) -> int:
    """
    This now uses the pure Python helper to calculate the open time.
    """
    duration_microseconds = 0
    well_name = get_well_name_from_indices(well.Row, well.Column)
    
    calibration = get_calibration_for_valve_number_from_python(active_calibration_data, valve_number)
    dispense_volume = get_dispense_volume_from_python(protocol, well_name, valve_number)

    if dispense_volume > D2_CONSTANTS_MIN_DISPENSE_VOLUME:
        # OLD LINE: duration_microseconds = calibration.VolumeToOpenTime(dispense_volume)
        # --- THIS IS THE CHANGE ---
        duration_microseconds = volume_to_open_time_from_python(calibration, dispense_volume)
        # --- END CHANGE ---
        
    return duration_microseconds

def get_well_name_from_indices(row_index: int, col_index: int) -> str:
    """
    Generates an SBS well name (e.g., "A1", "H12") from zero-based indices.
    """
    row_name = ""
    n = row_index
    while n >= 0:
        row_name = chr(ord('A') + n % 26) + row_name
        n = n // 26 - 1
    return f"{row_name}{col_index + 1}"

def get_column_address_iterator_from_python(well_count: int, row_index: int) -> List[PyWellAddress]:
    """
    This function MUST return a list of our pure Python PyWellAddress objects.
    """
    _, cols = get_row_and_column_count_from_python(well_count)
    line_wells = []
    for col_index in range(cols):
        # Create and append our new, safe Python object
        well_address = PyWellAddress(row=row_index, column=col_index)
        line_wells.append(well_address)
    return line_wells

# --- MODIFY THIS EXISTING FUNCTION ---
def get_well_sequence_lines(well_count: int) -> List[List[PyWellAddress]]:
    """
    This function now correctly creates and returns lists of PyWellAddress objects.
    """
    rows, _ = get_row_and_column_count_from_python(well_count)
    well_lines = []
    for row_index in range(rows):
        line_wells = get_column_address_iterator_from_python(well_count, row_index)
        well_lines.append(line_wells)
    return well_lines

# --- Main Compiler Function (Translated from C#) ---

def compile_dispense_from_python(
    controller_number_arms: int,
    active_calibration_data: ActiveCalibrationData,
    protocol_data: ProtocolData,
    plate_type: PlateTypeData
) -> List[str]:
    # ... (This function's logic remains the same, as it now uses the updated helpers) ...
    well_count = plate_type.WellCount
    commands = [f"CLR_VALVE_WELL,{controller_number_arms},0"]
    dispense_well_delta_microns = get_dispense_well_delta_microns(well_count)

    for valve_number in range(1, VALVE_COUNT + 1):
        reverse_line = False
        well_lines = get_well_sequence_lines(well_count)
        
        for well_line in well_lines:
            if not well_line: continue

            x_approach_direction = -1
            if reverse_line:
                x_approach_direction = 1
                well_line.reverse()

            non_zero_dispense_on_line = False
            well_params_list = []

            for well in well_line:
                xy_x, xy_y = get_well_xy(plate_type, well)
                x_um = int(round(xy_x.GetValue(DistanceUnitType.um)))
                y_um = int(round(xy_y.GetValue(DistanceUnitType.um)))

                duration_microseconds = get_dispense_duration_microseconds(
                    valve_number,
                    active_calibration_data,
                    well,
                    protocol_data,
                    well_count
                )

                if duration_microseconds > 0:
                    non_zero_dispense_on_line = True
                
                well_params_list.append(f"{x_um},{y_um},{x_approach_direction},{duration_microseconds},1")

            if non_zero_dispense_on_line:
                well_count_on_line = len(well_line)
                all_well_params = ",".join(well_params_list)
                
                request_string = (
                    f"VALVE_WELL,{controller_number_arms},0,{valve_number},"
                    f"{dispense_well_delta_microns},{well_count_on_line},{all_well_params}"
                )
                commands.append(request_string)
                reverse_line = not reverse_line
                
    return commands