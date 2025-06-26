# uncompyle6 version 3.9.2
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: /home/pi/Desktop/new GUI/MMC_100/MMC_100.py
# Compiled at: 2021-03-26 01:16:28
# Size of source mod 2**32: 20135 bytes
"""
Communication with the MMC-100 Controller

19-06-06 Created this module
19-06-06 No longer using a class for the motor

19-06-07 Added encode('utf-8') to encode string command to bytes
19-06-07 Saw the note, does that mean I need to concatonate 
 or 
 characters to the serial command?
19-06-07 let the functions return value instead of just printing?
"""
import sys

def print(string):
    term = sys.stdout
    term.write(str(string) + "\n")
    term.flush()


import serial_communication as sc

class Error(Exception):
    __doc__ = "\n    Base class for exceptions in this module.\n    "


class rangeError(Error):
    pass


class parameterError(Error):
    pass


def status(n):
    """
    Checks the status register for a specific axis
    """
    if n >= 1:
        if n <= 99:
            return str(n) + "STA?"
    raise rangeError("Axis number (0-99) or maximum acceleration (0.001-500) is out of bounds")


def max_acceleration(n, x):
    """
    set the maximum allowable acceleration for the specified axis

    Read: return maximum allowable acceleration value in mm/s**2 for the axis

    n – 0 to 99
    x – 000.001 to 500.000 mm/s2 [degrees/s2]
    """
    KEYWORD = "AMX"
    if not (str(x) == "?" or x) >= 0.001 or x <= 500:
        if n >= 0:
            if n <= 99:
                serial_command = str(n) + KEYWORD + str(x)
                return serial_command
            else:
                raise rangeError("Axis number (0-99) or maximum acceleration (0.001-500) is out of bounds")


def acceleration(n, x):
    """
    set the desired acceleration for the specified axis, acceleration must be less than maximum

    Read: returns the acceleration value in mm/s2 for the specified axis

    Did not implement to check whether accel is more than AMX
    """
    KEYWORD = "ACC"
    if not (str(x) == "?" or x) >= 0.001 or x <= 500:
        if n >= 0:
            if n <= 99:
                serial_command = str(n) + KEYWORD + str(x)
                return serial_command
            else:
                raise rangeError("Axis number (0-99) or acceleration (0.001-500) is out of bounds")


def set_axis(n, x):
    """
    override Auto Addressing by manually assigning an axis number to a controller.
    Auto Addressing is the default method of assigning axis numbers on power up and may be reassigned to an axis by substituting a “0” for the parameter value.

    Simultaneous axis swapping is possible by using multiple ANR commands on the same command line. This command can be called globally by specifying a ‘0’ for the
    axis number; however it will only work if the new axis number parameter is set to ‘0’ for auto-addressing.
    """
    pass


def clear_errors(n, x):
    pass


def dump_trace_data(n):
    return str(n) + "DAT?"


def encoder_velocity(n):
    if n >= 1:
        if n <= 99:
            return str(n) + "VRT?"
    raise rangeError("Axis number (0-99)")


def read_closed_loop_deadband(n):
    if n >= 1:
        if n <= 99:
            return str(n) + "DBD?"
    raise rangeError("Axis number (0-99)")


def closed_loop_deadband(n, x1, x2):
    """
    set the acceptable deadband and deadband timeout values.
    Deadband refers to the number of encoder counts (±) from the target that is considered acceptable.
    If 'x1' is set to '0', the controller will continuously oscillate around the target.

    Deadband timeout refers to the amount of time that the controller will try to move into the deadband area.
    If the parameter 'x2' is set to '0', the controller will seek continuously.

    Read: returns the deadband and deadband timeout values for the specified axis
    """
    KEYWORD = "DBD"
    if n >= 0:
        if n <= 99:
            serial_command = str(n) + KEYWORD + str(x1) + "," + str(x2)
            return serial_command
    raise rangeError("Axis number (0-99) is out of bounds")


def deceleration(n, x):
    """
    set the desired deceleration for the specified axis, acceleration must be less than maximum

    Read: returns the acceleration value in mm/s2 for the specified axis

    Did not implement to check whether accel is more than AMX
    """
    KEYWORD = "ACC"
    if not (str(x) == "?" or x) >= 0.001 or x <= 500:
        if n >= 0:
            if n <= 99:
                serial_command = str(n) + KEYWORD + str(x)
                return serial_command
            else:
                raise rangeError("Axis number (0-99) or deceleration is out of bounds")


