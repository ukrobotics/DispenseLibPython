# DispenseLib for Python

## Intro

This library provides a Python interface for the UK Robotics D2 dispenser, intended to aid users and integrators in creating their own custom software. It acts as a wrapper around the official `DispenseLibDotNet` C# libraries.

For general user documentation for the D2, see here: [D2 quick start docs](https://ukrobotics.tech/docs/d2dispenser/quick-start/)

## Status

This codebase is currently in **BETA** - we welcome comments, feedback, and collaboration!

## Requirements
* Windows Operating System
* Python 3.7+
* .NET Framework 4.6.1 or later

## Installation

1.  **Clone or Download:** Get the project code, for example by cloning the repository:
    ```bash
    git clone [https://github.com/your_username/your_repo.git](https://github.com/your_username/your_repo.git)
    cd DispenseLibDotPy
    ```

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    venv\Scripts\activate
    ```

3.  **Install Dependencies:** The included `setup.py` file allows you to install the package and its dependencies (`pythonnet`) with a single command. From the project's root directory, run:
    ```bash
    pip install .
    ```
    This will install the `dispenselib` package into your virtual environment, making it importable in your scripts.

## Quick Start Guide

The primary class you will use to control the D2 is `D2Controller`. Integrating the D2 into your Python software is very simple.

After installation, you can import and use the controller in your own scripts:

```python
from dispenselib.D2Controller import D2Controller
import traceback

# Use a 'with' statement to ensure the connection is always properly closed
try:
    with D2Controller() as controller:
        # Open the communications port for your device
        controller.open_comms("COM4")

        # Protocol and plate type IDs are taken from the web apps
        protocol_id = "994fc5a85580ff1423a5c2b7646311a6" # From [https://dispense.ukrobotics.app](https://dispense.ukrobotics.app)
        plate_type_id = "ad49c4c6-669a-41d5-9c66-d972ccde8e1a" # From [https://labware.ukrobotics.app](https://labware.ukrobotics.app)

        # This single command runs the entire dispense protocol and blocks until complete
        controller.run_dispense(protocol_id, plate_type_id)

        print("Dispense finished successfully!")

except Exception as e:
    print(f"An error occurred: {e}")
    traceback.print_exc()