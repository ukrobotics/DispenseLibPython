# dispenselib/dll.py
"""
This module is responsible for loading all the required .NET DLLs using pythonnet.
It centralizes the complex import logic so that other modules in the package
can access .NET types in a clean and consistent way.
"""
import clr
import os
import sys

try:
    # Determine the absolute path to the 'utils' directory containing the DLLs.
    # This makes the package location-independent.
    dll_dir = os.path.abspath(os.path.dirname(__file__))

    # Add the DLL directory to the system path to help pythonnet find dependencies.
    sys.path.append(dll_dir)

    # Add references to the required .NET assemblies.
    clr.AddReference("System")
    clr.AddReference("System.Collections")
    clr.AddReference("UKRobotics.Common")
    clr.AddReference("UKRobotics.MotorControllerLib")
    clr.AddReference("UKRobotics.D2.DispenseLib")

    # Import specific classes and namespaces to be exposed to the Python code.
    # This acts as the single source of truth for all .NET types used in the wrapper.
    from UKRobotics.D2.DispenseLib import D2Controller as DotNetD2Controller
    from UKRobotics.D2.DispenseLib.Protocol import ProtocolData, ProtocolWell, ProtocolCsvImporter, ProtocolCsvExporter
    from UKRobotics.D2.DispenseLib.DataAccess import D2DataAccess
    from UKRobotics.Common.Maths import Distance, DistanceUnitType, Volume, VolumeUnitType
    from UKRobotics.D2.DispenseLib.Calibration import ActiveCalibrationData, ChannelCalibration, CalibrationTable, CalibrationPoint
    from System import Net
    from System.Collections.Generic import List, Dictionary
    from System.IO.Ports import SerialPort

    # Configure the security protocol to ensure web requests to the UK Robotics service succeed.
    Net.ServicePointManager.SecurityProtocol = Net.SecurityProtocolType.Tls12

except (ImportError, FileNotFoundError) as e:
    # Provide a comprehensive error message if the DLLs can't be loaded.
    raise ImportError(
        "A critical error occurred while loading the .NET DLLs. "
        "Please ensure that all required DLLs are present in the 'dispenselib/utils' directory "
        "and that the 'pythonnet' library is installed correctly. "
        f"Original error: {e}"
    )