def factory_defaults(n):
    """
    restores controller factory defaults

    Read: None
    """
    KEYWORD = "DEF"
    if n >= 0:
        if n <= 99:
            serial_command = str(n) + KEYWORD
            return serial_command
    raise rangeError("Axis number (0-99) or acceleration is out of bounds")


def set_encoder(self, *args):
    pass


def encoder_resolution(self, *args):
    pass


def read_and_clear_errors(self, *args):
    pass


def emergency_stop(n):
    """
    stops a specific axis or all connected axes simultaneously in case of an emergency

    Read: None
    """
    KEYWORD = "EST"
    if n >= 0:
        if n <= 99:
            serial_command = str(n) + KEYWORD
            return serial_command
    raise rangeError("Axis number (0-99) is out of bounds")


def execute_program(self, *args):
    pass


def set_loop_mode(n, x):
    """
    select the feedback mode of the controller.

    Read: A read operation returns the following loop mode values for the specified axis:
    0 – Open Loop [default]
    1 – Clean Open Loop
    2 – Clean Open Loop Movement, Closed Loop deceleration
    3 – Closed Loop
    """
    KEYWORD = "FBK"
    if str(x) == "?" or x in (0, 1, 2, 3):
        if n >= 0 and n <= 99:
            serial_command = str(n) + KEYWORD + str(x)
            return serial_command
    else:
        raise rangeError("Axis number (0-99) or loop mode number (0, 1, 2, 3) is out of bounds")


def home_config(n, x):
    """
    select the direction of motion when the Home [HOM] command is initialized

    Read: returns the current direction setting:
    0 – Home starts in the direction of the negative limit
    1 – Home starts in the direction of the positive limit
    """
    KEYWORD = "HCG"
    if str(x) == "?" or x in (0, 1):
        if n >= 0 and n <= 99:
            serial_command = str(n) + KEYWORD + str(x)
            return serial_command
    else:
        raise rangeError("Axis number (0-99) or motion setting number (0-1) is out of bounds")


def home(n, x='none'):
    """
    used to find the home (zero) position for a specified axis.

    An error will occur if there is no encoder signal at the time of execution.
    Home is configured using the HCG command.

    This command will jog the stage till it reaches the limit configured by the HCG command. It will then acquire the zero position by looking for the index.
    This command blocks all communication over the serial port during motion. The controller will buffer all commands sent during this period and execute them
    once the command has found the index.

    Caution: if you write too many commands while this command is executing you run the risk of overloading the receive buffer.

    Read: returns the following calibration values for the specified axis:
    0 – Not calibrated to home position
    1 – Calibrated to home position
    """
    KEYWORD = "HOM"
    if n >= 0 and n <= 99:
        if x == "?":
            serial_command = str(n) + KEYWORD + str(x)
            return serial_command
        if x == "none":
            serial_command = str(n) + KEYWORD
            return serial_command
        raise parameterError("Parameter entered incorrectly")
    else:
        raise rangeError("Axis number (0-99) or motion direction number (0-1) is out of bounds")


def IO_pin_def(self, *args):
    pass


def IO_function(self, *args):
    pass


def jog_acc_and_deacc(n, x):
    """
    set the desired value for the jog acceleration and deceleration for a specified axis.
    The controller will not allow for JAC values that are greater than AMX.

    Read: returns the jog acceleration and deceleration value in mm/s2 for the specified axis. 
    """
    KEYWORD = "JAC"
    if not (str(x) == "?" or x) >= 0.001 or x <= 500:
        if n >= 0:
            if n <= 99:
                serial_command = str(n) + KEYWORD + str(x)
                return serial_command
            else:
                raise rangeError("Axis number (0-99) or acceleration (0.001-500) is out of bounds")


def jog_mode(n, x):
    """
    used to jog a specific axis, or move continuously in a direction with no target position. 
    The jog velocity is a percentage of the maximum velocity and may be changed onthe-fly by sending another JOG command during motion. 
    
    Read: None
    """
    KEYWORD = "JOG"
    if not (str(x) == "?" or x) >= 0.001 or x <= 100:
        if n >= 0:
            if n <= 99:
                serial_command = str(n) + KEYWORD + str(x)
                return serial_command
            else:
                raise rangeError("Axis number (0-99) or percent of max velocity (0.001-100) is out of bounds")


