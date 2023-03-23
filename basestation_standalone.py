import sys
from PyQt5 import QtGui
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import QApplication, QWidget, QSpinBox
import pyqtgraph as pg
import time
import numpy as np
import serial
# from xbee import XBee
import re
import pprint

# manual control mode indicator
manual_mode = False

# log output to a csv file
LOG_FLAG = True
log_name = './gui_output/log-' + time.asctime(time.gmtime()).replace(
    '  ', '-').replace(' ', '-') + '.csv'

# points to display
past_points = []
max_points = 20
buoys = []
waypoints = []
orig_lat = None
orig_long = None

pg.setConfigOption('background', 'w')

## Always start by initializing Qt (only once per application)
app = QtGui.QApplication(sys.argv)

## Define a top-level widget to hold everything
w = QtGui.QWidget()

# serial port to read from (different for everyone)
serial_port = serial.Serial('/dev/cu.usbmodem14201', 9600,
                            timeout=0.25)  #Courtney - /dev/cu.usbmodem14201
# xbee = XBee(serial_port)

header = "----------NAVIGATION----------"
end = "----------END----------"
waypt_header = "----------WAYPOINTS----------"
hit_header = "----------HIT----------"
regex = "(b')((.|\n)*)'"
curPacket = ""

## Create some widgets to be placed inside
kill_button = QtGui.QPushButton('Kill Algorithm')
manual_button = QtGui.QPushButton('Manual Override')
send_button = QtGui.QPushButton('Send Angles')
main_angle_input = QtGui.QSpinBox(maximum=500, minimum=-500)
tail_angle_input = QtGui.QSpinBox(maximum=500, minimum=-500)
main_label = QtGui.QLabel('Sail Angle:')
tail_label = QtGui.QLabel('Tail Angle:')

main_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
tail_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

main_angle_input.setDisabled(True)
tail_angle_input.setDisabled(True)
send_button.setDisabled(True)

btn3 = QtGui.QPushButton('Reload Buoys')
listw = QtGui.QListWidget()
labelw = QtGui.QLabel('Next Waypoints')
plot = pg.PlotWidget()
plot.showGrid(True, True, 0.3)
plot.hideButtons()
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


# update the display
def update(data):
    try:
        global past_points, max_points, orig_lat, orig_long
        x = float(data['X position'])
        y = float(data['Y position'])

        # set the origin and draw buoys if it hasn't already been done
        if orig_lat is None or orig_long is None:
            orig_lat = float(data['Origin Latitude'])
            orig_long = float(data['Origin Longitude'])
            reloadBuoys()

        # only display the last 'max_points' number of points
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

        # extract all of the data
        wind_dir = round(float(data["Wind Direction"]))
        roll = round(float(data["Roll"]))
        pitch = round(float(data["Pitch"]))
        yaw = round(float(data["Yaw"]))
        sail = round(float(data["Sail Angle"]))
        tail = round(float(data["Tail Angle"]))
        heading = round(float(data["Heading"]))

        # log to a file
        if LOG_FLAG:
            with open(log_name, 'a') as log_file:
                print("{},Boat Position,{},{}".format(
                    time.asctime(time.gmtime()), x, y),
                      file=log_file)
                print("{},Wind Direction,{}".format(
                    time.asctime(time.gmtime()), wind_dir),
                      file=log_file)
                print("{},Roll,{}".format(time.asctime(time.gmtime()), roll),
                      file=log_file)
                print("{},Pitch,{}".format(time.asctime(time.gmtime()), pitch),
                      file=log_file)
                print("{},Yaw,{}".format(time.asctime(time.gmtime()), yaw),
                      file=log_file)
                print("{},Sail Angle,{}".format(time.asctime(time.gmtime()),
                                                sail),
                      file=log_file)
                print("{},Tail Angle,{}".format(time.asctime(time.gmtime()),
                                                tail),
                      file=log_file)
                print("{},Heading Angle,{}".format(time.asctime(time.gmtime()),
                                                   heading),
                      file=log_file)

        # set the labels
        display0.setText("Sail, Tail: <" + str(sail) + "," + str(tail) + ">")
        display1.setText("Wind Angle: " + str(wind_dir))
        display2.setText("Roll, Pitch, Yaw: <" + str(roll) + "," + str(pitch) +
                         "," + str(yaw) + ">")
        display3.setText("Heading: " + str(heading))

        # set the compass angles
        # subtract 90 here to get wrt N instead of the x-axis
        sail_compass.setAngle(-(float(data["Sail Angle"]) - 90.0))
        wind_compass.setAngle(-(float(data["Wind Direction"]) - 90.0))
        boat_compass.setAngle(-(float(data["Yaw"]) - 90.0))
        angle_compass.setAngle(-(float(data["Heading"]) - 90.0))
    except:
        print("Corrupt Data Dump")


# make sure that all necessary keys are there
def correctData(dataIn):
    wanted_keys = [
        "X position", "Y position", "Wind Direction", "Roll", "Pitch", "Yaw",
        "Sail Angle", "Tail Angle", "Heading"
    ]
    for key in wanted_keys:
        if key not in dataIn:
            return False
    return True


