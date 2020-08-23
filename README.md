# GUI

Dependencies (install with pip3): PyQt5, pyqtgraph, numpy, serial, xbee (and a few more but those should be pre-installed)

There are two versions of the GUI. The __standalone__ version mocks the latitude and longitude data (it just loops around the engineering quad). To run this version, you must upload *GUI_Standalone_Test/GUI_Standalone_Test.ino* to an Arduino and have it plugged in to your computer. In *basestation_standalone.py*, change the name of the serial port to be the one that your Arduino is plugged in to (serial_port = serial.Serial('your port here', 9600)). Now, you can run *python3 basestation_standalone.py*.

To run the *full* test suite, program an Arduino with *GUI_Test_Suite/GUI_Test_Suite.ino*. This version requires that GPS and Xbee modules are attached to the Arduino. Change the name of the serial port in *basestation.py* to be the name of the port that the Xbee module connected to your computer is plugged in to. Now, you can run *python3 basestation.py*.