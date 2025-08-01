Functional Purpose	Unified HAL Name	agilent_8163a.py	hp816x_instr.py	hp816x_N77Det_instr.py	N774xA.py	Description
Connect to laser/detector	connect	connect	connect	connect	connect	Establish connection to the instrument
Disconnect from device	disconnect	disconnect	disconnect	disconnect	disconnect	Close connection from the instrument
Set laser wavelength	set_wavelength	set_wavelength	setTLSWavelength			Set the output laser wavelength
Get laser wavelength	get_wavelength	get_wavelength	getTLSWavelength			Read the output laser wavelength
Set laser power	set_power	set_power	setTLSPower			Set the output laser power
Get laser power	get_power	get_power	getTLSPower			Read the output laser power
Enable laser output	enable_output	enable_output	setTLSState			Enable or disable laser emission
Get laser output state	get_output_state	get_output_state	getTLSState			Read current output enable state
Set sweep state	set_sweep_state	set_sweep_state	setTLSSweepState			Enable or disable laser sweep mode
Get sweep state	get_sweep_state	get_sweep_state	getTLSSweepState			Read whether sweep mode is active
Set sweep range	set_sweep_range	set_sweep_range	setSweepRange			Set start/stop range for sweep
Get sweep range	get_sweep_range	get_sweep_range	getSweepRange			Get configured sweep range
Set sweep speed	set_sweep_speed	set_sweep_speed	setSweepSpeed			Set wavelength sweep speed
Get sweep speed	get_sweep_speed	get_sweep_speed	getSweepSpeed			Get current sweep speed
Read detector power	read_power	read_power	readPWM	readPWM	readPower	Read optical power from detector
Set power unit	set_power_unit		setPWMPowerUnit	setPWMPowerUnit	setUnit	Set unit to dBm or Watts
Get power unit	get_power_unit		getPWMPowerUnit	getPWMPowerUnit	getUnit	Get power measurement unit
Set power range	set_power_range		setPWMPowerRange	setPWMPowerRange	setRange	Set fixed range of input power
Get power range	get_power_range		getPWMPowerRange	getPWMPowerRange	getRange	Get current power range
Enable autorange	enable_autorange		setAutorange	setAutorange	setAutorange	Enable automatic range switching
Start logging	start_logging				setLoopRangeGainTriggerPWR	Start timed or triggered power logging
Stop logging	stop_logging				stopLogging	Stop ongoing power logging
