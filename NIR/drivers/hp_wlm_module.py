

import time 

class HP_WLM():
    '''
    @brief DREAMSlab instrument driver for the HP 86120C multi-wavelength meter.

    @details
    This driver was written to profile tuning of DFB lasers with current.  
    Note that the functionality implemented is limited and focused specifically on that use case.
    Stolen from the Scylla Stage in June 2025
    '''

    def __init__(self):
        self.instrument = None
        

    def identify(self):
        return self.instrument.query("*IDN?") 

    def Reset(self):
        self.instrument.write("*CLS")
        self.instrument.write("*RST")


    def FindPeakWavelength(self, highRes = False):
        '''
        @brief Returns the wavelength with the highest power
        @note This function was written for a spectrum with one peak, it may misidentify a spectrum with multiple lasers
   
        @param highRes bool: Thether to capture a slow high res measurement (1pm resolution) or a faster low res measruement (10pm resolution). Default is False
        
        @return float: The peak wavelength in nm
        '''
        speed_setting = "MAX" if highRes == False else "MIN"

        if highRes == False:
            speed_setting = "MAX"
        else:
            speed_setting = "MIN"
        measurement_command_buffer = ":MEAS:SCAL:POW:WAV? DEF,"+speed_setting

        PeakWavelength= (10E9)*float(self.instrument.query(measurement_command_buffer))/10.0 #for some reason it keeps returning numbers multiplied by an extra 10 so I am dividing by 10 to counter that 
        #docs for this are on page 152 of the manual
        return PeakWavelength
    

    def FindPower(self):
        """
        @brief Returns the power of the peak with the highest power
        @Note this function was written for a spectrum with one peak, it may misidentify a spectrum with multiple peaks

        @return TODO: I'm not sure what units power is in

        """
        measurement_command_buffer = ":MEASure:SCALar:POWer?"
        power = self.instrument.query(":MEASure:SCALar:POWer?")
        return power