# try to read input and update display
def run():
    try:
        # read a line and make sure it's the correct format
        packet = str(serial_port.readline())
        match = re.search(regex, packet)
        if match:
            # remove line annotations
            packet = packet.replace("b'", "")
            packet = packet.replace("'", "")
            packet = packet.replace("\\n", "")
            packet = packet.replace("\n", "")

            split_line = packet.split(",")

            # read sensor information and current position
            if header in split_line and end in split_line:
                data_line = filter(lambda l: l not in [header, end],
                                   split_line)

                data = {}
                for d in data_line:
                    if ":" in d and d.count(":") == 1:
                        label, value = d.split(":")
                        data[label] = value

                update(data)

            # read all waypoints
            elif waypt_header in split_line and end in split_line:
                data_line = filter(lambda l: l not in [waypt_header, end],
                                   split_line)

                global waypoints
                waypoints = []

                logged_pt = False
                for d in data_line:
                    if d.count(" ") == 1 and d.count(":") == 2:
                        xval, yval = d.split(" ")
                        _, x = xval.split(":")
                        _, y = yval.split(":")
                        waypoints.append((float(x), float(y)))

                        if LOG_FLAG and not logged_pt:
                            with open(log_name, 'a') as log_file:
                                print("{},Current Waypoint,{},{}".format(
                                    time.asctime(time.gmtime()), x, y),
                                      file=log_file)
                                logged_pt = True

                redrawWaypoints()

            # read hit waypoint message
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

                        if LOG_FLAG:
                            with open(log_name, 'a') as log_file:
                                print("{},Hit Waypoint,{},{}".format(
                                    time.asctime(time.gmtime()), x, y),
                                      file=log_file)
        else:
            print("Regex failed to match")
    except KeyboardInterrupt:
        exit(0)


brush_list = [pg.mkColor(c) for c in "rgbcmykwrg"]


# reload buoys from file
def reloadBuoys():
    global buoys

    if orig_lat is None or orig_long is None:
        print("Origin is not yet defined.")
        return

    try:
        with open('./gui_input/buoy.csv', 'r') as in_file:
            lines = in_file.readlines()

        with open('./gui_output/buoy_xy.csv', 'w') as out_file:
            buoys = []
            for line in lines:
                split_line = line.split(",")
                if len(split_line) == 2:
                    x, y = latLongToXY(float(split_line[0]),
                                       float(split_line[1]))
                    buoys.append((x, y))
                    print("{},{}".format(x, y), file=out_file)
    except:
        print("Could not read buoys from file.")


# redraw buoys on the plot
def redrawBuoys():
    global buoys
    pen = pg.mkPen((235, 119, 52))
    brush = pg.mkBrush((235, 119, 52))

    for buoy in buoys:
        plot.plot([buoy[0]], [buoy[1]],
                  symbolPen=pen,
                  symbolBrush=brush,
                  symbol="o")


# redraw all waypoints
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

    # linear interpolation of color (red is the next waypoint, blue is last)
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


# convert a (latitude, longitude) position to (x, y)
def latLongToXY(lat, long):
    if orig_lat is None or orig_long is None:
        return

    shifted_long = long - orig_long
    shifted_lat = lat - orig_lat
    deg_to_rad = np.pi / 180.0

    x = 6371000.0 * np.cos(orig_lat * deg_to_rad) * deg_to_rad * shifted_long
    y = 6371000.0 * deg_to_rad * shifted_lat

    return x, y


# send the quit signal back to the boat
def killswitch():
    print("Sending quit command...")
    serial_port.write(0x03)
    serial_port.flush()


def manual_control():
    global manual_mode

    if manual_mode:
        # disengage manual control
        serial_port.write('a\n'.encode('utf-8'))
        serial_port.flush()

        manual_mode = False
        manual_button.setText("Manual Override")
        main_angle_input.setDisabled(True)
        tail_angle_input.setDisabled(True)
        send_button.setDisabled(True)
    else:
        serial_port.write('o\n'.encode('utf-8'))
        serial_port.flush()

        manual_mode = True
        manual_button.setText("Engage Autopilot")
        main_angle_input.setDisabled(False)
        tail_angle_input.setDisabled(False)
        send_button.setDisabled(False)


def send_angles():
    main_angle = main_angle_input.value()
    tail_angle = tail_angle_input.value()
    print("Sending anlges: {} {}".format(main_angle, tail_angle))
    serial_port.write("{} {}\n".format(main_angle, tail_angle).encode('utf-8'))
    serial_port.flush()


# compass widgets
wind_compass = CompassWidget()
boat_compass = CompassWidget()
sail_compass = CompassWidget()
angle_compass = CompassWidget()

# link reload buoys button to function
btn3.clicked.connect(reloadBuoys)

# link killswitch to function to send quit command
kill_button.clicked.connect(killswitch)

# manual control
manual_button.clicked.connect(manual_control)
send_button.clicked.connect(send_angles)

## Create a grid layout to manage the widgets size and position
layout = QtGui.QGridLayout()
w.setLayout(layout)

## Add widgets to the layout in their proper positions
## goes row, col, rowspan, colspan
layout.addWidget(kill_button, 0, 0)
layout.addWidget(hit_label, 1, 0)
layout.addWidget(btn3, 2, 0)
layout.addWidget(labelw, 3, 0)
layout.addWidget(listw, 4, 0)
layout.addWidget(display0, 6, 0)
layout.addWidget(display1, 6, 1)
layout.addWidget(display2, 6, 2)
layout.addWidget(display3, 6, 3)
layout.addWidget(plot, 0, 1, 5, 3)
layout.addWidget(sail_compass, 5, 0, 1, 1)
layout.addWidget(wind_compass, 5, 1, 1, 1)
layout.addWidget(boat_compass, 5, 2, 1, 1)
layout.addWidget(angle_compass, 5, 3, 1, 1)

manual_widget = QWidget()
hlayout = QtGui.QHBoxLayout()
manual_widget.setLayout(hlayout)

hlayout.addWidget(manual_button)
hlayout.addWidget(main_label)
hlayout.addWidget(main_angle_input)
hlayout.addWidget(tail_label)
hlayout.addWidget(tail_angle_input)
hlayout.addWidget(send_button)

layout.addWidget(manual_widget, 7, 0, 1, 4)

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
