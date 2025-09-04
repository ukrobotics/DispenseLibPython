"""
Handles conversion between Python-native data structures and .NET ProtocolData objects,
as well as importing and exporting protocols from/to CSV files.
"""

# stdlib
import uuid
from collections import defaultdict
from typing import List as PythonList, Dict, Any

# third-party
from dispenselib.utils.dlls import ProtocolData, ProtocolWell, ProtocolCsvImporter, ProtocolCsvExporter, D2DataAccess, List
from UKRobotics.Common.Maths import Volume, VolumeUnitType

def import_from_csv(file_path: str) -> 'ProtocolData':
    """
    Imports a protocol from a CSV file using the .NET importer.
    """
    return ProtocolCsvImporter.Import(file_path)


def export_to_csv(protocol_id: str, file_path: str) -> None:
    """
    Exports a protocol to a CSV file using the .NET exporter.
    """
    protocol_to_export = D2DataAccess.GetProtocol(protocol_id)
    ProtocolCsvExporter.Export(protocol_to_export, file_path)
