# GUI

Dependencies (install with pip3): PyQt5, pyqtgraph, numpy, serial, xbee (and a few more but those should be pre-installed)

There are two versions of the GUI. The __standalone__ version mocks the sensor and waypoint data (everything is randomized). To run this version, you must upload *GUI_Standalone_Test/GUI_Standalone_Test.ino* to an Arduino and have it plugged in to your computer. In *basestation_standalone.py*, change the name of the serial port to be the one that your Arduino is plugged in to (serial_port = serial.Serial('your port here', 9600)). Now, you can run *python3 basestation_standalone.py*.

To run the *full* basestation code, setup the Raspberry Pi testbench with all of the sensors and the Xbee module. Plug another Xbee module into your computer and change the name of the serial port in *basestation.py* if necessary. Now, you can run *python3 basestation.py*.