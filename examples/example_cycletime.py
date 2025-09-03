import json
import time
import traceback
from typing import List, Dict, Any, Tuple, Optional

# --- Local Imports & .NET Types ---
from dispenselib.D2Controller import D2Controller
# Import the pythonnet CLR and the centralized DLL loader
import clr
from dispenselib.utils.dlls import ActiveCalibrationData, ChannelCalibration, CalibrationTable, CalibrationPoint, List as DotNetList

# --- Self-Contained Calibration Loading and .NET Object Creation ---

class CalibrationData:
    """A simple Python class to hold the data for a single calibration profile."""
    def __init__(self, cal_dict: Dict[str, Any]):
        self._data = cal_dict
        self.id: str = cal_dict.get("_id", "")
        self.valve_type: str = cal_dict.get("valveType", "")
        self.pressure_bar: float = float(cal_dict.get("pressure", 0.0))

    def to_dict(self) -> Dict[str, Any]:
        """Returns the raw dictionary representation of the calibration data."""
        return self._data

class CalibrationLibrary:
    """Loads and stores a collection of CalibrationData objects from a JSON file."""
    def __init__(self, json_filepath: str):
        self.calibrations: List[CalibrationData] = []
        self._load_from_json(json_filepath)

    def _load_from_json(self, json_filepath: str):
        """Loads calibration data from the specified JSON file."""
        print(f"Loading calibrations from {json_filepath}...")
        try:
            with open(json_filepath, 'r') as f:
                data = json.load(f)
                cal_list = data.get("calibrations", [])
                self.calibrations = [CalibrationData(cal) for cal in cal_list]
                print(f"Successfully loaded {len(self.calibrations)} calibration profiles.")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error: Could not load or parse {json_filepath}: {e}")
            self.calibrations = []

def create_active_calibration_object(cal_profile_ch1: Dict, cal_profile_ch2: Dict) -> ActiveCalibrationData:
    """
    Constructs a .NET ActiveCalibrationData object from Python dictionaries.
    This function manually builds the required nested .NET objects.
    """
    # This is the top-level object the controller expects
    active_cal_data = ActiveCalibrationData()
    active_cal_data.Calibrations = DotNetList[ChannelCalibration]()

    # Process calibration for each channel (valve)
    for i, profile in enumerate([cal_profile_ch1, cal_profile_ch2]):
        valve_number = i + 1
        
        # Create the .NET CalibrationTable
        cal_table = CalibrationTable()
        cal_table.Density = float(profile.get("density", 1000.0))
        cal_table.FluidName = profile.get("fluidName", "Default Fluid")
        cal_table.Pressure = float(profile.get("pressure", 0.0))
        cal_table.Points = DotNetList[CalibrationPoint]()

        # Create and add each .NET CalibrationPoint
        for point_dict in profile.get("points", []):
            point = CalibrationPoint()
            point.OpenTimeUSecs = int(point_dict.get("openTimeUSecs", 0))
            point.InterShotTimeUSecs = int(point_dict.get("interShotTimeUSecs", 0))
            point.ShotCount = int(point_dict.get("shotCount", 0))
            point.MassGrams = float(point_dict.get("massGrams", 0.0))
            cal_table.Points.Add(point)
        
        # This is the CRITICAL post-processing step for the calibration table to be valid
        cal_table.UpdateVolumePerShots()

        # Wrap the table in a ChannelCalibration object
        channel_cal = ChannelCalibration()
        channel_cal.ValveChannelNumber = valve_number
        channel_cal.Calibrations = DotNetList[CalibrationTable]()
        channel_cal.Calibrations.Add(cal_table)
        
        # Add the completed channel calibration to the main object
        active_cal_data.Calibrations.Add(channel_cal)

    return active_cal_data

# --- Main Script Logic ---

VALVE_TYPE_TO_DIAMETER_MM = {"19508": 0.45, "19518": 0.1, "19524": 0.2, "19542": 0.6, "19555": 0.3, "22209": 0.2, "24613": 0.45, "25430": 0.45}
PLATE_GUID_MAPPING = {}
MEASUREMENT_FILE = "examples/measurements.txt"

def log_measurement(measurement_data: Dict[str, Any]):
    """Appends a new measurement record to the measurements.txt file."""
    measurements = []
    try:
        with open(MEASUREMENT_FILE, 'r') as f:
            measurements = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        measurements = []
    measurements.append(measurement_data)
    with open(MEASUREMENT_FILE, 'w') as f:
        json.dump(measurements, f, indent=2)

def load_json_file(filename: str) -> Any:
    """Loads a generic JSON file and returns its content."""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error: Could not load or parse {filename}: {e}")
        return None

def find_latest_calibration_for_valve_pressure(cal_library: CalibrationLibrary, valve_type: str, pressure_bar: float, tolerance=0.01) -> Optional[CalibrationData]:
    """Finds the newest calibration for a specific valve and pressure."""
    matches = [cal for cal in cal_library.calibrations if cal.valve_type == valve_type and abs(cal.pressure_bar - pressure_bar) <= tolerance]
    if not matches:
        return None
    matches.sort(key=lambda c: c.id, reverse=True)
    return matches[0]

def get_plate_dimensions(well_count: int) -> Optional[Tuple[int, int]]:
    """Returns the (rows, columns) for standard plate types."""
    return {96: (8, 12), 384: (16, 24), 1536: (32, 48), 24: (4, 6), 48: (6, 8)}.get(well_count)

