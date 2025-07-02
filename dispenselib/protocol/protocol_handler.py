# dispenselib/protocol/protocol_handler.py
"""
Handles conversion between Python-native data structures and .NET ProtocolData objects,
as well as importing and exporting protocols from/to CSV files.
"""
from typing import List as PythonList, Dict, Any
import uuid

# Import the centralized DLL loader from the parent package.
from dispenselib.utils.dlls import ProtocolData, ProtocolWell, ProtocolCsvImporter, ProtocolCsvExporter, D2DataAccess, List
from UKRobotics.Common.Maths import Volume, VolumeUnitType

def from_list(well_data: PythonList[Dict[str, Any]]) -> 'ProtocolData':
    """
    Converts a Python list of dictionaries into a .NET ProtocolData object.
    """
    protocol = ProtocolData()
    protocol.Id = str(uuid.uuid4())
    protocol.Name = "Dynamic Python Protocol"
    # Create a .NET List of the specific type ProtocolWell
    protocol.Wells = List[ProtocolWell]()

    for well_dict in well_data:
        well_name = well_dict.get("wellName")
        if not well_name:
            raise ValueError("Each well dictionary must contain a 'wellName' key.")

        protocol_well = ProtocolWell()
        protocol_well.WellName = well_name
        # Create a .NET List of the specific type ValveCommand
        protocol_well.ValveCommands = List[ProtocolWell.ValveCommand]()

        # Valve 1
        v1_vol_ul = well_dict.get("valve1_ul", 0.0)
        v1_command = ProtocolWell.ValveCommand()
        v1_command.ValveNumber = 1
        v1_command.Volume = Volume(float(v1_vol_ul), VolumeUnitType.ul)
        protocol_well.ValveCommands.Add(v1_command)

        # Valve 2
        v2_vol_ul = well_dict.get("valve2_ul", 0.0)
        v2_command = ProtocolWell.ValveCommand()
        v2_command.ValveNumber = 2
        v2_command.Volume = Volume(float(v2_vol_ul), VolumeUnitType.ul)
        protocol_well.ValveCommands.Add(v2_command)

        protocol.Wells.Add(protocol_well)

    return protocol


def to_list(protocol: 'ProtocolData') -> PythonList[Dict[str, Any]]:
    """
    Converts a .NET ProtocolData object into a Python list of dictionaries.
    """
    well_list = []
    for well in protocol.Wells:
        well_dict = {
            "wellName": well.WellName,
            "valve1_ul": well.GetVolume(1).GetValue(VolumeUnitType.ul),
            "valve2_ul": well.GetVolume(2).GetValue(VolumeUnitType.ul)
        }
        well_list.append(well_dict)
    return well_list


def import_from_csv(file_path: str) -> 'ProtocolData':
    """
    Imports a protocol from a CSV file using the .NET importer.
    """
    return ProtocolCsvImporter.Import(file_path)


def export_to_csv(protocol_id: str, file_path: str):
    """
    Exports a protocol to a CSV file using the .NET exporter.
    """
    protocol_to_export = D2DataAccess.GetProtocol(protocol_id)
    ProtocolCsvExporter.Export(protocol_to_export, file_path)
