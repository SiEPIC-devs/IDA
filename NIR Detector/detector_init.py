import NIR_detector as detector

detector = detector.detector()
detector.update_parameter('detector_model', '81635A')

detector.update_parameter('detector_power_range','-20.000000dbm')

detector.update_parameter('detector_averaging_time','2ms')
detector.update_parameter('detector_decision_threshold', '')
detector.update_parameter('detector_ipAddress', "10.2.137.64")
detector.update_parameter('detector_ipPort', '5025')
detector.update_parameter('detector_slot', '1')
detector.update_parameter('detector_total_time', '4s')
detector.update_parameter('detector_sensor_current_wavelength', '1550.000')
detector.update_parameter('detector_inuse','0')
detector.update_parameter('measurement_inprogress','0')
detector.update_parameter('detector_init','0')
