# -*- coding: utf-8 -*-
# Python for Test and Measurement

# Requires VISA installed on Control PC
# 'http://www.agilent.com/find/visa'
# Requires PyVISA to use VISA in Python
# 'http://pyvisa.sourceforge.net/pyvisa/'

# Keysight IO Libraries 18.1.24130.0
# Anaconda Python 3.7.1 64 bit
# pyvisa 1.10.1

##"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
## Copyright © 2020 Agilent Technologies Inc. All rights reserved.
##
## You have a royalty-free right to use, modify, reproduce and distribute this
## example files (and/or any modified version) in any way you find useful, provided
## that you agree that Agilent has no warranty, obligations or liability for any
## Sample Application Files.
##
##"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

# Example Description:
#    This example setups an N774xA to perform a continuous data streaming measurement

# Required Instrument Setup to Execute Example:
#    N774xA/C MultiPort Power Meter

# Additional Information:
#    Additional information on the MPPM streaming is in the following white paper
#    http://literature.cdn.keysight.com/litweb/pdf/5990-3710EN.pdf


import pyvisa as visa
import time
import numpy as np

class N774xA():

    def __init__(self):
        self.connected = False

    def __del__(self):
        if self.connected:
            self.disconnect()
    def connect(self,visaAddr):
        self.rm = visa.ResourceManager()
        self.instrument = self.rm.open_resource(visaAddr)
        print(self.instrument.query("*IDN?")) #Requests the device for identification
        self.connected = True

        # Set Timeout - 5 seconds
        self.instrument.timeout = 5000

        # *IDN? - Query Instrumnet ID
        self.instrument.write("*CLS")
        self.instrument.write("*IDN?")
        print (self.instrument.read())

        # Reset the instrument
        self.instrument.write("*RST")
        self.instrument.write("*OPC?")
        print (self.instrument.read())

    def mppm_err(self, inst):
        ## Query for Errors
        error_list = []
        i = 0
        while True:
            inst.write(":SYSTem:ERRor?")
            error = inst.read()
            error_list.append(error)
            i = i + 1
            if 'No error' in error:
                break
        return error_list
    # Some Extra N774xA functions based on the following white paper:
    # https://www.keysight.com/ca/en/assets/7018-02079/application-notes/5990-3710.pdf
    def stopLogging(self, set_chan):
        self.instrument.write("SENS%d:FUNC:STAT LOGG,STOP" % (set_chan))
        #print("SENS%d:FUNC:STAT LOGG,STOP: " % (set_chan) + str(self.mppm_err(self.instrument)))

    def setLoopRangeGainTriggerPWR(self, set_chan, PWR_unit, num_of_samples, averaging_time_ms):
        ## Unlimited Loops
        self.instrument.write("SENS%d:FUNC:LOOP 0" % (set_chan))
        #print("SENS%d:FUNC:LOOP 0" % (set_chan) + str(self.mppm_err(self.instrument)))
        print("Loop: " + self.instrument.query("SENS%d:FUNC:LOOP?" % (set_chan)).strip())
        ## Manual Range Mode
        self.instrument.write("SENS%d:POW:RANGE:AUTO 0" % (set_chan))
        #print("SENS%d:POW:RANGE:AUTO 0: " % (set_chan) + str(self.mppm_err(self.instrument)))
        print ("Range Auto: " + self.instrument.query("SENS%d:POW:RANGE:AUTO?" % (set_chan)).strip())
        ## Manual Gain Mode
        self.instrument.write("SENS%d:POW:GAIN:AUTO 0" % (set_chan))
        #print("SENS%d:POW:GAIN:AUTO 0: " % (set_chan) + str(self.mppm_err(self.instrument)))
        print ("Gain Auto: " + self.instrument.query("SENS%d:POW:GAIN:AUTO?" % (set_chan)).strip())
        ## MME Single Measurement Trigger Mode
        self.instrument.write("TRIG%d:INPUT MME" % (set_chan))
        #print("TRIG%d:INPUT MME: " + str(self.mppm_err(self.instrument)))
        ## Set Range
        self.instrument.write("SENS%d:POW:RANG 10DBM" % (set_chan))
        #print("SENS%d:POW:RANG 10DBM: " % (set_chan) + str(self.mppm_err(self.instrument)))
        print ("Range Settings: " + self.instrument.query("SENS%d:POW:RANG?" % (set_chan)).strip())
        ## Set Power Unit
        self.instrument.write("SENS%d:POW:UNIT %d" % (set_chan, PWR_unit)) # 0:dBm, 1:watt
        #print("SENS%d:POW:UNIT 1:" % (set_chan) + str(self.mppm_err(self.instrument)))
        print ("Power Unit: " + self.instrument.query("SENS%d:POW:UNIT?" % (set_chan)).strip())
        ## Setup Logging
        self.instrument.write("SENS%d:FUNC:PAR:LOGG %d, %.3fms" % (set_chan,num_of_samples,averaging_time_ms)) # Number of samples (Max = 1000000), averaging time, overall data acquisition time = Number_of_samples * averaging_time
        #print("SENS%d:FUNC:PAR:LOGG %d, %.fms" % (set_chan,num_of_samples,averaging_time_ms) + str(self.mppm_err(self.instrument)))
        #print ("Log Settings: " + self.instrument.query("SENS%d:FUNC:PAR:LOGG?" % (set_chan)).strip())

    def startLogging(self, set_chan): # This prepares the N77 to start taking measurements once the trigger is received.
        ##Start Logging
        self.instrument.write("SENS%d:FUNC:STAT LOGG,STAR" % (set_chan))
        #print("SENS%d:FUNC:STAT LOGG,STAR: " % (set_chan) + str(self.mppm_err(self.instrument)))

    def trigger(self, triggerType): #1: Internal trigger
        self.instrument.write("TRIG "+str(triggerType))

    def measure(self, meas_chan, measurement_loops):
        ## Loop to get x Continuous results
        j = 0
        index_current = 0
        index_old = 0
        total_array=[]
        while True:
            ## Query for Measurement Complete
            self.instrument.write("SENS1:FUNC:RES:INDex?")
            index_old = self.instrument.read().strip()
            while True:
                #time.sleep(1)
                self.instrument.write("SENS1:FUNC:RES:INDex?")
                index_current = self.instrument.read().strip()
                #print ('index_current: ' + index_current)
                #print ('index_old: ' + index_old)
                if index_current > index_old:
                    # If the index changes by more than 1 this indicates multiple measurements occured
                    # during download and streaming data has been lost
                    break
                else:
                    index_old = index_current

            ##  Query Data
            for channel_count, i in enumerate(meas_chan):
                data = self.instrument.query_binary_values("SENS%d:FUNC:RESULT?" % (i), "f", False)
                # Convert list to Array of Float to Plot Data
                array = np.array(data)
                if channel_count==0:
                    total_array = array
                else:
                    total_array = np.array([total_array, array])

            #total_array = np.concatenate((total_array, array))

            j = j + 1
            print("End of Loop# "+str(j))
            ## Determine how many loops have been performed
            if j == measurement_loops:
                break

        return total_array

    def stopLogging(self, set_chan):
        ##Stop Logging
        self.instrument.write("SENS%d:FUNC:STAT LOGG,STOP" % (set_chan))
        #print("SENS%d:FUNC:STAT LOGG,STOP: " % (set_chan) + str(self.mppm_err(self.instrument)))


    def disconnect(self):
        self.instrument.close()



