# uncompyle6 version 3.9.2
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: /home/pi/Desktop/new GUI/MMC_100/serial_communication.py
# Compiled at: 2021-03-21 22:56:48
# Size of source mod 2**32: 715 bytes
import serial, sys

def print(string):
    term = sys.stdout
    term.write(str(string) + "\n")
    term.flush()


class mmc100_communicator:

    def __init__(self):
        pass

    def set_serial(self, serial_port, timeout=0.3, baudrate=38400, port='/dev/ttyUSB0'):
        self.serial_port = serial_port
        self.serial_port.timeout = timeout
        self.serial_port.baudrate = baudrate
        self.serial_port.port = port
        self.serial_port.open()

    def serial_write(self, message):
        self.serial_port.write((message + " \n\r").encode("ascii"))