def generate_well_names(rows: int, cols: int) -> List[str]:
    """Generates a list of well names in row-major order (A1, A2, etc.)."""
    def get_row_label(r_idx: int) -> str:
        label = ""
        while r_idx >= 0:
            label = chr(ord('A') + r_idx % 26) + label
            r_idx = r_idx // 26 - 1
        return label
    return [f"{get_row_label(r)}{c+1}" for r in range(rows) for c in range(cols)]

def run_dispense_test(controller: D2Controller, test_run: Dict[str, Any]) -> Optional[float]:
    """Executes a dispense, measures the duration, and logs the result."""
    plate_info, volume_ul = test_run["plate_info"], test_run["volume"]
    plate_guid = plate_info.get("Id")
    if not plate_guid: return None

    dimensions = get_plate_dimensions(plate_info.get("WellCount", 0))
    if not dimensions: return None
    well_names = generate_well_names(dimensions[0], dimensions[1])
    well_data = [{"wellName": well, "valve1_ul": volume_ul, "valve2_ul": 0.0} for well in well_names]

    # Use the new, self-contained function to create the .NET object
    python_cal_profile = test_run["cal_to_use"]
    active_cal_object = create_active_calibration_object(
        cal_profile_ch1=python_cal_profile.to_dict(),
        cal_profile_ch2=python_cal_profile.to_dict() # Use same profile for both valves
    )

    try:
        result = controller.run_dispense_from_list(well_data, plate_guid, calibration_data=active_cal_object)
        if result is None:
            print("Error: run_dispense_from_list returned None.")
            return None
            
        estimated_duration_ms, actual_duration_s = result
        valve_diameter = VALVE_TYPE_TO_DIAMETER_MM.get(test_run['valve'], "Unknown")

        log_measurement({
            "valve_diameter_mm": valve_diameter, "pressure_bar": test_run['pressure'],
            "well_count": plate_info.get('WellCount', 0), "volume_ul": test_run['volume'],
            "estimated_time_ms": round(estimated_duration_ms, 2), "actual_time_s": round(actual_duration_s, 4)
        })
        return actual_duration_s
        
    except Exception as e:
        print(f"An error occurred during the dispense run: {e}")
        traceback.print_exc()
        return None

def main():
    """Main function to build and execute the test plan."""
    plates_data = load_json_file("examples/plates.json")
    if not plates_data: return
    
    plates = plates_data.get("plates", [])
    global PLATE_GUID_MAPPING
    PLATE_GUID_MAPPING = {p['Name']: p['Id'] for p in plates if 'Name' in p and 'Id' in p}

    cal_library = CalibrationLibrary("calibrations.json")
    if not cal_library.calibrations: return

    print("--- D2 Dispenser Cycle Time Test Runner ---")

    experiment_combinations = []
    seen = set()
    for cal in cal_library.calibrations:
        if cal.valve_type in VALVE_TYPE_TO_DIAMETER_MM and (cal.valve_type, cal.pressure_bar) not in seen:
            experiment_combinations.append({"valve_type": cal.valve_type, "pressure": cal.pressure_bar})
            seen.add((cal.valve_type, cal.pressure_bar))
    
    volumes_to_test = [0.1, 0.5, 1, 2.5, 5, 10, 20, 45, 80, 125, 250, 300, 500, 1000, 2000]

    print("\nBuilding test plan...")
    full_test_plan = []
    for combo in experiment_combinations:
        rep_cal = find_latest_calibration_for_valve_pressure(cal_library, combo["valve_type"], combo["pressure"])
        if not rep_cal: continue
        for plate in plates:
            if plate.get('Name') not in PLATE_GUID_MAPPING: continue
            for vol in volumes_to_test:
                if vol <= plate.get('WellVolume', 0):
                    full_test_plan.append({"valve": combo["valve_type"], "pressure": combo["pressure"], "volume": vol,
                                           "plate_name": plate['Name'], "plate_info": plate, "cal_to_use": rep_cal})
    
    print("\n--- GENERATED TEST PLAN ---")
    if not full_test_plan:
        print("No valid test combinations could be generated.")
        return
        
    for i, run in enumerate(full_test_plan, 1):
        print(f"{i}: {{Valve: {VALVE_TYPE_TO_DIAMETER_MM.get(run['valve'])}mm, Pressure: {run['pressure']} bar, Vol: {run['volume']} µL, Plate: {run['plate_info'].get('WellCount')}-well}}")
    
    try:
        input("\nPress Enter to begin the test run, or Ctrl+C to cancel.")
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return

    print("\n--- Device Connection ---")
    try:
        ports = D2Controller.get_available_com_ports()
        if not ports:
            print("No COM ports found. Ensure D2 dispenser is connected."); return
        print("Available COM ports:", ", ".join(ports))
        port = ports[0] if len(ports) == 1 else input("Enter COM port: ").strip()
        if not port:
            print("No COM port provided. Exiting."); return
    except Exception as e:
        print(f"Could not list COM ports. Error: {e}"); return

    try:
        with D2Controller() as controller:
            controller.open_comms(port)
            for i, run_details in enumerate(full_test_plan, 1):
                print(f"Running Test {i}/{len(full_test_plan)}: {{Valve: {VALVE_TYPE_TO_DIAMETER_MM.get(run_details['valve'])}mm, Pressure: {run_details['pressure']}, Vol: {run_details['volume']}, Plate: {run_details['plate_info'].get('WellCount')}-well}}")
                duration = run_dispense_test(controller, run_details)
                if duration:
                    print(f"  -> SUCCESS: Dispense completed in {duration:.2f} seconds.\n")
                else:
                    print(f"  -> FAILED: Test did not complete successfully.\n")
                time.sleep(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nA critical error occurred: {e}"); traceback.print_exc()
    finally:
        print("\nTest run finished.")

if __name__ == "__main__":
    main()