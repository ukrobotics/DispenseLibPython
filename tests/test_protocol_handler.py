# tests/test_protocol_handler.py
import pytest
import os
from dispenselib.protocol import protocol_handler

# Mock the .NET imports for testing without the actual DLLs if needed,
# but for this, we assume the dev environment has them.

def test_from_list_conversion():
    """Tests conversion from a Python list to a .NET ProtocolData object."""
    well_data = [
        {"wellName": "A1", "valve1_ul": 10.5, "valve2_ul": 0},
        {"wellName": "H12", "valve1_ul": 5, "valve2_ul": 50.2}
    ]
    protocol = protocol_handler.from_list(well_data)

    assert protocol is not None
    assert protocol.Name == "Dynamic Python Protocol"
    assert protocol.Wells.Count == 2

    # Check well A1
    well_a1 = protocol.GetProtocolWell("A1")
    assert well_a1 is not None
    assert well_a1.GetVolume(1).GetValue(protocol_handler.VolumeUnitType.ul) == 10.5
    assert well_a1.GetVolume(2).GetValue(protocol_handler.VolumeUnitType.ul) == 0

    # Check well H12
    well_h12 = protocol.GetProtocolWell("H12")
    assert well_h12 is not None
    assert well_h12.GetVolume(1).GetValue(protocol_handler.VolumeUnitType.ul) == 5.0
    assert well_h12.GetVolume(2).GetValue(protocol_handler.VolumeUnitType.ul) == 50.2

def test_to_list_conversion():
    """Tests conversion from a .NET ProtocolData object back to a Python list."""
    # First, create a .NET object to convert
    well_data_in = [
        {"wellName": "C3", "valve1_ul": 1.1, "valve2_ul": 2.2}
    ]
    protocol_net = protocol_handler.from_list(well_data_in)

    # Now, convert it back to a Python list
    well_data_out = protocol_handler.to_list(protocol_net)

    assert isinstance(well_data_out, list)
    assert len(well_data_out) == 1
    well_dict = well_data_out[0]
    assert well_dict["wellName"] == "C3"
    assert well_dict["valve1_ul"] == 1.1
    assert well_dict["valve2_ul"] == 2.2

def test_csv_import(tmp_path):
    """Tests importing a protocol from a CSV file."""
    csv_content = "Well,Valve1 (ul),Valve2 (ul)\nA1,15.0,25.0\nB2,100.1,0\n"
    csv_file = tmp_path / "test_protocol.csv"
    csv_file.write_text(csv_content)

    protocol = protocol_handler.import_from_csv(str(csv_file))

    assert protocol is not None
    assert protocol.Wells.Count == 2
    well_b2 = protocol.GetProtocolWell("B2")
    assert well_b2.GetVolume(1).GetValue(protocol_handler.VolumeUnitType.ul) == 100.1
