# dispenselib/protocol/protocol_handler.py
"""
Handles conversion between Python-native data structures and .NET ProtocolData objects,
as well as importing and exporting protocols from/to CSV files.
"""
from typing import List as PythonList, Dict, Any
import uuid
from collections import defaultdict

# Import the centralized DLL loader from the parent package.
from dispenselib.utils.dlls import ProtocolData, ProtocolWell, ProtocolCsvImporter, ProtocolCsvExporter, D2DataAccess, List
from UKRobotics.Common.Maths import Volume, VolumeUnitType

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