def limit_config(self, *args):
    pass


def limit_switch_direction(self, *args):
    pass


def program_list(self, *args):
    pass


def limit_switch_polarity(self, *args):
    pass


def to_neg_limit(n):
    KEYWORD = "MLN"
    if n >= 0:
        if n <= 99:
            serial_command = str(n) + KEYWORD
            return serial_command
    raise rangeError("Axis number (0-99) or motion current number (0-1) is out of bounds")


def to_pos_limit(n):
    KEYWORD = "MLP"
    if n >= 0:
        if n <= 99:
            serial_command = str(n) + KEYWORD
            return serial_command
    raise rangeError("Axis number (0-99) or motion current number (0-1) is out of bounds")


def toggle_motor_on_off(n, x):
    """
    user to turn the motor current flow 'off' or 'on' for a specific axis
    Turn the motor current off will cause the piezo to replax and the stage will shift slightly!

    Read: returns the following motor current off/on values for the specified axis:
    0 – Motor current is off
    1 – Motor current is on
    """
    KEYWORD = "MOT"
    if str(x) == "?" or x in (0, 1):
        if n >= 0 and n <= 99:
            serial_command = str(n) + KEYWORD + str(x)
            return serial_command
    else:
        raise rangeError("Axis number (0-99) or motion current number (0-1) is out of bounds")


def motor_polarity(self, *args):
    pass


def sync_move_abs(self, *args):
    pass


def sync_move_rel(self, *args):
    pass


def move_abs(n, x):
    """
    used to initiate an instantaneous move to an absolute position for a specified axis. 
    An error will occur if the commanded position is outside of the soft limits
    
    x – ± 0.000001 to ± 999.999999 mm [degrees]

    Read: None
    """
    KEYWORD = "MVA"
    if x == 0:
        x = 1e-06
    elif not (str(x) == "?" or abs(x)) >= 1e-06 or abs(x) <= 999.999999:
        if n >= 0:
            if n <= 99:
                serial_command = str(n) + KEYWORD + "{:.6f}".format(x)
                return serial_command
            else:
                raise rangeError("Axis number (0-99) or range of movement (0.000001 - 999.999999) is out of bounds")


def move_rel(n, x):
    """
    used to initiate an instantaneous move to a relative position for a specified axis. 
    An error will occur if the commanded increment will cause the stage to travel outside of the set soft limits. 
   
    x – ± 0.000001 to ± 999.999999 mm [degrees]

    Read: None
    """
    KEYWORD = "MVR"
    if abs(x) >= 1e-06 and abs(x) <= 999.999999:
        if n >= 0 and n <= 99:
            serial_command = str(n) + KEYWORD + "{:.6f}".format(x)
            return serial_command
    else:
        raise rangeError("Axis number (0-99) or range of movement (0.000001 - 999.999999) is out of bounds")


def loop_program(self, *args):
    pass


def read_availible_programs(axis):
    serial_command = str(axis) + "PGM?"
    return serial_command


def program_recording_start(axis, program_number):
    serial_command = str(axis) + "PGM" + str(program_number)
    return serial_command


def program_recording_end(axis):
    serial_command = str(axis) + "END"
    return serial_command


def erase_program(axis, program_number):
    serial_command = str(axis) + "ERA" + str(program_number)
    return serial_command


def run_program(axis, program_number):
    serial_command = str(axis) + "EXC" + str(program_number)
    return serial_command


def set_feedback_constants(self, *args):
    pass


def position(n):
    """
    used to read the position information from the specified axis controller
    
    Read: returns the position values in mm for the specified axis in the following format:
    [Theoretical position in mm, Encoder position in mm]
    [Theoretical position in degrees, Encoder position in degrees]

    Note: Setting the axis to 0 will cause an error
    """
    KEYWORD = "POS"
    if n >= 1:
        if n <= 99:
            serial_command = str(n) + KEYWORD + "?"
            return serial_command
    raise rangeError("Axis number (1-99) is out of bounds")


def set_resolution(self, *args):
    pass


def soft_reset(self, *args):
    pass


def start_sync_move(self, *args):
    pass


def save_axis_settings(self, *args):
    pass


def status_byte(self, *args):
    pass


def stop_motion(n):
    """
    used to stop the motion for a specified axis

    Read: None
    """
    KEYWORD = "STP"
    if n >= 0:
        if n <= 99:
            serial_command = str(n) + KEYWORD
            return serial_command
    raise rangeError("Axis number (0-99) is out of bounds")


