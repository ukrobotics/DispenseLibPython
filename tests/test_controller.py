# tests/test_controller.py
import pytest
import signal
import sys
from unittest.mock import MagicMock, patch

# We patch the 'dll' module at the top level to replace the actual .NET objects
# with mock objects for all tests in this file.
@pytest.fixture(autouse=True)
def mock_dotnet_dependencies(mocker):
    """Mocks all .NET dependencies for the entire test session."""
    mocker.patch('dispenselib.utils.dlls.DotNetD2Controller', return_value=MagicMock())
    mocker.patch('dispenselib.utils.dlls.ProtocolData', return_value=MagicMock())
    mocker.patch('dispenselib.utils.dlls.D2DataAccess', return_value=MagicMock())
    mocker.patch('dispenselib.protocol.protocol_handler.from_list', return_value=MagicMock())
    mocker.patch('dispenselib.protocol.protocol_handler.import_from_csv', return_value=MagicMock())


# Correctly import the D2Controller CLASS from the D2Controller MODULE
from dispenselib.D2Controller import D2Controller

@pytest.fixture
def controller():
    """
    Provides a D2Controller instance within a context manager for each test,
    ensuring that resources are properly released after the test runs.
    """
    with D2Controller() as d2:
        yield d2
    # The __exit__ method (which calls dispose) is automatically handled here.

def test_open_comms_calls_dotnet_method(controller: D2Controller):
    """
    Tests that the open_comms method calls the underlying .NET method correctly.
    """
    # Act
    controller.open_comms("COM3", 9600)

    # Assert
    # Check that the underlying .NET controller's OpenComms method was called correctly
    controller._controller.OpenComms.assert_called_once_with("COM3", 9600)

def test_context_manager_calls_dispose(mocker):
    """
    Tests that using the D2Controller as a context manager automatically calls dispose.
    This test verifies the __exit__ method's behavior.
    """
    # We need to spy on the dispose method for this specific test
    spy_dispose = mocker.spy(D2Controller, 'dispose')

    with D2Controller() as d2:
        d2.open_comms("COM3")
        # The .NET OpenComms method on the mock object should have been called
        d2._controller.OpenComms.assert_called_once_with("COM3", 115200)

    # Assert that dispose was called exactly once when exiting the 'with' block
    spy_dispose.assert_called_once()

def test_run_dispense_from_list(controller: D2Controller):
    """
    Tests that run_dispense_from_list correctly calls the protocol handler
    and the underlying .NET RunDispense method.
    """
    # Arrange
    test_protocol_list = [{"wellName": "A1", "valve1_ul": 10}]
    plate_guid = "test-plate-guid"
    
    # Act
    controller.run_dispense_from_list(test_protocol_list, plate_guid)

    # Assert
    # Verify that the protocol handler was called with our Python list
    from dispenselib.protocol import protocol_handler
    protocol_handler.from_list.assert_called_once_with(test_protocol_list)
    
    # Verify that the .NET RunDispense method was called with the result
    # from the protocol handler and the correct plate GUID.
    controller._controller.RunDispense.assert_called_once()
    # We check the arguments it was called with
    args, _ = controller._controller.RunDispense.call_args
    assert args[0] is protocol_handler.from_list.return_value
    assert args[1] == plate_guid

def test_signal_handler_graceful_exit(mocker):
    """
    Tests that the Ctrl+C signal handler calls dispose and exits.
    """
    # Arrange
    # Mock the methods we expect to be called by the signal handler
    mock_dispose = mocker.patch.object(D2Controller, 'dispose')
    mock_exit = mocker.patch.object(sys, 'exit')

    # Act
    # Create a controller instance to register the signal handler
    controller_instance = D2Controller()
    # Manually invoke the handler, simulating a Ctrl+C event
    controller_instance._signal_handler(signal.SIGINT, None)

    # Assert
    # Check that dispose and sys.exit were both called exactly once
    mock_dispose.assert_called_once()
    mock_exit.assert_called_once_with(0)
