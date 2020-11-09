# -*- coding: utf-8 -*-
"""
Created on Sun Oct 25 11:37:17 2020

@author: Srikar Yallala
"""

from PyQt5 import QtWidgets, uic
import sys  # We need sys so that we can pass argv to QApplication
import os


class MainWindow(QtWidgets.QMainWindow):
  def __init__(self, *args, **kwargs):
    super(MainWindow, self).__init__(*args, **kwargs)

    # Load the UI Page
    uic.loadUi('v1.ui', self)

    self.sail.display(151)
    self.tail.display(31)
    self.angle.display(61)
    self.wind_direction.display(136)
    self.wind_speed.display(11)
    self.yaw.display(101)
    self.roll.display(10)
    self.pitch.display(5)
    self.waypoint_x.display(12)
    self.waypoint_y.display(16)
    self.d_o_m.display(13.5)

    # Dials are weird, 0 means straight down, 90 means left, 270 means right, etc.
    self.wind_dial.setValue(180)
    self.d_o_m_dial.setValue(270)


def main():
    app = QtWidgets.QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
