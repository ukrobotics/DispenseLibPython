# DispenseLibDotPy

## Intro

This library is intended to aid users and integrators to create their own software for UK Robotics' D2 dispenser. It is the Python counterpart of [DispenseLibDotNet](https://github.com/ukrobotics/DispenseLibDotNet).

For general user documentation for the D2, see here: [D2 quick start docs](https://ukrobotics.tech/docs/d2dispenser/quick-start/)

## Status

This codebase is currently in BETA - we welcome comments, feedback and collaboration!

## Requirements

* **Operating System:** Windows (The underlying .NET libraries require the Windows environment).
* **Python Version:** Python 3.11 or newer.
* **Hardware:** UK Robotics D2 Dispenser.
* **Framework:** Microsoft .NET Framework 4.6.1 or later (typically pre-installed on modern Windows systems).

---

## Installation from GitHub

Since this package is hosted on GitHub, you can install it directly using `pip` and the repository's URL. This command will download the library, install its dependencies (like `pythonnet`), and make the `dispenselib` package available in your Python environment.

Open your terminal or command prompt and run the following command.

```bash
pip install git+https://github.com/UKRobotics/DispenseLibDotPy.git
```

## Usage

Once the package is installed, the controller is found in `dispenselib.D2Controller`.

```python
from dispenselib.D2Controller import D2Controller
```

Starting a dispense operation requires a protocol (via its UUID or a `.csv` file) and a plate UUID. You can find the Uuid for your protocol and plate at [dispense.ukrobotics.app](https://dispense.ukrobotics.app)

```python
PROTOCOL_ID = "d338f60cb0d79fb0d16c00966f373a58"
PLATE_ID = "3c0cdfed-19f9-430f-89e2-29ff7c5f1f20"

with D2Controller() as D2:
    COM_PORTS = D2.get_available_com_ports()

    print(COM_PORTS)
    D2.open_comms(com_port=COM_PORTS[0])

    D2.run_dispense_from_id(PROTOCOL_ID, PLATE_ID)
```

Running a dispense from a `.csv` requires the same setup, this time specifying the file path and calling a different method.

```python
CSV_PATH = "some_protocol.csv"

D2.run_dispense_from_csv(CSV_PATH, PLATE_ID)
```

You can find these examples under the `/examples` directory of this repository.