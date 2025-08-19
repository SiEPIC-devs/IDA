#
# Copyright 2015, Michael Caverley
#

from ctypes import *
import numpy as np
from itertools import repeat
import hp816x_instr
import math


class hp816x_Oband_N77Det(hp816x_instr.hp816x):
    name = "hp816x Oband with N77 Detector"
    numPWMSlots = 11
    maxPWMPoints = 100000

    def connect(self, visaAddr, n77DetAddr, reset=0, forceTrans=1, autoErrorCheck=1):
        super(hp816x_Oband_N77Det, self).connect(
            visaAddr, reset, forceTrans, autoErrorCheck
        )
        print("[self.SlotInfo: %s]" % ", ".join(map(str, self.slotInfo)))
        print(
            "[pwmSlotIndex: %s]" % ", ".join(map(str, self.pwmSlotIndex))
        )  #### HERE - THIS IS THE IMPORTANT ONE WHICH SHOULD BECOME [0,1,2,3,4,5] - Index of each detector
        print("[pwmSlotMap: %s]" % ", ".join(map(str, self.pwmSlotMap)))
        self.hN77Det = c_int32()

        queryID = 1
        # The instrument ignores this value.

        res_N77 = self.hp816x_init(
            n77DetAddr.encode("utf-8"), queryID, reset, byref(self.hN77Det)
        )
        self.checkErrorN77(res_N77)

        print("Connected to N7744 detector")
        self.registerMainframe(self.hN77Det)
        self.N77SlotInfo = self.getN77SlotInfo()
        # Keep mainframe slot info ### HERE ### This function is below... Lets try to get that. So its an aaray of pointers
        self.N77pwmSlotIndex, self.N77pwmSlotMap = self.enumerateN77PWMSlots()
        ### HERE ### This function is below... Lets try to get that.
        self.N77activeSlotIndex = self.N77pwmSlotIndex
        ### HERE ### This seems to be contradicting with what im seeing below - sort of confusing
        print("[activeSlotIndex: %s]" % ", ".join(map(str, self.N77activeSlotIndex)))

        self.plotcolors = ["b", "g", "r", "k", "y", "c", "m", "b", "g", "r", "k", "y"]
        # self.plotnames = ['HP8164 Slot 1 Det 1', 'HP8164 Slot 1 Det 1', 'N7744C Slot 1 Det 2', 'N7744C Slot 2 Det 1', 'N7744C Slot 3 Det 1', 'N7744C Slot 4 Det 1']
        self.plotnames = [
            "HP8164 Slot 1 Det 1",
            "HP8164 Slot 1 Det 2",
            "HP8164 Slot 2 Det 1",
            "HP8164 Slot 2 Det 2",
            "HP8164 Slot 3 Det 1",
            "HP8164 Slot 3 Det 2",
            "HP8164 Slot 4 Det 1",
            "HP8164 Slot 4 Det 2",
            "N7744C Slot 1 Det 2",
            "N7744C Slot 2 Det 1",
            "N7744C Slot 3 Det 1",
            "N7744C Slot 4 Det 1",
        ]

        self.modN77pwmSlotIndex = self.pwmSlotIndex + self.N77pwmSlotIndex
        self.modactiveSlotIndex = self.pwmSlotIndex + self.N77activeSlotIndex
        ### HERE ### This seems to be contradicting with what im seeing below - sort of confusing
        print("[modactiveSlotIndex: %s]" % ", ".join(map(str, self.modactiveSlotIndex)))

        return

    def disconnect(self):
        super().disconnect()
        self.unregisterMainframe(self.hN77Det)

        res_N77 = self.hp816x_close(self.hN77Det)
        self.checkErrorN77(res_N77)

    def getN77SlotInfo(
        self,
    ):  ### NEED to know what this guy is doing here a bit moree clearer ###
        slotInfoArr = (c_int32 * self.numPWMSlots)()
        slotInfoArrPtr = cast(slotInfoArr, POINTER(c_int32))
        res_N77 = self.hp816x_getSlotInformation_Q(
            self.hN77Det, self.numPWMSlots, slotInfoArrPtr
        )  ## This is hardcoded in the driver :'(
        self.checkErrorN77(res_N77)
        # slotInfoArrPtr[self.numPWMSlots - 5] = 0 # Manually added
        # slotInfoArrPtr[self.numPWMSlots - 1] = 1 # Manually added
        # print (slotInfoArrPtr[:self.numPWMSlots])
        return slotInfoArrPtr[
            : self.numPWMSlots
        ]  # I guess this returns the pointer array from [0:5] - 6 spots of it as a list

    #    def enumerateN77PWMSlots(self): ### OLD ONE ###
    #        pwmSlotIndex = list();
    #        pwmSlotMap = list();
    #        ii = 1;
    #        for slot in self.N77SlotInfo:
    #            if slot == self.hp816x_SINGLE_SENSOR:
    #                pwmSlotIndex.append(ii);
    #                pwmSlotMap.append((ii,0));
    #                ii += 1;
    #            elif slot == self.hp816x_DUAL_SENSOR:
    #                pwmSlotIndex.append(ii);
    #                pwmSlotMap.append((ii,0));
    #                ii += 1;
    #                pwmSlotIndex.append(ii);
    #                pwmSlotMap.append((ii,1));
    #                ii += 1;
    #        return (pwmSlotIndex,pwmSlotMap)

    def enumerateN77PWMSlots(self):
        """Returns two lists:
        pwmSlotIndex - List containing index for each detector
        pwmSlotMap - List of tuples containing the index and detector number for each detector
        """
        pwmSlotIndex = list()
        pwmSlotMap = list()
        slotIndex = 0
        # Slot index
        enumeratedIndex = len(
            self.pwmSlotMap
        )  # previous value=2. Modified PWM index to start from the length of available mainframe slots
        print(
            "[self.N77SlotInfo: %s]" % ", ".join(map(str, self.N77SlotInfo))
        )  ### HERE ### - Good to know what this thing is doing actually - 6 iterations or 4 iterations??
        for slot in self.N77SlotInfo:  # This should have 0:5 iterations??
            if slot == self.hp816x_SINGLE_SENSOR:  # 1
                pwmSlotIndex.append(enumeratedIndex)
                pwmSlotMap.append((slotIndex, 0))
                # slotIndex += 1;
                enumeratedIndex += 1
            elif slot == self.hp816x_DUAL_SENSOR:  # 2
                pwmSlotIndex.append(enumeratedIndex)
                pwmSlotMap.append((slotIndex, 0))
                # slotIndex += 1;
                enumeratedIndex += 1
                pwmSlotIndex.append(enumeratedIndex)
                pwmSlotMap.append((slotIndex, 1))
                # slotIndex += 1;
                enumeratedIndex += 1
            slotIndex += 1

        print(
            "[N77pwmSlotIndex: %s]" % ", ".join(map(str, pwmSlotIndex))
        )  #### HERE - THIS IS THE IMPORTANT ONE WHICH SHOULD BECOME [0,1,2,3,4,5] - Index of each detector
        print("[N77pwmSlotMap: %s]" % ", ".join(map(str, pwmSlotMap)))
        return (pwmSlotIndex, pwmSlotMap)

    ### HERE ### - # Slot info
    # hp816x_UNDEF = 0;
    # hp816x_SINGLE_SENSOR = 1;
    # hp816x_DUAL_SENSOR = 2;
    # hp816x_FIXED_SINGLE_SOURCE = 3;
    # hp816x_FIXED_DUAL_SOURCE = 4;
    # hp816x_TUNABLE_SOURCE = 5;
    # hp816x_SUCCESS = 0;

    def getNumSweepChannels(self):
        return len(self.N77pwmSlotIndex)

    def N77setAutorangeAll(self):
        """Turns on autorange for all detectors and sets units to dBm"""

        for slotinfo in self.N77pwmSlotMap:
            detslot = slotinfo[0]
            detchan = slotinfo[1]

            self.N77setPWMPowerUnit(detslot, detchan, "dBm")
            self.N77setPWMPowerRange(detslot, detchan, rangeMode="auto")

    def N77setRangeParams(self, chan, initialRange, rangeDecrement, reset=0):
        res_N77 = self.hp816x_setInitialRangeParams(
            self.hN77Det, chan, reset, initialRange, rangeDecrement
        )
        self.checkErrorN77(res_N77)
        return

    def N77setPWMPowerUnit(self, slot, chan, unit):
        res_N77 = self.hp816x_set_PWM_powerUnit(
            self.hN77Det, slot, chan, self.sweepUnitDict[unit]
        )
        self.checkErrorN77(res_N77)

    def N77setPWMPowerRange(self, slot, chan, rangeMode="auto", range=0):
        res_N77 = self.hp816x_set_PWM_powerRange(
            self.hN77Det, slot, chan, self.rangeModeDict[rangeMode], range
        )
        self.checkErrorN77(res_N77)

    def checkInstrumentErrorN77(self):
        """Reads error messages from the instrument"""
        ERROR_MSG_BUFFER_SIZE = 256
        instErr = c_int32()
        c_errMsg = (c_char * ERROR_MSG_BUFFER_SIZE)()
        c_errMsgPtr = cast(c_errMsg, c_char_p)
        self.hp816x_error_query(self.hN77Det, byref(instErr), c_errMsgPtr)
        return instErr.value, c_errMsg.value

    def checkErrorN77(self, errStatus):
        ERROR_MSG_BUFFER_SIZE = 256
        if errStatus < self.hp816x_SUCCESS:
            if errStatus == self.hp816x_INSTR_ERROR_DETECTED:
                instErr, instErrMsg = self.checkInstrumentError()
                raise InstrumentError("Error " + str(instErr) + ": " + instErrMsg)
            else:
                c_errMsg = (c_char * ERROR_MSG_BUFFER_SIZE)()
                c_errMsgPtr = cast(c_errMsg, c_char_p)

                self.hp816x_error_message(self.hN77Det, errStatus, c_errMsgPtr)
                raise InstrumentError(c_errMsg.value)
        return 0

    def getLambdaScanResult(self, chan, useClipping, clipLimit, numPts):
        wavelengthArr = np.zeros(int(numPts))
        powerArr = np.zeros(int(numPts))
        ### HERE ### This is where our array is made
        res_N77 = self.hp816x_getLambdaScanResult(
            self.hN77Det, chan, useClipping, clipLimit, powerArr, wavelengthArr
        )  ### This is hardcoded in the driver :'(
        self.checkErrorN77(res_N77)
        return wavelengthArr, powerArr
        ### HERE ### This is where our array is made

    def N77readPWM(self, slot, chan):
        """read a single wavelength"""
        powerVal = c_double()
        res_N77 = self.hp816x_PWM_readValue(self.hN77Det, slot, chan, byref(powerVal))
        # Check for out of range error
        if res_N77 == self.hp816x_INSTR_ERROR_DETECTED:
            instErr, instErrMsg = self.checkInstrumentError()
            if instErr == -231 or instErr == -261:
                return self.sweepClipLimit  # Assumes unit is in dB
            else:
                raise InstrumentError("Error " + str(instErr) + ": " + instErrMsg)
        self.checkError(res_N77)
        return float(powerVal.value)

    def sweep(self):
        """Performs a wavelength sweep"""

        # Convert values from string representation to integers for the driver
        unitNum = self.sweepUnitDict[self.sweepUnit]
        outputNum = self.laserOutputDict[self.sweepLaserOutput]
        numScans = self.sweepNumScansDict[self.sweepNumScans]

        numChan = len(self.modN77pwmSlotIndex)
        ### HERE ### These look like they are not decided by us.. Lets see. This must become [0,1,2,3,4,5]
        numActiveChan = len(
            self.modactiveSlotIndex
        )  # Number of active channels  ### HERE ### These look like they are not decided by us.. Lets see. This must become [0,1,2,3,4,5]

        # Total number of points in sweep
        numTotalPoints = int(
            round((self.sweepStopWvl - self.sweepStartWvl) / self.sweepStepWvl + 1)
        )
        ### HERE ### This is decided by us == [(1550+5)-(1550-5)]/(8pm+1)

        # The laser reserves 100 pm of spectrum which takes away from the maximum number of datapoints per scan
        # Also, we will reserve another 100 datapoints as an extra buffer.
        # maxPWMPointsTrunc = int(round(self.maxPWMPoints-100e-12/self.sweepStepWvl-1));
        maxPWMPointsTrunc = (
            int(round(self.maxPWMPoints - math.ceil(100e-12 / self.sweepStepWvl))) - 100
        )
        numFullScans = int(numTotalPoints // maxPWMPointsTrunc)
        numRemainingPts = numTotalPoints % maxPWMPointsTrunc

        stitchNumber = numFullScans + 1

        print(
            "Total number of datapoints: %d" % numTotalPoints
        )  ### HERE ### This is decided by us
        print("Stitch number: %d" % stitchNumber)

        # Create a list of the number of points per stitch
        numPointsLst = list()

        for x in repeat(maxPWMPointsTrunc, numFullScans):
            numPointsLst.append(int(x))

        numPointsLst.append(int(round(numRemainingPts)))

        startWvlLst = list()
        stopWvlLst = list()

        # Create a list of the start and stop wavelengths per stitch
        pointsAccum = 0
        for points in numPointsLst:
            startWvlLst.append(self.sweepStartWvl + pointsAccum * self.sweepStepWvl)
            stopWvlLst.append(
                self.sweepStartWvl + (pointsAccum + points - 1) * self.sweepStepWvl
            )
            pointsAccum += points

        # Set sweep speed
        self.setSweepSpeed(self.sweepSpeed)

        wavelengthArrPWM = np.zeros(int(numTotalPoints))
        powerArrPWM = np.zeros(
            (int(numTotalPoints), numActiveChan)
        )  ### HERE ### powerArrPWM - this array has to be initialized for 6 channels
        print("numActiveChan: %d" % numActiveChan)  ### HERE ### So this has to be 6

        pointsAccum = 0
        # Loop over all the stitches
        for points, startWvl, stopWvl in zip(numPointsLst, startWvlLst, stopWvlLst):
            print("Sweeping from %g nm to %g nm" % (startWvl * 1e9, stopWvl * 1e9))
            # If the start or end wavelength is not a multiple of 1 pm, the laser will sometimes choose the wrong start
            # or end wavelength for doing the sweep. To fix this, we will set the sweep start wavelength to the
            # nearest multiple of 1 pm below the start wavelength and the nearest multiple above the end wavelength.
            # After the sweep is completed, the desired wavelength range is extracted from the results.
            startWvlAdjusted = startWvl
            stopWvlAdjusted = stopWvl
            if startWvl * 1e12 - int(startWvl * 1e12) > 0:
                startWvlAdjusted = math.floor(startWvl * 1e12) / 1e12
            if stopWvl * 1e12 - int(stopWvl * 1e12) > 0:
                stopWvlAdjusted = math.ceil(stopWvl * 1e12) / 1e12

            # Format the start and dtop wvl to 13 digits of accuracy (otherwise the driver will sweep the wrong range)
            startWvlAdjusted = float("%.13f" % (startWvlAdjusted))
            stopWvlAdjusted = float("%.13f" % (stopWvlAdjusted))

            c_numPts = c_uint32()
            c_numChanRet = c_uint32()
            ### The below function is using numChan which must become len([0,1,2,3,4,5]) = 6
            res_N77 = self.hp816x_prepareMfLambdaScan(
                self.hDriver,
                unitNum,
                self.sweepPower,
                outputNum,
                numScans,
                numChan,
                startWvlAdjusted,
                stopWvlAdjusted,
                self.sweepStepWvl,
                byref(c_numPts),
                byref(c_numChanRet),
            )
            ## This is hardcoded in the driver :'(

            self.checkError(res_N77)
            numPts = int(c_numPts.value)

            # Set range params
            for (
                ii
            ) in self.modactiveSlotIndex:  ### HERE ### This must become [0,1,2,3,4,5]
                self.N77setRangeParams(
                    ii, self.sweepInitialRange, self.sweepRangeDecrement
                )

            # for ii in self.pwmSlotIndex:
            # self.setRangeParams(ii, self.sweepInitialRange, self.sweepRangeDecrement);

            # This value is unused since getLambdaScanResult returns the wavelength anyways
            c_wavelengthArr = (c_double * int(numPts))()
            c_wavelengthArrPtr = cast(c_wavelengthArr, POINTER(c_double))

            # Perform the sweep
            res_N77 = self.hp816x_executeMfLambdaScan(self.hDriver, c_wavelengthArrPtr)
            self.checkError(res_N77)

            wavelengthArrTemp = np.zeros(int(numPts))
            for zeroIdx, chanIdx in enumerate(
                self.modactiveSlotIndex
            ):  ### HERE ### This must become [0,1,2,3,4,5]
                # print (zeroIdx,chanIdx)
                # zeroIdx is the index starting from zero which is used to add the values to the power array
                # chanIdx is the channel index used by the mainframe
                # Get power values and wavelength values from the laser/detector
                wavelengthArrTemp, powerArrTemp = self.getLambdaScanResult(
                    chanIdx, self.sweepUseClipping, self.sweepClipLimit, numPts
                )  ### HERE ### ## This is hardcoded in the driver :'(
                # The driver sometimes doesn't return the correct starting wavelength for a sweep
                # We will search the returned wavelength results to see the index at which
                # the deired wavelength starts at, and take values starting from there
                wavelengthStartIdx = self.findClosestValIdx(wavelengthArrTemp, startWvl)
                wavelengthStopIdx = self.findClosestValIdx(wavelengthArrTemp, stopWvl)
                wavelengthArrTemp = wavelengthArrTemp[
                    wavelengthStartIdx : wavelengthStopIdx + 1
                ]
                powerArrTemp = powerArrTemp[
                    wavelengthStartIdx : wavelengthStopIdx + 1
                ]  ### HERE ###
                powerArrPWM[pointsAccum : pointsAccum + points, zeroIdx] = powerArrTemp
                ### HERE ###
            wavelengthArrPWM[pointsAccum : pointsAccum + points] = wavelengthArrTemp
            pointsAccum += points

        return (
            wavelengthArrPWM,
            powerArrPWM,
        )  ### HERE ### powerArrPWM - this array has to hold 6 arrays for 6 channels


class InstrumentError(Exception):
    pass


## CONCLUSION - If i can get the code to detect the extra two channels, then it will take care of the rest!
