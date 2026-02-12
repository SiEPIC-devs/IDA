import comtypes.client as cc
from comtypes import COMError
cc.GetModule('Ke26XXA.dll')
import comtypes.gen.Ke26XXALib as Ke26XXALib
from ctypes import byref, pointer, c_long, c_float, c_int32, cast, c_char_p, c_char

class Ke26XXA(object):
    name = 'Keithley 26xxA'
        
    def __init__(self):
        self.inst = cc.CreateObject('Ke26XXA.Ke26XXA')
        
    def connect(self, visaAddr):
        self.inst.Initialize(visaAddr, False, False, '')
    
    # Sets the voltage for a channel. If cvMode is true sets channel automatically to constant voltage mode
    def setVoltage(self, chan, v, cvMode=True):
        if cvMode:
            self.setMode(chan,'cv')
        try:
            self.inst.Source.Voltage.Level[chan]=v
        except COMError:
            raise Ke26XXAException(self.checkError()[1])
        
    def getVoltage(self, chan):
        try:
            res = self.inst.Measurement.Voltage.Measure(chan)
            #res = self.inst.Source.Voltage.Level[chan]          This is the old statement
        except COMError:
            raise Ke26XXAException(self.checkError()[1])
        return res
    
    # Sets the current for a channel. If ccMode is true sets channel automatically to constant current mode
    def setCurrent(self, chan, c, ccMode=True):
        if ccMode:
            self.setMode(chan,'cc')
        try:
            self.inst.Source.Current.Level[chan]=c        
        except COMError:
            raise Ke26XXAException(self.checkError()[1])
        
    def getCurrent(self, chan):
        try:
            res = self.inst.Measurement.Current.Measure(chan)
        except COMError:
            raise Ke26XXAException(self.checkError()[1])
        return res
        
    def setVoltageAutorange(self, chan, val):
        try:
            self.inst.Source.Voltage.AutoRangeEnabled[chan] = val
        except COMError:
            raise Ke26XXAException(self.checkError()[1])
        
    def setCurrentAutorange(self, chan, val):
        try:
            self.inst.Source.Current.AutoRangeEnabled[chan] = val
        except COMError:
            raise Ke26XXAException(self.checkError()[1])
    
    # current range - options are: 100nA - 1uA - 10uA - 100uA - 1mA - 10mA- 100mA - 1A - 3A        
    def setCurrentMeasurementRange(self, chan, val):
        try:
            self.inst.Measurement.Current.Range[chan] = val
        except COMError:
            raise Ke26XXAException(self.checkError()[1])
            
    def setVoltageLimit(self, chan, val):
        try:
            self.inst.Source.Voltage.Limit[chan] = val
        except COMError:
            raise Ke26XXAException(self.checkError()[1])
            
    def setCurrentLimit(self, chan, val):
        try:
            self.inst.Source.Current.Limit[chan] = val
        except COMError:
            raise Ke26XXAException(self.checkError()[1])

    # Sets mode to be constant current ('cc') or constant voltage ('cv')        
    def setMode(self,chan,mode):
        # In COM driver, cc and cv are flipped
        modeDict = {'cv':1,\
                    'cc':0}
        try:
            self.inst.Source.Function[chan]=modeDict[mode]
        except COMError:
            raise Ke26XXAException(self.checkError()[1])
        except KeyError:
            raise Ke26XXAException('Mode must be either constant current (cc) or constant voltage (cv).')
     
    #set the auto zero function of the DAC  smua.AUTOZERO_OFF|smua.AUTOZERO_AUTO|smua.AUTOZERO_ONCE 
    def setAutoZeroMode(self, chan, mode):
        # In COM driver, cc and cv are flipped
        modeDict = {'off':0,\
                    'once':1,\
                    'auto':2}
        try:
            self.inst.Measurement.AutoZero[chan]=modeDict[mode]
        except COMError:
            raise Ke26XXAException(self.checkError()[1])
        except KeyError:
            raise Ke26XXAException('Mode must be either off, once, or auto.')

    # Sets the integration time in number of power line cycles. Range 0.001 to 25 
    def setNPLC(self, chan, val):
        try:
            self.inst.Measurement.NPLC[chan] = val
        except COMError:
            raise Ke26XXAException(self.checkError()[1])
    
    def outputEnable(self, chan, enable):
        try:
            self.inst.Source.OutputEnabled[chan] = enable
        except COMError:
            raise Ke26XXAException(self.checkError()[1])
    
    def checkError(self):        
        instErr, errMsg = self.inst.Utility.ErrorQuery()
        return instErr, errMsg
        
    def queryErrorStatus(self,val):
        self.inst.DriverOperation.QueryInstrumentStatus=val
        
class Ke26XXAException(Exception):
    pass