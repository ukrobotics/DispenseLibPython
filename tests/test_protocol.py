import pytest
from unittest.mock import patch, MagicMock
from dispenselib.protocol import protocol_handler


@patch('dispenselib.protocol.protocol_handler.ProtocolCsvImporter')
def test_import_from_csv_calls_dotnet_importer(mock_importer):
    """
    Tests that the import_from_csv function correctly calls the underlying
    .NET importer with the provided file path.
    """
    # Arrange: Define a dummy file path
    file_path = "test_protocol.csv"

    # Act: Call the function we are testing
    protocol_handler.import_from_csv(file_path)

    # Assert: Verify that the .NET Import method was called exactly once
    # with the correct file path.
    mock_importer.Import.assert_called_once_with(file_path)


@patch('dispenselib.protocol.protocol_handler.ProtocolCsvExporter')
@patch('dispenselib.protocol.protocol_handler.D2DataAccess')
def test_export_to_csv_calls_dotnet_exporter(mock_data_access, mock_exporter):
    """
    Tests that the export_to_csv function first fetches the correct protocol
    using the given ID and then calls the underlying .NET exporter with the
    retrieved protocol and file path.
    """
    # Arrange: Set up test data and mock return values
    protocol_id = "test-protocol-uuid"
    file_path = "exported_protocol.csv"

    # Create a mock protocol object to be "returned" by the data access layer
    mock_protocol = MagicMock()
    mock_data_access.GetProtocol.return_value = mock_protocol

    # Act: Call the function we are testing
    protocol_handler.export_to_csv(protocol_id, file_path)

    # Assert: Check that the .NET methods were called in the correct sequence
    # with the correct arguments.
    mock_data_access.GetProtocol.assert_called_once_with(protocol_id)
    mock_exporter.Export.assert_called_once_with(mock_protocol, file_path)


@patch('dispenselib.protocol.protocol_handler.ProtocolCsvImporter')
def test_import_from_csv_file_not_found(mock_importer):
    """
    Tests that the import_from_csv function properly raises a FileNotFoundError
    if the underlying .NET importer indicates that the file does not exist.
    """
    # Arrange: Define the path for a non-existent file
    file_path = "non_existent_file.csv"
    # Configure the mock to raise a FileNotFoundError when called
    mock_importer.Import.side_effect = FileNotFoundError(f"File not found: {file_path}")

    # Act & Assert: Use pytest.raises to confirm that a FileNotFoundError
    # is thrown when the function is called.
    with pytest.raises(FileNotFoundError):
        protocol_handler.import_from_csv(file_path)


@patch('dispenselib.protocol.protocol_handler.D2DataAccess')
@patch('dispenselib.protocol.protocol_handler.ProtocolCsvExporter')
def test_export_to_csv_invalid_protocol_id(mock_exporter, mock_data_access):
    """
    Tests that export_to_csv raises an exception if the provided protocol ID
    is invalid and the data access layer returns None.
    """
    # Arrange: Define an invalid protocol ID and a dummy file path
    protocol_id = "invalid-id"
    file_path = "should_not_be_created.csv"

    # Simulate the .NET data access method returning None for the invalid ID
    mock_data_access.GetProtocol.return_value = None

    # Configure the mock exporter to raise a generic Exception if its Export
    # method is called with None. This simulates how the real .NET library might behave.
    mock_exporter.Export.side_effect = Exception("Protocol object cannot be null")

    # Act & Assert: Check that calling the function with an invalid ID
    # results in an exception being raised.
    with pytest.raises(Exception):
        protocol_handler.export_to_csv(protocol_id, file_path)

    # Also, ensure GetProtocol was called, but Export was not, since the
    # protocol was invalid.
    mock_data_access.GetProtocol.assert_called_once_with(protocol_id)