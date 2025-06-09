
import serial
import time
import json
import clr
import os
import sys

# Add DLL folder to sys.path
DLL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dlls"))
sys.path.append(DLL_DIR)

# Load the assembly (no .dll extension)
clr.AddReference("UKRobotics.MotorControllerLib")


from UKRobotics import MotorControllerLib

class D2Controller: