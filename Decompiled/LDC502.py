# uncompyle6 version 3.9.2
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: ./LDC502.py
# Compiled at: 2023-05-18 09:34:20
# Size of source mod 2**32: 6917 bytes
import time, socket, pickle

class controller:

    def __init__(self):
        ldc_parameters = [
         'ldc_ipAddress', 
         'ldc_ipPort', 
         'ldc_temperature_setpoint', 
         'ldc_temperature_max', 
         'ldc_temperature_min', 
         'ldc_sensor_type', 
         'ldc_model_A', 
         'ldc_model_B', 
         'ldc_model_C', 
         'ldc_PID_P', 
         'ldc_PID_I', 
         'ldc_PID_D', 
         'ldc_onoff', 
         'ldc_init']
        default_values = [
         "0"] * len(ldc_parameters)
        try:
            import os, sys
            cwd = os.getcwd()
            main_path = os.path.split(cwd)
            main_path = main_path[0]
            self.dict = self.load_obj(os.path.join(main_path, "LDC Temperature Controller", "LDC"))
        except:
            self.dict = dict(zip(ldc_parameters, default_values))
            self.save_obj(self.dict, os.path.join(main_path, "LDC Temperature Controller", "LDC"))

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
            self.save_obj(self.dict, os.path.join(main_path, "LDC Temperature Controller", "LDC"))
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
        self.dict = self.load_obj(os.path.join(main_path, "LDC Temperature Controller", "LDC"))

    def open_port(self, **kwargs):
        self.socket_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        time.sleep(4)
        self.socket_connection.connect((self.dict["ldc_ipAddress"], int(self.dict["ldc_ipPort"])))
        self.socket_connection.settimeout(5)
        time.sleep(0.5)
        self.socket_connection.send(bytes("uloc1\n", "ascii"))
        self.socket_connection.recv(1024).decode("ascii")

    def close_port(self):
        self.socket_connection.close()

    def controller_init(self):
        self.reload_parameters()
        self.open_port()
        onstate = self.dict["ldc_onoff"]
        if int(self.dict["ldc_init"]) == 0:
            self.open_port()
            self.TEC_onoff(0)
            self.set_sensor_type(self.dict["ldc_sensor_type"])
            self.set_sensor_coefficients([self.dict["ldc_model_A"], self.dict["ldc_model_B"], self.dict["ldc_model_C"]])
            self.set_PID_coefficients([self.dict["ldc_PID_P"], self.dict["ldc_PID_I"], self.dict["ldc_PID_D"]])
            self.set_temperature(self.dict["ldc_temperature_setpoint"])
            self.update_parameter("ldc_init", str(1))
            self.TEC_onoff(onstate)

    def read_temperature(self):
        retry_count = 0
        while retry_count < 3:
            self.socket_connection.send(bytes("TTRD?\n", "ascii"))
            time.sleep(0.5)
            returned_data = self.socket_connection.recv(1024).decode("ascii")
            try:
                returned_data = returned_data.replace("\n", "")
                returned_data = returned_data.replace("\r", "")
                returned_data = float(returned_data)
                break
            except:
                retry_count += 1
                time.sleep(1)
                returned_data = 0.0

        return returned_data

    def read_onoff(self):
        retry_count = 0
        while retry_count < 3:
            self.socket_connection.send(bytes("TEON?\n", "ascii"))
            time.sleep(0.5)
            returned_data = self.socket_connection.recv(1024).decode("ascii")
            try:
                returned_data = returned_data.replace("\n", "")
                returned_data = returned_data.replace("\r", "")
                returned_data = int(returned_data)
                break
            except:
                retry_count += 1
                time.sleep(1)
                returned_data = 0

        self.update_parameter("ldc_onoff", str(int(returned_data)))
        return returned_data

    def set_temperature(self, temperature):
        if float(temperature) > float(self.dict["ldc_temperature_max"]):
            return -1
        if float(temperature) < float(self.dict["ldc_temperature_min"]):
            return -1
        self.socket_connection.send(bytes("TEMP " + str(temperature) + "\n", "ascii"))
        time.sleep(0.5)
        self.update_parameter("ldc_temperature_setpoint", str(temperature))
        return 0

    def get_setpoint(self):
        self.reload_parameters()
        return float(self.dict["ldc_temperature_setpoint"])

    def TEC_onoff(self, on_off):
        if on_off == True:
            self.socket_connection.send(bytes("TEON " + str(1) + "\n", "ascii"))
            time.sleep(0.5)
            self.dict["ldc_onoff"] = str(1)
            self.update_parameter("ldc_onoff", str(1))
        else:
            self.socket_connection.send(bytes("TEON " + str(0) + "\n", "ascii"))
            time.sleep(0.5)
            self.dict["ldc_onoff"] = str(0)
            self.update_parameter("ldc_onoff", str(0))

    def set_sensor_type(self, type):
        self.socket_connection.send(bytes("TMDN " + str(type) + "\n", "ascii"))
        time.sleep(0.5)
        self.update_parameter("ldc_sensor_type", str(type))

    def set_sensor_coefficients(self, coefficients):
        self.socket_connection.send(bytes("TSHA " + str(coefficients[0]) + "\n", "ascii"))
        time.sleep(0.5)
        self.socket_connection.send(bytes("TSHB " + str(coefficients[1]) + "\n", "ascii"))
        time.sleep(0.5)
        self.socket_connection.send(bytes("TSHC " + str(coefficients[2]) + "\n", "ascii"))
        time.sleep(0.5)

    def set_PID_coefficients(self, coefficients):
        self.socket_connection.send(bytes("TPGN " + str(coefficients[0]) + "\n", "ascii"))
        time.sleep(0.5)
        self.socket_connection.send(bytes("TIGN " + str(coefficients[1]) + "\n", "ascii"))
        time.sleep(0.5)
        self.socket_connection.send(bytes("TDGN " + str(coefficients[2]) + "\n", "ascii"))
        time.sleep(0.5)