def save_start_up_position(self, *args):
    pass


def sync(self, *args):
    pass


def neg_soft_limit_position(n, x='none'):
    """
    used to set the desire negative soft limit position, using absolute position for a axis.
    The negatice soft limit position value must be less than the positive soft limit poisiton value

    x – ± 0.000001 to ± 999.999999 mm [degrees]

    Read: return the negative soft limit poistion value
    """
    KEYWORD = "TLN"
    if n >= 0 and n <= 99:
        if x == "?":
            serial_command = str(n) + KEYWORD + str(x)
            return serial_command
        if abs(x) >= 1e-06:
            if abs(x) <= 999.999:
                serial_command = str(n) + KEYWORD + str(x)
                return serial_command
        if x == "none":
            serial_command = str(n) + KEYWORD
            return serial_command
        raise parameterError("Parameter entered incorrectly")
    else:
        raise rangeError("Axis number (0-99) or range of movement (+/-0.000001-999.999999) is out of bounds")


def pos_soft_limit_position(n, x='none'):
    """
    used to set the desire positive soft limit position, using absolute position for a axis.
    The positive soft limit position value must be greater than the negative soft limit poisiton value

    x – ± 0.000001 to ± 999.999999 mm [degrees]

    Read: return the positive soft limit poistion value
    """
    KEYWORD = "TLP"
    if n >= 0 and n <= 99:
        if x == "?":
            serial_command = str(n) + KEYWORD + str(x)
            return serial_command
        if abs(x) >= 1e-06:
            if abs(x) <= 999.999:
                serial_command = str(n) + KEYWORD + str(x)
                return serial_command
        if x == "none":
            serial_command = str(n) + KEYWORD
            return serial_command
        raise parameterError("Parameter entered incorrectly")
    else:
        raise rangeError("Axis number (0-99) or range of movement (+/-0.000001-999.999999) is out of bounds")


def perform_trace(n, samples, frequency, position):
    serial_command = str(n) + "TRA" + str(samples) + "," + str(frequency) + "," + str(position)
    return serial_command


def velocity(n, x):
    """
    used to set the desired velocity for the specified axis. 
    The velocity may be changed on-the-fly by sending another VEL command during motion. 
    The velocity value should be lower than the maximum allowable velocity [VMX] for the command to be accepted. 
    
    x – 000.001 to VMX (999.999 mm/s) [degrees/s]

    Read: returns the velocity value in mm/s for the specified axis
    """
    KEYWORD = "VEL"
    if not x == "?":
        if not x * 0.001 >= 1e-06 or x * 0.001 <= 999.999999:
            if n >= 0 and n <= 99:
                if x == "?":
                    serial_command = str(n) + KEYWORD + str(x)
                    return serial_command
                serial_command = str(n) + KEYWORD + str(x * 0.001)
                return serial_command
    else:
        raise rangeError("Axis number (0-99) or range of movement (0.000001-999.999) is out of bounds")


def firmware_version(self, *args):
    pass


def max_velocity(self, *args):
    pass


def wait_for_stop(axis):
    serial_command = str(axis) + "WST"
    return serial_command


def wati_for_sync(self, *args):
    pass


def wait_for_time_period(axis, time):
    serial_command = str(axis) + "WTM" + str(time)
    return serial_command


def zero_position(n):
    """
    used to set the absolute zero position for the specified axis.

    Read: None

    Notice that the axis numbers is restricted in 1-99
    """
    KEYWORD = "ZRO"
    if n >= 1:
        if n <= 99:
            serial_command = str(n) + KEYWORD
            return serial_command
    raise rangeError("Axis number (1-99) is out of bounds")


def set_hardware_trigger(axis, io_pin, function):
    serial_command = str(axis) + "IOF" + str(io_pin) + "," + str(function)
    print(serial_command)
    return serial_command


def set_pin(axis, io_pin, input_output):
    serial_command = str(axis) + "IOD" + str(io_pin) + "," + str(input_output)
    print(serial_command)
    return serial_command


def set_encoder(axis, state):
    serial_command = str(axis) + "EPL" + str(state)
    print(serial_command)
    return serial_command


def get_errors(axis):
    serial_command = str(axis) + "ERR?"
    return serial_command


if __name__ in "__main__":
    max_acceleration(1, 0.002)
