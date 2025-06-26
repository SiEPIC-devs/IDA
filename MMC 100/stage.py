# uncompyle6 version 3.9.2
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: /home/pi/Desktop/new GUI/MMC 100/stage.py
# Compiled at: 2023-02-15 01:38:14
# Size of source mod 2**32: 18373 bytes
"""
Stage Control Module
"""
import pickle
import serial
import time
import MMC_100 as mmc100
import RPi.GPIO as GPIO
import sys

from motors_hal import MotorHAL

def print(string):
    term = sys.stdout
    term.write(str(string) + "\n")
    term.flush()


class StageHAL(MotorHAL):
    __doc__ = "\n    passing '?' as a parameter causes method to return some value if applicable\n\n    Inherited functions:\n    set_serial()\n    serial_write()\n    listing_port()\n    "
    X_AXIS = 1
    Y_AXIS = 2
    Z_AXIS = 3
    FR_AXIS = 4
    CR_AXIS = 5
    ALL_AXIS = 0

    def __init__(self):
        # For now, this is fine, we can configure the stage params as we go
        stage_parameters = [
         'stage_type', 
         'stage_inuse', 
         'step_size_x', 
         'step_size_y', 
         'step_size_z', 
         'step_size_fr', 
         'step_size_cr', 
         'crosshair_step_size', 
         'motor_velocity', 
         'motor_acceleration', 
         'Stage_COM_port', 
         'x_position', 
         'y_position', 
         'z_position', 
         'r_position', 
         'fr_position', 
         'fr_angle', 
         'fr_zero_position', 
         'fr_pivot_distance', 
         'real_x_position', 
         'real_y_position', 
         'real_z_position', 
         'timeout', 
         'baudrate', 
         'temp_initial_position', 
         'max_z', 
         'max_y', 
         'max_x', 
         'min_z', 
         'min_y', 
         'min_x', 
         'automated_move_happened']
        default_values = [
         "0"] * len(stage_parameters)
        try:
            import os, sys
            cwd = os.getcwd()
            main_path = os.path.split(cwd)
            main_path = main_path[0]
            self.dict = self.load_obj(os.path.join(main_path, "MMC 100", "stage"))
        except:
            self.dict = dict(zip(stage_parameters, default_values))
            self.save_obj(self.dict, "stage")

        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(11, GPIO.IN, GPIO.PUD_UP)
        GPIO.setup(13, GPIO.IN, GPIO.PUD_UP)
    
    def set_serial(self, serial_port, timeout=0.3, baudrate=38400, port='/dev/ttyUSB0'):
        """
        Serial configuration
        """
        self.serial_port = serial_port
        self.serial_port.timeout = timeout
        self.serial_port.baudrate = baudrate
        self.serial_port.port = port
        self.serial_port.open()

    def serial_write(self, message):
        """
        Writes to serial port
        """
        self.serial_port.write((message + " \n\r").encode("ascii"))

    def update_parameter(self, key, val):
        """
        Updates the corresponding value of a key in the dictionary
        """
        import os, sys
        cwd = os.getcwd()
        main_path = os.path.split(cwd)
        main_path = main_path[0]
        if key in self.dict:
            self.dict[key] = val
            self.save_obj(self.dict, os.path.join(main_path, "MMC 100", "stage"))
        else:
            print("%s does not exist" % key)

    def save_obj(self, obj, name):
        with open(name + ".pkl", "wb+") as f:
            pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)
            f.close()

    def load_obj(self, name):
        while True:
            try:
                with open(name + ".pkl", "rb") as f:
                    data = pickle.load(f)
                    break
            except EOFError:
                pass

        f.close()
        return data

    def reload_parameters(self):
        import os, sys
        cwd = os.getcwd()
        main_path = os.path.split(cwd)
        main_path = main_path[0]
        self.dict = self.load_obj(os.path.join(main_path, "MMC 100", "stage"))

    def open_port(self, **kwargs):
        """
        Initializes a Serial object and sets serial.

        **kwargs gives the option to initialize - timeout, baudrate, and COM port
        """
        self.serial_port = serial.Serial()
        self.set_serial((self.serial_port), port=(self.dict["Stage_COM_port"]))

    def read_pin(self, pin):
        return int(GPIO.input(pin))

    def wait_for_trigger(self, axis, timeout=-1):
        call_time = time.time()
        if axis == self.X_AXIS or axis == self.Y_AXIS:
            start = 0
            triggered = 0
            while 1:
                if time.time() - call_time > timeout:
                    break
                if self.read_pin(11) == 1 and triggered == 0:
                    start = time.time()
                elif self.read_pin(11) == 0:
                    triggered = 1
                elif triggered == 1:
                    pulse = time.time() - start
                    if pulse > 0.003:
                        return 0
                    triggered = 0

        return -1

    def stage_init(self):
        """
        initializes the stage parameters
        """
        # Grab motor vel from initialization
        self.set_velocity(self.X_AXIS, float(self.dict["motor_velocity"]))
        self.set_velocity(self.Y_AXIS, float(self.dict["motor_velocity"]))
        time.sleep(1)

        # Set to closed feedback loop
        self.loop_mode(self.X_AXIS, 3)
        self.loop_mode(self.Y_AXIS, 3)

        # Set vel 
        self.set_velocity(self.X_AXIS, "?") # "?" corresponds to setting 
        strip = lambda x : x.read_until("\n\r").decode("ascii").strip("#").strip("\n\r")
        print("Stage x velocity: {} um/s".format(strip(self.serial_port)))
        self.set_velocity(self.Y_AXIS, "?")
        print("Stage y velocity: {} um/s".format(strip(self.serial_port)))

        # For RPI
        self.set_trigger(self.X_AXIS, 1)
        self.set_trigger(self.Y_AXIS, 1)

    def stage_init_z(self):
        self.loop_mode(self.Z_AXIS, 3)

    def stage_init_fr(self):
        self.loop_mode(self.FR_AXIS, 3)

    def emergency_stop(self):
        """
        halts all axis
        """
        self.serial_write(mmc100.emergency_stop(self.ALL_AXIS))

    def move_x_axis(self, distance):
        """
        move stage (distance) um
        """
        self.serial_write(mmc100.move_rel(self.X_AXIS, distance * 0.001))
        self.update_parameter("automated_move_happened", str(1))

    def move_y_axis(self, distance):
        """
        move stage (distance) um
        """
        self.serial_write(mmc100.move_rel(self.Y_AXIS, distance * 0.001))
        self.update_parameter("automated_move_happened", str(1))

    def move_z_axis(self, distance):
        """
        move stage (distance) um
        """
        self.serial_write(mmc100.move_rel(self.Z_AXIS, distance * 0.001))
        self.update_parameter("automated_move_happened", str(1))

    def move_fr_axis(self, distance):
        """
        rotate fiber array mm
        """
        self.serial_write(mmc100.move_rel(self.FR_AXIS, distance))

    def move_cr_axis(self, distance):
        """
        rotate chip
        """
        self.serial_write(mmc100.move_rel(self.CR_AXIS, distance))

    def set_zero_point(self, axis_number):
        """
        axis_number is one of the defined class variable 
        """
        self.serial_write(mmc100.zero_position(axis_number))

    def set_velocity(self, axis_number, velocity):
        """
        sets the velocity of a particular stage

        velocity in mm/s [degrees/s]
        """
        self.serial_write(mmc100.velocity(axis_number, velocity))

    def set_acceleration(self, axis_number, acceleration):
        """
        sets the acceleration of a particular stage

        acceleration in mm/s2
        """
        self.serial_write(mmc100.acceleration(axis_number, acceleration))

    def stop_motion(self, axis_number):
        """
        stop the motion of some axis
        """
        self.serial_write(mmc100.stop_motion(axis_number))

    def axis_read_position(self, axis_number):
        """
        read the position information from an axis
    
        returns the position values in mm for the specified axis in the following format:
        [Theoretical position in mm, Encoder position in mm]
        [Theoretical position in degrees, Encoder position in degrees]

        Note: Setting the axis to 0 will cause an error
        """
        read = mmc100.position(axis_number)
        self.serial_write(read)
        time.sleep(0.1)
        pos = self.serial_port.read_until("\n\r".encode("ascii")).decode("ascii")
        time.sleep(0.1)
        pos = pos.strip("#").strip("\n\r")
        pos = pos.split(",")
        pos = float(pos[0]) * 1000
        time.sleep(0.1)
        return pos

    def read_position(self):
        """
        used to read the position information from all axis

        we do not use ALL_AXIS since the function to read all is not defined
    
        returns the position values in mm for the specified axis in the following format:
        [Theoretical position in mm, Encoder position in mm]
        [Theoretical position in degrees, Encoder position in degrees]

        Note: Setting the axis to 0 will cause an error
        """
        # Read x,y,z axis
        readX = mmc100.position(self.X_AXIS)
        readY = mmc100.position(self.Y_AXIS)
        readZ = mmc100.position(self.Z_AXIS)
        self.serial_write(readX)
        time.sleep(0.1)

        # Read port x axis
        xpos = self.serial_port.read_until("\n\r".encode("ascii")).decode("ascii")
        time.sleep(0.1)
        xpos = xpos.strip("#").strip("\n\r")
        xpos = xpos.split(",")
        xpos = float(xpos[0]) * 1000
        time.sleep(0.1)

        # Read port y axis
        self.serial_write(readY)
        ypos = self.serial_port.read_until("\n\r".encode("ascii")).decode("ascii")
        time.sleep(0.1)
        ypos = ypos.strip("#").strip("\n\r")
        ypos = ypos.split(",")
        ypos = float(ypos[0]) * 1000
        time.sleep(0.1)
        
        # Read port z
        self.serial_write(readZ)
        zpos = self.serial_port.read_until("\n\r".encode("ascii")).decode("ascii")
        time.sleep(0.1)
        zpos = zpos.strip("#").strip("\n\r")
        zpos = zpos.split(",")
        zpos = float(zpos[0]) * 1000
        
        return [xpos, ypos, zpos]

    def read_fiber_position(self):
        # Read fr axis
        readangle = mmc100.position(self.FR_AXIS)
        self.serial_write(readangle)
        time.sleep(0.1)
        distance = self.serial_port.read_until("\n\r".encode("ascii")).decode("ascii")
        time.sleep(0.1)
        distance = distance.strip("#").strip("\n\r")
        distance = distance.split(",")
        distance = float(distance[0]) * 1000
        time.sleep(0.1)
        return distance

    def motor_toggle(self, axis_number, state):
        """
        toggles current flow to a motor

        state in [0, 1] where 0 is OFF and 1 is ON
        """
        self.serial_write(mmc100.toggle_motor_on_off(axis_number, state))

    def loop_mode(self, axis_number, state):
        """
        sets the feedback mode of some controller

        state in (0, 1, 2, 3) or ? - Read mode
        0 – Open Loop [default]
        1 – Clean Open Loop
        2 – Clean Open Loop Movement, Closed Loop deceleration
        3 – Closed Loop
        """
        self.serial_write(mmc100.set_loop_mode(axis_number, state))

    def status(self, axis_number):
        """
        
        bit0:
        bit1:
        bit2:
        bit3: 1 - stage has stopped
              0 - stage is moving
        bit4:
        bit5:
        bit6:
        bit7:
        """
        self.serial_write(mmc100.status(axis_number))
        try:
            integer = self.serial_port.read_until("\n\r").decode("ascii")
            integer = integer.strip("#").strip("\n\r")
        except Exception:
            print("STATUS ERROR")
            self.serial_write("CER")
            return self.status(axis_number=axis_number)
        else:
            if integer != "":
                try:
                    return bin(int(integer, base=10))[2[:None]][4]
                except:
                    print("STATUS ERROR")
                    self.serial_write("CER")
                    return self.status(axis_number=axis_number)

            else:
                return self.status(axis_number=axis_number)

    def read_deadband(self, axis_number):
        self.serial_write(mmc100.read_closed_loop_deadband(axis_number))
        return self.serial_port.read_until("\n\r").decode("ascii")

    def closed_loop_deadband(self, axis_number, counts, timeout):
        self.serial_write(mmc100.closed_loop_deadband(axis_number, counts, timeout))

    def read_encoder_velocity(self, axis_number):
        self.serial_write(mmc100.encoder_velocity(axis_number))
        return self.serial_port.read_until("\n\r").decode("ascii")

    def set_trigger(self, axis, pin):
        serial_command = str(axis) + "IOF" + "?"
        self.serial_write(serial_command)
        print(self.serial_port.read_until("\n\r").decode("ascii"))
        self.serial_write(mmc100.set_pin(axis, pin, 0))
        time.sleep(1)
        print(self.get_errors(axis))
        self.serial_write(mmc100.set_hardware_trigger(axis, pin, 3))
        time.sleep(1)
        print(self.get_errors(axis))

    def set_encoder_polarity(self, normal_reverse):
        self.serial_write(mmc100.set_encoder(self.ALL_AXIS, normal_reverse))

    def get_errors(self, axis):
        self.serial_write(mmc100.get_errors(axis))
        return self.serial_port.read_until("\n\r").decode("ascii")

    def move_and_velocity_z(self, distance):
        self.serial_write(mmc100.move_rel(self.Z_AXIS, distance * 0.001) + ";" + mmc100.encoder_velocity(self.Z_AXIS))
        return self.serial_port.read_until("\n\r").decode("ascii")

    def trace(self, axis, samples, frequency, position):
        self.serial_write(mmc100.perform_trace(axis, samples, frequency, position))

    def dump_trace(self, axis):
        self.serial_write(mmc100.dump_trace_data(axis))
        raw = self.serial_port.read_until("\n\r").decode("ascii")
        while True:
            inputdata = self.serial_port.read_until("\n\r").decode("ascii")
            if inputdata == "":
                break
            raw += inputdata

        splitdata = raw.split()
        count = 0
        theoretical = []
        actual = []
        dac = []
        notused = []
        for i in splitdata:
            if "#" in i:
                count = 0
                continue
            count += 1
            if count == 1:
                theoretical.append(float(int(i)) * 5e-10 * 1000)
            elif count == 2:
                actual.append(float(int(i)) * 5e-10 * 1000)
            elif count == 3:
                dac.append(int(i))
            elif count == 4:
                notused.append(int(i))

        return [
         theoretical, actual, dac, notused]

    def home_axis(self, axis, direction):
        if direction == 0:
            self.serial_write(mmc100.to_neg_limit(axis))
        else:
            self.serial_write(mmc100.to_pos_limit(axis))
        time.sleep(1)
        status = self.status(axis)
        while status == "0":
            status = self.status(axis)

        self.set_zero_point(axis)

    def go_to_limit(self, axis, direction):
        if direction == 0:
            self.serial_write(mmc100.to_neg_limit(axis))
        else:
            self.serial_write(mmc100.to_pos_limit(axis))
        time.sleep(1)
        status = self.status(axis)
        while status == "0":
            status = self.status(axis)

    def move_abs(self, axis, distance):
        self.serial_write(mmc100.move_abs(axis, distance))

    def read_availible_programs(self, axis):
        self.serial_write(mmc100.read_availible_programs(axis))
        return self.serial_port.read_until("\n\r").decode("ascii")

    def erase_program(self, axis, program_number):
        self.serial_write(mmc100.erase_program(axis, program_number))

    def program_recording(self, axis, program_number, list_of_commands):
        self.serial_write(mmc100.program_recording_start(axis, program_number))
        time.sleep(0.1)
        for command in list_of_commands:
            self.serial_write(command)
            time.sleep(0.1)

        self.serial_write(mmc100.program_recording_end(axis))
        time.sleep(0.1)

    def program_linear_move(self, axis, program_number, steps, step_size):
        commands = []
        commands.append(mmc100.wait_for_time_period(axis, 100))
        for i in range(0, steps):
            commands.append(mmc100.move_rel(axis, step_size * 0.001))
            commands.append(mmc100.wait_for_stop(axis))
            commands.append(mmc100.wait_for_time_period(axis, 1))

        self.program_recording(axis, program_number, commands)

    def program_linear_move_delay(self, axis, program_number, steps, step_size, delay):
        commands = []
        if delay <= 0:
            delay = 1
        commands.append(mmc100.wait_for_time_period(axis, delay))
        for i in range(0, steps):
            commands.append(mmc100.move_rel(axis, step_size * 0.001))
            commands.append(mmc100.wait_for_stop(axis))
            commands.append(mmc100.wait_for_time_period(axis, delay))

        self.program_recording(axis, program_number, commands)

    def program_recording_end(self, axis):
        self.serial_write(mmc100.program_recording_end(axis))

    def run_program(self, axis, program):
        self.serial_write(mmc100.run_program(axis, program))

    def read(self):
        self.serial_port.read_until("\n\r").decode("ascii")
