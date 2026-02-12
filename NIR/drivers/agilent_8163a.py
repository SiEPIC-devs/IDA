# uncompyle6 version 3.9.2
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: /home/pi/Desktop/new GUI/NIR laser/agilent_8163a.py
# Compiled at: 2022-05-02 18:40:11
# Size of source mod 2**32: 20385 bytes
"""
Unit       Default
    
Meters     M
Decibel    DB
Second     S
dbm        DBM
Hertz      HZ
Watt       Watt
m/s        M/S
"""
import sys

def print(string):
    term = sys.stdout
    term.write(str(string) + "\n")
    term.flush()


class agilent_8163a_mainframe:

    def __init__(self, *args):
        pass

    @staticmethod
    def operation_complete_query():
        """
        parses all program message units in the input queue, sets the operation complete bit in the
        standard event status register, and places ASCII 1 in the output queue, when the contents of the input queue
        has been processed

        1: is retunred if all modules are ready to execute a new operation
        0: is returned if any module is busy
        """
        return "*OPC"

    @staticmethod
    def slot_full(slot):
        return "SLOT" + str(slot) + ":EMPTy?"

    @staticmethod
    def identity():
        return "*IDN?"

    @staticmethod
    def options():
        return "*OPT?"

    @staticmethod
    def is_laser(slot):
        return "SLOT" + str(slot) + ":IDN?"

    @staticmethod
    def is_power_sensor(slot):
        return "SLOT" + str(slot) + ":IDN?"

    @staticmethod
    def clear_status():
        return "*CLS"

    @staticmethod
    def options():
        return "*OPT?"

    @staticmethod
    def check_error():
        """
        Returns the next error from error queue
        Each error has an error code and a description, separated by a commma.
        + errors are device dependent, and -errors are defined by SCPI standard.
        """
        return "SYST:ERR?"

    @staticmethod
    def set_hardware_trigger_config(additional):
        """
        sets the harware trigger config with regard to output and input trigger connectors

        DIS - trigger connectors are disabled
        DEF - input trigger connector is activated, the incoming trigger response fro each slot determines how
        each slot responds to an incoming trigger
        PASS - same as DEF but a trigger at the input tirgger connector geneerates a trigger at the output trigger
        connector automatically
        LOOP - the same as DEF but a trigger at the output trigger connector generates a trigger at the input
        trigger connector automatically
        
        """
        return "TRIG:CONF " + additional

    @staticmethod
    def send_trigger(channel):
        return "trig " + str(channel)

    @staticmethod
    def read_data(slot, channel):
        """
        returns the data array of the last data acquisition function
        """
        return "SENS" + str(slot) + ":CHAN" + str(channel) + ":FUNC:RES?"

    @staticmethod
    def read_max_block_size(slot, channel):
        """
        returns the max block size for a single GPIB transfer for power meter data acquisition functions.
        """
        return "SENS" + str(slot) + ":CHAN" + str(channel) + ":FUNC:RES:MAXB?"

    @staticmethod
    def read_block(slot, channel, offset, samples):
        """
        returns a specific binary block from the data array for the last data acquisition function
        """
        return ":SENSe" + str(slot) + ":CHANnel" + str(channel) + ":FUNCtion:RESult:BLOCk? " + str(offset) + "," + str(samples)

    @staticmethod
    def set_detector_sensor_logging(slot, num_samples, averaging):
        """
        sets the number of data points and the averaging time fro the logging data acquisition function
        """
        return "SENS" + str(slot) + ":FUNC:PAR:LOGG " + str(num_samples) + "," + str(averaging)

    @staticmethod
    def read_detector_sensor_logging(slot):
        """
        returns the number of datapoints and the averaging time for logging
        """
        return "SENS" + str(slot) + ":FUNC:PAR:LOGG?"

    @staticmethod
    def set_detector_data_acquisition(slot, additional, start_stop):
        """
        Enables/disables the logging, MinMAX, or stability data acquisition function mode

        additional:
        LOGG - 
        STAB - 
        MINMAX -

        STOP
        STAR
        """
        return "SENS" + str(slot) + ":FUNC:STAT " + str(additional) + "," + str(start_stop)

    @staticmethod
    def read_detector_data_acquisition(slot):
        """
        returns the function mode, and the status of the data acquistion function
        """
        return "SENS" + slot + ":FUNC:STAT?"

    @staticmethod
    def set_detector_output_trigger_timing(slot, channel, additional):
        """
        Specifies when an output trigger is generated and arms the module

        Additionals:
        DIS - Never
        AVG - when a averaging time period finishes
        MEA - when a averaging time period begins
        MOD - for every leading edge of a digitally-modulated signal
        STF - when a sweep cycle finishes
        SWS - when a sweep cycle starts
        """
        return "TRIG" + str(slot) + ":CHAN" + str(channel) + ":OUTP " + str(additional)

    @staticmethod
    def read_detector_output_trigger_timing(slot, channel):
        return "TRIG" + str(slot) + ":CHAN" + str(channel) + ":OUTP?"

    @staticmethod
    def set_incoming_trigger_response(slot, response):
        """
        This setting allows the sweep to wait for a hardware or software
        trigger before beginning, after all configuration commands are
        sent

        - IGN - ignore incoming trigger
        - SME - start single measurement. One sample is performed and result is stored in data array
        - CME - start complete measurement
        - NEXT - Perform next step of a stepped sweep
        - SWS - Start a sweep cycle
        """
        return "TRIG" + str(slot) + ":INP " + str(response)

    @staticmethod
    def read_incoming_trigger_response(slot):
        return "TRIG" + str(slot) + ":INP?"

    @staticmethod
    def read_sensor_wavelength(slot, channel, additional='None'):
        """
        Addtional parameters allowed:

        + ' MIN' minimum programmable value
        + ' MAX' maximum programmable value
        + ' DEF' half the sum of the min programmable value anf the maximum programmable value
        """
        if additional == "None":
            return "SENS" + str(slot) + ":CHAN" + str(channel) + ":POW:WAV?"
        return "SENS" + str(slot) + ":CHAN" + str(channel) + ":POW:WAV?" + " " + str(additional)

    @staticmethod
    def set_sensor_wavelength(slot, channel, wavelength):
        """
        Default units is in meters unless specified
        """
        return "SENS" + str(slot) + ":CHAN" + str(channel) + ":POW:WAV " + str(wavelength)

    @staticmethod
    def read_detector_averaging_time(slot):
        """
        returns the gpib command to read the averging time in seconds
        """
        return "SENS" + str(slot) + ":POW:ATIM?"

    @staticmethod
    def set_detector_averaging_time(slot, averaging_time):
        """
        returns the gpib command to set the averging time in seconds

        Example: 0.002000
        """
        return "SENS" + str(slot) + ":POW:ATIM " + str(averaging_time)

    @staticmethod
    def read_power_sensor_unit(slot, channel):
        return "SENS" + str(slot) + ":CHAN" + str(channel) + ":POW?"

    @staticmethod
    def power_sensor_autorange(slot, on_off):
        """
        0:OFF
        1:ON
        """
        return "SENSe" + str(slot) + ":POWer:RANGe:AUTO " + str(on_off)

    @staticmethod
    def is_power_sensor_autoranging(slot):
        return "SENS" + str(slot) + ":POW:RANG:AUTO?"

    @staticmethod
    def read_power_sensor_range(slot, channel):
        return "SENS" + str(slot) + ":CHAN" + str(channel) + ":POW:RANG?"

    @staticmethod
    def set_power_sensor_range(slot, channel, power_range):
        """
        power_range example: 1.00DBM
        """
        return "SENS" + str(slot) + ":CHAN" + str(channel) + ":POW:RANG " + str(power_range)

    @staticmethod
    def power_sensor_unit(slot, channel, unit):
        """
        0:dbm
        1:Watt
        """
        return "SENSe" + str(slot) + ":CHANnel" + str(channel) + ":POWer:UNIT " + unit

    @staticmethod
    def set_continuous(slot, channel):
        """
        sets the software trigger to continuous sweeping mode
        """
        return "init" + str(slot) + ":chan" + str(channel) + ":cont 1"

    @staticmethod
    def power_sensor_head_response(slot, head):
        return "SLOT" + str(slot) + ":HEAD" + str(head) + ":WAVelength:RESPonse:CSV?"

    @staticmethod
    def power_sensor_reference(slot, channel, levelindb):
        return "SENSe" + str(slot) + ":CHANnel" + str(channel) + ":POWer:REFerence TOREF," + str(levelindb) + "DBM"

    @staticmethod
    def power_sensor_logging_result(slot, channel, offset, samples):
        return ":SENSe" + str(slot) + ":CHANnel" + str(channel) + ":FUNCtion:RESult?"

    @staticmethod
    def power_sensor_logging_state(slot, channel):
        return "SENSe" + str(slot) + ":CHANnel" + str(channel) + ":FUNCtion:STATe?"

    @staticmethod
    def enable_trigger():
        return "TRIGger:CONFiguration PASSthrough"

    @staticmethod
    def trigger_config(mode):
        """
        0 - DISabled
        1 - DEFault
        2 - PASSthrough
        3 - LOOPback
        """
        return "TRIG:CONF " + mode

    @staticmethod
    def set_sensor_power_reading(slot, additional, on_off):
        """
        CONT - Continuously reading
        IMM - Completes 1 measurement
        """
        return "INIT" + slot + ":" + additional + " " + on_off

    @staticmethod
    def read_power(slot, channel):
        return "FETC" + str(slot) + ":CHAN" + str(channel) + ":POW?"

    @staticmethod
    def disable_trigger_rearm(trigger):
        return "TRIGger" + str(trigger) + ":INPut:REARm 0"

    @staticmethod
    def enable_output_trigger_rearm(trigger):
        """
        Sets the arming response of a channel to an outgoing trigger
        """
        return "TRIGger" + str(trigger) + ":OUTPut:REARm 1"

    @staticmethod
    def read_trigger():
        return "TRIGger:CONFiguration?"

    @staticmethod
    def set_laser_sweep_state(slot, channel, start_stop):
        """
        gives the option to stop, start, or continue a wavelength sweep

        start_stop:
        STAR
        STOP
        CONT
        """
        return "SOUR" + str(slot) + ":CHAN" + str(channel) + ":WAV:SWE " + str(start_stop)

    @staticmethod
    def read_laser_sweep_state(slot, channel):
        """
        returns the states of a sweep

        0: sweep is not running
        1: sweep is running
        """
        return "SOUR" + str(slot) + ":CHAN" + str(channel) + ":WAV:SWE:STAT?"

    @staticmethod
    def read_laser_sweep_parameters(slot):
        """
        returns the sweep parameters

        """
        return "SOUR" + str(slot) + ":WAV:SWE:chec?"

    @staticmethod
    def read_trigger_number(slot):
        """
        returns the number of triggers 

        """
        return "SOUR" + str(slot) + ":WAV:SWE:exp?"

    @staticmethod
    def set_laser_output_trigger_timing(slot, additional):
        """
        Specifies when an output trigger is generated and arms the module

        Additionals:
        DIS - Never
        AVG - when a averaging time period finishes
        MEA - when a averaging time period begins
        MOD - for every leading edge of a digitally-modulated signal
        STF - when a sweep cycle finishes
        SWS - when a sweep cycle starts
        """
        return "TRIG" + str(slot) + ":OUTP " + str(additional)

    @staticmethod
    def read_laser_output_trigger_timing(slot):
        return "TRIG" + str(slot) + ":OUTP?"

    @staticmethod
    def set_laser_lambda_logging(slot, on_off):
        """
        Switches lambda logging on or off. Lambda logging records the exact wavelength of a
        tunable laser module when a trigger is generated during a continuous sweep 

        0: OFF
        1: ON
        """
        return "SOUR" + str(slot) + ":WAV:SWE:LLOG " + str(on_off)

    @staticmethod
    def set_laser_amplitude_modulation(slot, channel, on_off):
        """
        Enables and disables amplitude modulation of the laser output

        on_off:
        0:OFF
        1:ON
        """
        return "SOUR" + str(slot) + ":CHAN" + str(channel) + ":AM:STAT " + str(on_off)

    @staticmethod
    def set_laser_sweep_cycles(slot, cycles):
        """
        Sets the number of sweep cycles.

        cycles:
        Some Integer value - 
        MIN - mimnmum programmable value
        MAX - maximum programmable vlaue
        DEF - half thhe sum of the min and the mac value
        0 - cycles continuously
        """
        return "SOUR" + str(slot) + ":WAV:SWE:CYCL " + str(cycles)

    @staticmethod
    def set_laser_sweep_directionality(slot, sweep_directionality):
        return "SOUR" + str(slot) + ":WAV:SWE:REP " + str(sweep_directionality)

    @staticmethod
    def set_laser_sweep_mode(slot, additional):
        """
        Sets the sweep mode

        addtional:
        STEP - Stepped sweep mode
        MAN - Manual sweep mode
        CONT - continuous sweep mode
        """
        return "SOUR" + str(slot) + ":WAV:SWE:MODE " + str(additional)

    @staticmethod
    def set_laser_sweep_step_size(slot, size):
        """
        Sets the widtho of the sweep step

        Example: 0.010000nm
        """
        return "SOUR" + str(slot) + ":WAV:SWE:STEP " + str(size)

    @staticmethod
    def read_laser_sweep_step_size(slot):
        """

        """
        return "SOUR" + str(slot) + ":WAV:SWE:STEP?"

    @staticmethod
    def laser_power_units(slot, unit):
        """
        sets the power units.
        0: dbm
        1: W
        """
        return "SOUR" + str(slot) + ":POW:UNIT " + str(unit)

    @staticmethod
    def lock_laser(on_off, password):
        """
        Swithes the laser lock on/off to enable the laser

        password: 4 digit safety password
        """
        return "LOCK" + str(on_off) + "," + str(password)

    @staticmethod
    def is_locked():
        """
        Queries the current state of the lock
    
        - 0 lock is off
        - 1 lock is on
        """
        return "LOCK?"

    @staticmethod
    def laser_current(slot, on_off):
        """
        Switches laser current on or off

        0 or OFF
        1 or ON
        """
        return "OUTP" + str(slot) + " " + str(on_off)

    @staticmethod
    def read_laser_current(slot):
        return "OUTP" + str(slot) + "?"

    @staticmethod
    def read_laser_wavelength(slot, additional='None'):
        """
        Reads the current laser_wavelength

        Additionals:
        MIN
        MAX
        """
        if additional == "None":
            return "SOUR" + str(slot) + ":WAV?"
        return "SOUR" + str(slot) + ":WAV? " + str(additional)

    @staticmethod
    def read_laser_power(slot, additional='None'):
        """
        Reads the current laser_power

        Additionals:
        MIN
        MAX
        """
        if additional == "None":
            return "SOUR" + str(slot) + ":POW?"
        return "SOUR" + str(slot) + ":POW? " + str(additional)

    @staticmethod
    def set_laser_power_state(slot, on_off):
        """
        Switches the laser of the chosen source on or off

        0:OFF
        1:ON
        """
        return "SOUR" + str(slot) + ":POW:STAT " + str(on_off)

    @staticmethod
    def read_laser_power_state(slot):
        """
        Switches the laser of the chosen source on or off

        0:OFF
        1:ON
        """
        return "SOUR" + str(slot) + ":POW:STAT?"

    @staticmethod
    def set_laser_current_wavelength(slot, wavelength):
        """
        Sets the absolute laser wavelength output.

        Specify the wavelength units when passing to method
        """
        return "SOUR" + str(slot) + ":WAV " + str(wavelength) + "NM"

    @staticmethod
    def set_laser_current_power(slot, power):
        """
        Sets the absolute laser power output
        """
        return "SOUR" + str(slot) + ":POW " + str(power)

    @staticmethod
    def set_regulated_path(slot, path):
        """
        HIGH - High power output is regulated
        LOWS - Low SSE output is regulated
        BHR - Both outputs are active but only th high power output is regulated
        BLR - Both outputs are active but only the low SSW output is regulated
        """
        return "OUTP" + str(slot) + ":PATH " + str(path)

    @staticmethod
    def read_regulated_path(slot):
        return "OUTP" + str(slot) + ":PATH?"

    @staticmethod
    def set_continuous_sweep_speed(slot, speed):
        """
        Sets the speed for the continuous sweep.

        Example:
        speed: 5.00nm/s
        """
        return "SOUR" + str(slot) + ":WAV:SWE:SPE " + str(speed)

    @staticmethod
    def read_continuous_sweep_speed(slot):
        return "SOUR" + str(slot) + ":WAV:SWE:SPE?"

    @staticmethod
    def read_sweep_boundary_wavelength(slot, start_stop, additional):
        """
        Command returns the max or min starting / stopping wavelength possible, this is wavelenght dependent

        start_stop:
        STAR
        STOP
        
        additional:
        MAX
        MIN
        """
        return "SOUR" + str(slot) + ":WAV:SWE:" + str(start_stop) + "? " + str(additional)

    @staticmethod
    def set_sweep_wavelength(slot, start_stop, wavelength):
        """
        sets the starting point of the sweep

        - Please Specify the wavelength units when wavelength parameter is passed

        Example: 1525.000nm
        """
        return "SOUR" + str(slot) + ":WAV:SWE:" + str(start_stop) + " " + str(wavelength)

    @staticmethod
    def read_trigger_status(slot):
        """
        reads trigger status
        """
        return "SOUR" + str(slot) + ":WAV:SWE:FLAG?"

    @staticmethod
    def arm_laser_sweep(slot):
        """
        reads trigger status
        """
        return "SOUR" + str(slot) + ":WAV:SWE 1"

    @staticmethod
    def send_laser_trigger(slot):
        """
        reads trigger status
        """
        return "SOUR" + str(slot) + ":WAV:SWE:soft"

    @staticmethod
    def read_laser_wavelength_points_avail(slot):
        """
        reads trigger status
        """
        return "SOUR" + str(slot) + ":read:points? llog"

    @staticmethod
    def read_laser_wavelength_log(slot):
        """
        reads trigger status
        """
        return "SOUR" + str(slot) + ":read:data? llog"

    @staticmethod
    def read_laser_wavelength_data_block(slot, offset, points):
        """
        reads trigger status
        """
        return "SOUR" + str(slot) + ":read:data:block? llog," + str(offset) + "," + str(points)
