# file: dispense/d2_controller.py

import clr
import os
import sys

dll_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dlls"))
sys.path.append(dll_dir)
clr.AddReference("UKRobotics.MotorControllerLib")

from UKRobotics.MotorControllerLib import D2Controller as D2ControllerDotNet

class D2Controller:
    def __init__(self, port: str, baud: int = 115200):
        self._ctrl = D2ControllerDotNet()
        self._ctrl.OpenComms(port, baud)

    def dispose(self):
        self._ctrl.Dispose()

    def move_z_axis(self, pos):
        self._ctrl.ZAxis.MoveAbsolute(pos)
