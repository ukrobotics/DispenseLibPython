# D2 Dispenser Python API (`dispenselib`)

This library provides a Python interface for the UK Robotics D2 dispenser, intended to aid users and integrators in creating their own custom software. It acts as a wrapper around the official `DispenseLibDotNet` C# libraries.

For general user documentation for the D2, see here: [D2 quick start docs](https://ukrobotics.tech/docs/d2dispenser/quick-start/)

## Requirements

* **Operating System:** Windows (The underlying .NET libraries require the Windows environment).
* **Python Version:** Python 3.11 or newer.
* **Hardware:** UK Robotics D2 Dispenser.
* **Framework:** Microsoft .NET Framework 4.6.1 or later (typically pre-installed on modern Windows systems).

---

## Use Case 1: Standard Library Usage

This section is for users who want to use this library in their own Python projects to control the D2 dispenser without modifying the library itself.

### Installation from GitHub

Since this package is hosted on GitHub, you can install it directly using `pip` and the repository's URL. This command will download the library, install its dependencies (like `pythonnet`), and make the `dispenselib` package available in your Python environment.

Open your terminal or command prompt and run the following command.

```bash
pip install git+https://github.com/UKRobotics/DispenseLibDotPy.git
```

### Quick Start Example

Here’s a simple example of how to connect to the dispenser and run a protocol defined dynamically in your code.

```python
from dispenselib.D2Controller import D2Controller
```

Find the correct COM port for your device

```python
try:
    available_ports = D2Controller.get_available_com_ports()
    if not available_ports:
        print("No COM ports found. Please ensure the D2 dispenser is connected.")
        exit()
    
    print(f"Available COM ports: {available_ports}")
    com_port = input("Enter the COM port for the D2 dispenser: ").strip()

except Exception as e:
    print(f"Could not list COM ports. Error: {e}")
    exit()
```

Define the dispense protocol as a list of dictionaries

```python
my_protocol = [
    {"wellName": "A1", "valve1_ul": 10.5, "valve2_ul": 0},
    {"wellName": "A2", "valve1_ul": 10.5, "valve2_ul": 0},
    {"wellName": "B1", "valve1_ul": 0, "valve2_ul": 50.0},
    {"wellName": "B2", "valve1_ul": 0, "valve2_ul": 50.0},
]
```

Define the plate type (GUID for a standard 96-well plate)

```python
plate_guid = "3c0cdfed-19f9-430f-89e2-29ff7c5f1f20"
```

Connect and run the dispense

```python
try:
    # The 'with' statement ensures the connection is properly closed,
    # even if errors occur or you press Ctrl+C.
    with D2Controller() as d2:
        d2.open_comms(com_port)
        d2.run_dispense_from_list(my_protocol, plate_guid)

except Exception as e:
    print(f"An error occurred: {e}")
```

## Use Case 2: Development & Customization

This section is for developers who want to modify the dispenselib wrapper itself—for example, to add new methods, change existing behavior, or contribute to the project.

### Setup for Development

First, you need to get a local copy of the code. Clone the repository:

```bash
git clone "https://github.com/UKRobotics/DispenseLibDotPy.git"
```

Navigate into the project directory:

```bash
cd DispenseLibDotPy
```

### Installing in Editable Mode

For active development, you should install the package in "editable" mode. This creates a link from your Python environment to your local source code. Any changes you make to the Python files are immediately reflected without needing to reinstall the package.

Run the following command from the root of the project directory:

```bash
pip install -e .
```

(The -e stands for "editable", and the . refers to the current directory)

### Standard Local Installation

Alternatively, you can perform a standard local installation. This copies the files to your Python site-packages directory, just as it would if you installed from GitHub. This is useful for testing the final installation process, but it is less convenient for development, as you must reinstall the package after every change.

```bash
pip install .
```

### Running Tests

After making changes, it is crucial to run the automated tests to ensure you haven't broken any existing functionality. Make sure you have installed the test dependencies:

```bash
pip install pytest pytest-mock
```

Then, run the test suite from the root of the project directory:

```bash
pytest
```
