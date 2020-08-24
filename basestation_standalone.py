import sys
from PyQt5 import QtGui
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import QApplication, QWidget, QSpinBox
import pyqtgraph as pg
import time as time
import pprint
import random
import numpy as np
import os
import serial
# from xbee import XBee
import re
import pprint

past_points = []
max_points = 20
orig_lat = None
orig_long = None
buoys = []
waypoints = []

pg.setConfigOption('background', 'w')
pp = pprint.PrettyPrinter(indent=4)

## Always start by initializing Qt (only once per application)
app = QtGui.QApplication(sys.argv)

## Define a top-level widget to hold everything
w = QtGui.QWidget()

serial_port = serial.Serial('/dev/cu.usbmodem14201', 9600,
                            timeout=0.25)  #Courtney - /dev/cu.usbmodem14201
# xbee = XBee(serial_port)

header = "----------NAVIGATION----------"
end = "----------END----------"
waypt_header = "----------WAYPOINTS----------"
hit_header = "----------HIT----------"
# regex = "(?:'rf_data': b')((.|\n)*)'"
regex = "(b')((.|\n)*)'"
curPacket = ""

## Create some widgets to be placed inside
# btn = QtGui.QPushButton('Waypoint')
# btn2 = QtGui.QPushButton('Update')
btn3 = QtGui.QPushButton('Reload Buoys')
# text = QtGui.QLineEdit('Enter Buoy/Waypoint')
listw = QtGui.QListWidget()
labelw = QtGui.QLabel('Next Waypoints')
plot = pg.PlotWidget()
plot.showGrid(True, True, 0.3)
plot.hideButtons()
# plot.setLimits(minXRange=150, maxXRange=150, minYRange=150, maxYRange=150)
display0 = QtGui.QLabel('Sail, Tail: <x,y>')
display1 = QtGui.QLabel('Wind Direction: --')
display2 = QtGui.QLabel('Roll, Pitch, Yaw: <x,y,z>')
display3 = QtGui.QLabel('Heading: --')
hit_label = QtGui.QLabel("No waypoints hit yet.")


