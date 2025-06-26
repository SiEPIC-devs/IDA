import stage

stage = stage.stage()
stage.update_parameter('timeout', '0.30')
stage.update_parameter('baudrate', '38400')
stage.update_parameter('Stage_COM_port', '/dev/ttyUSB0')
stage.update_parameter('motor_velocity', '2000.0') #setting motor speed to 2 mm/s
stage.update_parameter('fr_zero_position','-0.5995')#position at zero angle
stage.update_parameter('fr_pivot_distance','-12.15391')#distance between the pivots
stage.update_parameter('max_y','20')
stage.update_parameter('max_x','20')
stage.update_parameter('max_z','20')
stage.update_parameter('min_y','-30400')
stage.update_parameter('min_x','-24940')
stage.update_parameter('min_z','-11110')
stage.update_parameter('automated_move_happened','1')
stage.open_port()
stage.emergency_stop()
stage.stage_init()
stage.stage_init_z()
stage.update_parameter('stage_inuse', '0')

