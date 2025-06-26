import LDC502 as temperature_controller

controller = temperature_controller.controller()
controller.update_parameter('ldc_ipAddress', "10.2.113.37")
controller.update_parameter('ldc_ipPort',"8886")
controller.update_parameter('ldc_temperature_setpoint', '25')
controller.update_parameter('ldc_temperature_max', '75')
controller.update_parameter('ldc_temperature_min', '15')
controller.update_parameter('ldc_sensor_type', '1')

controller.update_parameter('ldc_model_A', '1.204800E-03')
controller.update_parameter('ldc_model_B', '2.417000E-04')
controller.update_parameter('ldc_model_C', '1.482700E-07')

controller.update_parameter('ldc_PID_P', '-1.669519E+00')
controller.update_parameter('ldc_PID_I', '2.317650E-01')
controller.update_parameter('ldc_PID_D', '1.078678E+00')

controller.update_parameter('ldc_onoff', '1')


controller.update_parameter('ldc_init','0')