class CompassWidget(QWidget):
    angleChanged = pyqtSignal(float)

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        self._angle = 0.0
        self._margins = 10
        self._pointText = {
            0: "N",
            45: "NE",
            90: "E",
            135: "SE",
            180: "S",
            225: "SW",
            270: "W",
            315: "NW"
        }

    def paintEvent(self, event):
        painter = QPainter()
        painter.begin(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.fillRect(event.rect(), self.palette().brush(QPalette.Window))
        self.drawMarkings(painter)
        self.drawNeedle(painter)

        painter.end()

    def drawMarkings(self, painter):
        painter.save()
        painter.translate(self.width() / 2, self.height() / 2)
        scale = min((self.width() - self._margins) / 120.0,
                    (self.height() - self._margins) / 120.0)
        painter.scale(scale, scale)

        font = QFont(self.font())
        font.setPixelSize(10)
        metrics = QFontMetricsF(font)

        painter.setFont(font)
        painter.setPen(self.palette().color(QPalette.Shadow))

        i = 0
        while i < 360:
            if i % 45 == 0:
                painter.drawLine(0, -40, 0, -50)
                painter.drawText(-metrics.width(self._pointText[i]) / 2.0, -52,
                                 self._pointText[i])
            else:
                painter.drawLine(0, -45, 0, -50)

            painter.rotate(15)
            i += 15

        painter.restore()

    def drawNeedle(self, painter):
        painter.save()
        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(self._angle)
        scale = min((self.width() - self._margins) / 120.0,
                    (self.height() - self._margins) / 120.0)
        painter.scale(scale, scale)

        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(self.palette().brush(QPalette.Shadow))

        painter.drawPolygon(
            QPolygon([
                QPoint(-10, 0),
                QPoint(0, -45),
                QPoint(10, 0),
                QPoint(0, 45),
                QPoint(-10, 0)
            ]))

        painter.setBrush(self.palette().brush(QPalette.Highlight))

        painter.drawPolygon(
            QPolygon([
                QPoint(-5, -25),
                QPoint(0, -45),
                QPoint(5, -25),
                QPoint(0, -30),
                QPoint(-5, -25)
            ]))

        painter.restore()

    def sizeHint(self):
        return QSize(300, 300)

    def angle(self):
        return self._angle

    # @pyqtSlot(float)
    def setAngle(self, angle):
        if angle != self._angle:
            self._angle = angle
            self.angleChanged.emit(angle)
            self.update()

    angle = pyqtProperty(float, angle, setAngle)


def update(data):
    try:
        global past_points, max_points, orig_lat, orig_long
        x = float(data['X position'])
        y = float(data['Y position'])

        if orig_lat is None or orig_long is None:
            orig_lat = float(data['Origin Latitude'])
            orig_long = float(data['Origin Longitude'])
            reloadBuoys()

        past_points.append((x, y))
        if len(past_points) > max_points:
            past_points.pop(0)

        pen = pg.mkPen((49, 69, 122))
        plot.plot([p[0] for p in past_points], [p[1] for p in past_points],
                  clear=True,
                  pen=pen)
        redrawBuoys()
        redrawWaypoints()
        w.update()
        w.show()
        wind_dir = round(float(data["Wind Direction"]))
        roll = round(float(data["Roll"]))
        pitch = round(float(data["Pitch"]))
        yaw = round(float(data["Yaw"]))
        sail = round(float(data["Sail Angle"]))
        tail = round(float(data["Tail Angle"]))
        heading = round(float(data["Heading"]))
        display0.setText("Sail, Tail: <" + str(sail) + "," + str(tail) + ">")
        display1.setText("Wind Angle: " + str(wind_dir))
        display2.setText("Roll, Pitch, Yaw: <" + str(roll) + "," + str(pitch) +
                         "," + str(yaw) + ">")
        display3.setText("Heading: " + str(heading))
        # subtract 90 here to get wrt N instead of the x-axis
        sail_compass.setAngle(-(float(data["Sail Angle"]) - 90.0))
        wind_compass.setAngle(-(float(data["Wind Direction"]) - 90.0))
        boat_compass.setAngle(-(float(data["Yaw"]) - 90.0))
        angle_compass.setAngle(-(float(data["Heading"]) - 90.0))
    except:
        print("Corrupt Data Dump")


def correctData(dataIn):
    wanted_keys = ["X position", "Y position"]
    for key in wanted_keys:
        if key not in dataIn:
            return False
    return True


def run():
    try:
        packet = str(serial_port.readline())
        match = re.search(regex, packet)
        if match:
            packet = packet.replace("b'", "")
            packet = packet.replace("'", "")
            packet = packet.replace("\\n", "")
            packet = packet.replace("\n", "")

            split_line = packet.split(",")
            if header in split_line and end in split_line:
                data_line = filter(lambda l: l not in [header, end],
                                   split_line)

                data = {}
                for d in data_line:
                    if ":" in d and d.count(":") == 1:
                        label, value = d.split(":")
                        data[label] = value

                update(data)

            elif waypt_header in split_line and end in split_line:
                data_line = filter(lambda l: l not in [waypt_header, end],
                                   split_line)

                global waypoints
                waypoints = []
                for d in data_line:
                    if d.count(" ") == 1 and d.count(":") == 2:
                        xval, yval = d.split(" ")
                        _, x = xval.split(":")
                        _, y = yval.split(":")
                        waypoints.append((float(x), float(y)))
                        redrawWaypoints()

            elif hit_header in split_line and end in split_line:
                data_line = filter(lambda l: l not in [waypt_header, end],
                                   split_line)

                for d in data_line:
                    if d.count(" ") == 1 and d.count(":") == 2:
                        xval, yval = d.split(" ")
                        _, x = xval.split(":")
                        _, y = yval.split(":")

                        hit_label.setText("Hit ({:.2f}, {:.2f})".format(
                            float(x), float(y)))
        else:
            print("Regex failed to match")
    except KeyboardInterrupt:
        exit(0)


brush_list = [pg.mkColor(c) for c in "rgbcmykwrg"]


def reloadBuoys():
    global buoys

    if orig_lat is None or orig_long is None:
        print("Origin is not yet defined.")
        return

    try:
        with open('./gui_input/buoy.csv', 'r') as file:
            lines = file.readlines()

        buoys = []
        for line in lines:
            split_line = line.split(",")
            if len(split_line) == 2:
                x, y = latLongToXY(float(split_line[0]), float(split_line[1]))
                buoys.append((x, y))
    except:
        print("Could not read buoys from file.")


def redrawBuoys():
    global buoys
    pen = pg.mkPen((235, 119, 52))
    brush = pg.mkBrush((235, 119, 52))

    for buoy in buoys:
        plot.plot([buoy[0]], [buoy[1]],
                  symbolPen=pen,
                  symbolBrush=brush,
                  symbol="o")


def redrawWaypoints():
    global waypoints

    if len(waypoints) < 1:
        return

    listw.clear()

    # avoid div by zero
    if len(waypoints) == 1:
        listw.addItem("({:.2f}, {:.2f})".format(waypoints[0][0],
                                                waypoints[0][1]))
        pen = pg.mkPen('r')
        brush = pg.mkBrush('r')
        plot.plot([waypoints[0][0]], [waypoints[0][1]],
                  symbolPen=pen,
                  symbolBrush=brush,
                  symbol="+")
        return

    start_color = (255, 0, 0)
    end_color = (0, 70, 255)
    slope = [(end_color[i] - start_color[i]) / (len(waypoints) - 1)
             for i in range(len(start_color))]

    for i in range(len(waypoints)):
        listw.addItem("({:.2f}, {:.2f})".format(waypoints[i][0],
                                                waypoints[i][1]))
        color = [
            slope[j] * i + start_color[j] for j in range(len(start_color))
        ]

        pen = pg.mkPen(color)
        brush = pg.mkBrush(color)
        plot.plot([waypoints[i][0]], [waypoints[i][1]],
                  symbolPen=pen,
                  symbolBrush=brush,
                  symbol="+")


def latLongToXY(lat, long):
    if orig_lat is None or orig_long is None:
        return

    shifted_long = long - orig_long
    shifted_lat = lat - orig_lat
    deg_to_rad = np.pi / 180.0

    x = 6371000.0 * np.cos(orig_lat * deg_to_rad) * deg_to_rad * shifted_long
    y = 6371000.0 * deg_to_rad * shifted_lat

    return x, y


wind_compass = CompassWidget()
boat_compass = CompassWidget()
sail_compass = CompassWidget()
angle_compass = CompassWidget()

# btn.clicked.connect(waypoint)
#btn2.clicked.connect(update)
btn3.clicked.connect(reloadBuoys)
## Create a grid layout to manage the widgets size and position
layout = QtGui.QGridLayout()
w.setLayout(layout)

## Add widgets to the layout in their proper positions
## goes row, col, rowspan, colspan

layout.addWidget(hit_label, 0, 0)
layout.addWidget(btn3, 1, 0)  # button3 goes in upper-left is buoy
layout.addWidget(labelw, 2, 0)
layout.addWidget(listw, 3, 0)  # list widget goes in bottom-left
layout.addWidget(display0, 6, 0)
layout.addWidget(display1, 6, 1)  # display1 widget goes in bottom-left
layout.addWidget(display2, 6, 2)  # display2 widget goes in bottom-middle
layout.addWidget(display3, 6, 3)
layout.addWidget(plot, 0, 1, 5, 3)  # plot goes on right side, spanning 3 rows
layout.addWidget(sail_compass, 5, 0, 1, 1)
layout.addWidget(wind_compass, 5, 1, 1, 1)
layout.addWidget(boat_compass, 5, 2, 1, 1)
layout.addWidget(angle_compass, 5, 3, 1, 1)

# makes exit a little cleaner
exit_action = QtGui.QAction("Exit", app)
exit_action.setShortcut("Ctrl+Q")
exit_action.triggered.connect(lambda: exit(0))

## Display the widget as a new window
w.setWindowTitle("CUSail Basestation")
w.show()

w.timer = QTimer()
w.timer.setInterval(1000)  # once a second should be good enough
w.timer.timeout.connect(run)
w.timer.start()

## Start the Qt event loop
app.exec_()
