# D2 Dispenser Python API (`dispenselib`)

This library provides a Python interface for the UK Robotics D2 dispenser, intended to aid users and integrators in creating their own custom software. It acts as a wrapper around the official `DispenseLibDotNet` C# libraries.

For general user documentation for the D2, see here: [D2 quick start docs](https://ukrobotics.tech/docs/d2dispenser/quick-start/)

## Requirements

* **Operating System:** Windows (The underlying .NET libraries require the Windows environment).
* **Python Version:** Python 3.11 or newer.
* **Hardware:** UK Robotics D2 Dispenser.
* **Framework:** Microsoft .NET Framework 4.6.1 or later (typically pre-installed on modern Windows systems).

---

### Installation from GitHub

Since this package is hosted on GitHub, you can install it directly using `pip` and the repository's URL. This command will download the library, install its dependencies (like `pythonnet`), and make the `dispenselib` package available in your Python environment.

Open your terminal or command prompt and run the following command.

```bash
pip install git+https://github.com/UKRobotics/DispenseLibDotPy.git
```