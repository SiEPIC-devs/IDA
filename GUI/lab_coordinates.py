# uncompyle6 version 3.9.2
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: /home/pi/Desktop/new GUI/File Import/lab_coordinates.py
# Compiled at: 2022-04-01 14:24:57
# Size of source mod 2**32: 13303 bytes
import numpy as np
from tinydb import TinyDB, Query
import sys

class coordinates:

    def __init__(self, file_directory='./', name='coordinates.json', read_file=False):
        self.path = file_directory
        self.device_db = TinyDB(name)
        self.device = Query()
        if read_file == True:
            self.device_db.truncate()
            self.read_file()

    def read_file(self):
        """
        Reads the file and extracts data from file

        To search:
        self.device_db.search(self.device.wavelength == '1550')

        To update:
        self.device_db.update({'coordinate': [21,232]}, self.device.wavlength == '1550') #what to update to --> which one to update
        """
        with open(self.path) as self.coordinate_file:
            print("Loading devices into database")
            print("This may take awhile")
            file_contents = self.coordinate_file.readlines()
            startingline = 0
            for line in file_contents:
                try:
                    linesplit = line.split(",")
                    int(linesplit[0])
                    int(linesplit[1])
                    break
                except:
                    startingline += 1

            print("Device coordinates start on line " + str(startingline))
            file_contents = file_contents[startingline:]
            print("Precentage complete")
            currentline = startingline
            number_of_devices = len(file_contents)
            bracket = 0
            number = 1
            for line in file_contents:
                try:
                    raw = line.split(",")
                    line = []
                    for i in raw:
                        line.append(i.replace(" ", ""))

                    if "\n" in line[-1]:
                        line[-1] = line[-1].strip("\n")
                    coordinate = [
                     int(line[0]), int(line[1]), 0]
                    polarization = line[2]
                    wavelength = line[3]
                    device_type = line[4]
                    device_name = "_".join(line[5:])
                    data = [
                     number, coordinate,
                     polarization, wavelength, device_type,
                     device_name]
                    param = ['number', 'coordinate', 'polarization', 'wavelength', 'type',
                     'devicename']
                    device = dict(zip(param, data))
                    self.device_db.insert(device)
                    number += 1
                    if (number - 1) / number_of_devices * 100 > bracket:
                        bracket += 10
                        print(str(round((number - 1) / number_of_devices * 100, 2)) + "%")
                    currentline += 1
                except Exception:
                    print("Problem reading coordinates on line: " + str(currentline))
                    print("Line contents")
                    print(line)
                    print("skipping")
                    currentline += 1

        file_contents = []
        self.coordinate_file.close()
        print("All devices has been uploaded to database")

    def listdevicenames(self):
        device_list = []
        database_entries = self.device_db.all()
        for device in database_entries:
            device_list.append(device["devicename"])

        return device_list

    def listselecteddevices(self, wavelength, polarization):
        database_entries = self.finddevicesbywavelength(wavelength)
        device_list_wavelength = []
        for device in database_entries:
            device_list_wavelength.append(device["devicename"])

        database_entries = self.finddevicesbypolarization(polarization)
        device_list_polarization = []
        for device in database_entries:
            device_list_polarization.append(device["devicename"])

        if wavelength == "all":
            if polarization == "all":
                return self.listdevicenames()
        if wavelength == "all":
            device_list_wavelength = device_list_polarization
        if polarization == "all":
            device_list_polarization = device_list_wavelength
        return list(set(device_list_wavelength) & set(device_list_polarization))

    def listdeviceparam(self, parameter):
        device_list = []
        database_entries = self.device_db.all()
        for device in database_entries:
            device_list.append(device[str(parameter)])

        return device_list

    def finddevicesbywavelength(self, string):
        find = Query()
        devices = self.device_db.search(find.wavelength == string)
        return devices

    def finddevicesbypolarization(self, string):
        find = Query()
        devices = self.device_db.search(find.polarization == string)
        return devices

    def finddevicenumber(self, string):
        find = Query()
        device = self.device_db.search(find.devicename == string)
        numbers = []
        for i in device:
            numbers.append(int(i["number"]))

        return numbers

    def finddevicename(self, number):
        find = Query()
        device = self.device_db.search(find.number == number)
        device = device[0]
        return device["devicename"]

    def apply_transform(self, device_numbers, xy_motor1, xy_motor2, xy_motor3):
        """
        given the device number of 3 alignment devices

        param: device_numbers --> int respresenting 3 alignement devices, as stored in the mini db
        param: xy_motorN --> 3 lists containing the coordinates of the motor at 3 positions
        """
        transform_tries = 0
        while 1:
            xy_gds1 = np.array(self.device_db.get(self.device.number == device_numbers[0])["coordinate"])
            xy_gds2 = np.array(self.device_db.get(self.device.number == device_numbers[1])["coordinate"])
            xy_gds3 = np.array(self.device_db.get(self.device.number == device_numbers[2])["coordinate"])
            row1 = [
             xy_gds1[0], xy_gds1[1], xy_gds1[2], 0, 0, 0, 0, 0, 0, 1, 0, 0]
            row2 = [0, 0, 0, xy_gds1[0], xy_gds1[1], xy_gds1[2], 0, 0, 0, 0, 1, 0]
            row3 = [0, 0, 0, 0, 0, 0, xy_gds1[0], xy_gds1[1], xy_gds1[2], 0, 0, 1]
            row4 = [xy_gds2[0], xy_gds2[1], xy_gds2[2], 0, 0, 0, 0, 0, 0, 1, 0, 0]
            row5 = [0, 0, 0, xy_gds2[0], xy_gds2[1], xy_gds2[2], 0, 0, 0, 0, 1, 0]
            row6 = [0, 0, 0, 0, 0, 0, xy_gds2[0], xy_gds2[1], xy_gds2[2], 0, 0, 1]
            row7 = [xy_gds3[0], xy_gds3[1], xy_gds3[2], 0, 0, 0, 0, 0, 0, 1, 0, 0]
            row8 = [0, 0, 0, xy_gds3[0], xy_gds3[1], xy_gds3[2], 0, 0, 0, 0, 1, 0]
            row9 = [0, 0, 0, 0, 0, 0, xy_gds3[0], xy_gds3[1], xy_gds3[2], 0, 0, 1]
            A = np.array([row1, row2, row3, row4, row5, row6, row7, row8, row9])
            aug = np.array([xy_motor1[0], xy_motor1[1], xy_motor1[2], xy_motor2[0], xy_motor2[1], xy_motor2[2], xy_motor3[0], xy_motor3[1], xy_motor3[2]])
            solution = np.linalg.lstsq(A, aug, rcond=None)[0]
            transformation_matrix = solution[:9]
            transformation_matrix = transformation_matrix.reshape([3, 3])
            displacement_vector = solution[9:]
            large_error = 0
            xy_motor1_calculted = (np.matmul(transformation_matrix, xy_gds1) + displacement_vector).tolist()
            xy_motor2_calculted = (np.matmul(transformation_matrix, xy_gds2) + displacement_vector).tolist()
            xy_motor3_calculted = (np.matmul(transformation_matrix, xy_gds3) + displacement_vector).tolist()
            if abs(xy_motor1[0] - xy_motor1_calculted[0]) > 5:
                large_error = 1
            if abs(xy_motor1[1] - xy_motor1_calculted[1]) > 5:
                large_error = 1
            if abs(xy_motor1[2] - xy_motor1_calculted[2]) > 15:
                large_error = 1
            if abs(xy_motor2[0] - xy_motor2_calculted[0]) > 5:
                large_error = 1
            if abs(xy_motor2[1] - xy_motor2_calculted[1]) > 5:
                large_error = 1
            if abs(xy_motor2[2] - xy_motor2_calculted[2]) > 15:
                large_error = 1
            if abs(xy_motor3[0] - xy_motor3_calculted[0]) > 5:
                large_error = 1
            if abs(xy_motor3[1] - xy_motor3_calculted[1]) > 5:
                large_error = 1
            if abs(xy_motor3[2] - xy_motor3_calculted[2]) > 15:
                large_error = 1
            if large_error == 0:
                print("Transform matrix" + str(transformation_matrix))
                print("Displacement vector" + str(displacement_vector))
                print("Original and transformed alignment marks")
                print("mark 1: " + str(xy_motor1))
                print("mark 1 calculated: " + str(xy_motor1_calculted))
                print("mark 1 error: [" + str(xy_motor1[0] - xy_motor1_calculted[0]) + "," + str(xy_motor1[1] - xy_motor1_calculted[1]) + "," + str(xy_motor1[2] - xy_motor1_calculted[2]) + "]")
                print("mark 2: " + str(xy_motor2))
                print("mark 2 calculated: " + str(xy_motor2_calculted))
                print("mark 2 error: [" + str(xy_motor2[0] - xy_motor2_calculted[0]) + "," + str(xy_motor2[1] - xy_motor2_calculted[1]) + "," + str(xy_motor2[2] - xy_motor2_calculted[2]) + "]")
                print("mark 3: " + str(xy_motor3))
                print("mark 3 calculated: " + str(xy_motor3_calculted))
                print("mark 3 error: [" + str(xy_motor3[0] - xy_motor3_calculted[0]) + "," + str(xy_motor3[1] - xy_motor3_calculted[1]) + "," + str(xy_motor3[2] - xy_motor3_calculted[2]) + "]")
            else:
                if transform_tries > 40:
                    print("out of retries")
                    print("Transform matrix" + str(transformation_matrix))
                    print("Displacement vector" + str(displacement_vector))
                    print("Original and transformed alignment marks")
                    print("mark 1: " + str(xy_motor1))
                    print("mark 1 calculated: " + str(xy_motor1_calculted))
                    print("mark 1 error: [" + str(xy_motor1[0] - xy_motor1_calculted[0]) + "," + str(xy_motor1[1] - xy_motor1_calculted[1]) + "," + str(xy_motor1[2] - xy_motor1_calculted[2]) + "]")
                    print("mark 2: " + str(xy_motor2))
                    print("mark 2 calculated: " + str(xy_motor2_calculted))
                    print("mark 2 error: [" + str(xy_motor2[0] - xy_motor2_calculted[0]) + "," + str(xy_motor2[1] - xy_motor2_calculted[1]) + "," + str(xy_motor2[2] - xy_motor2_calculted[2]) + "]")
                    print("mark 3: " + str(xy_motor3))
                    print("mark 3 calculated: " + str(xy_motor3_calculted))
                    print("mark 3 error: [" + str(xy_motor3[0] - xy_motor3_calculted[0]) + "," + str(xy_motor3[1] - xy_motor3_calculted[1]) + "," + str(xy_motor3[2] - xy_motor3_calculted[2]) + "]")
                    return 1
                transform_tries = transform_tries + 1
                continue
            data = self.device_db.all()
            print("Transforming devices this might take awhile")
            total_length = len(data)
            bracket = 0
            current_complete = 0
            updated = []
            for item in data:
                item["coordinate"] = (np.matmul(transformation_matrix, np.array(item["coordinate"])) + displacement_vector).tolist()
                updated.append(item)

            self.device_db.truncate()
            for item in updated:
                self.device_db.insert(item)
                current_complete += 1
                percent = current_complete / total_length * 100
                if percent > bracket:
                    bracket += 10
                    print(str(round(percent, 0)) + "%")

            return 0
