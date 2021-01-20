import cb
import time
import struct

class TindeqProgressor(object):
	"""
    Uses Bluetooth 4 (LE) to communicate. 
    
    Send bytes to write UUID to control the device. Current weight or
    rate of force is reported on the notify UUID, so use callbacks to do 
    something when you receive info on this UUID.
    
    Command bytes are:
        0x64 - Tare the scale
        0x65 - Start measuring weight
        0x66 - Stop measuring weight
        0x67 - Start measure peak RFD
        0x68 - Start measure peak RFD series
        0x69 - Add calibration point
        0x6a - Save calibration
        0x6b - Get app version
        0x6c - Get error information
        0x6d - Clear error information               
        0x6e - Put cell to sleep. Device will disconnect and will only
               wake on button press.
        0x6f - Get battery voltage
	"""
	response_codes = {
	    'cmd_resp': 0, 'weight_measure': 1, 'low_pwr': 2
	}
	
	service_uuid = '7e4e1701-1ea6-40c9-9dcc-13d34ffead57'
	write_uuid = '7e4e1703-1ea6-40c9-9dcc-13d34ffead57'
	notify_uuid = '7e4e1702-1ea6-40c9-9dcc-13d34ffead57'
	
	def __init__(self, parent):
		"""
		Parent is an owning class that implements a callback for weight logging events.
		
		This class should implement `log_force_sample(timestamp, value)`.
		"""
		self.peripheral = None
		self.write_characteristic = None
		self.read_characteristic = None
		self.info_struct = struct.Struct('<bb')
		self.data_struct = struct.Struct('<fl')
		self.ready = False
		self.parent = parent
	
	def log(self, msg):
	    # ask for forgiveness, not permission
	    try:
	    	# first attempt to log to msgbox in parent if there
	        self.parent.msgbox.text = msg
	    except:
	    	# if this fails, print to screen
	        print(msg)
	
	def save_value(self, kind, now, val):
	    if kind == 1:
	        log_fn = getattr(self.parent, 'log_force_sample', None)
	    elif kind == 2:
	        log_fn = getattr(self.parent, 'log_rfd_sample', None)
	    if log_fn:
	        log_fn(now, val)
	
	def did_discover_peripheral(self, p):
		'''called whenever a new peripheral is found'''
		if (p.name and 'progressor' in p.name.lower()
		    and self.peripheral is None):
		    	self.peripheral = p
		    	self.log('connecting to progressor')
		    	cb.connect_peripheral(p)
		    	
	def did_connect_peripheral(self, p):
		self.log('connected; discovering services')
		p.discover_services()
		
	def did_fail_to_connect_peripheral(self, p, err):
		self.log('failed to connect: %s' % (err,))
		
	def did_disconnect_peripheral(self, p, err):
		self.log('disconnected: %s' % (err,))
		self.peripheral = None
		
	def did_discover_services(self, p, err):
		for s in p.services:
			# 2 services, the tindeq one and the firmware update
			if s.uuid.lower() == self.service_uuid:
				self.log('found service')
				p.discover_characteristics(s)
				
	def did_discover_characteristics(self, s, err):
		for c in s.characteristics:
			if c.uuid.lower() == self.notify_uuid:
				self.log('found notify')
				self.read_characteristic = c
			elif c.uuid.lower() == self.write_uuid:
			    self.log('found write')
			    self.write_characteristic = c
		# notify parent that we can start
		self.ready = True
            
	def did_update_value(self, c, err):
		'''called whenever a notify service sends a msg'''
		self.last_val = c.value
		kind, size= self.info_struct.unpack(c.value[:2])
		if kind == self.response_codes['weight_measure']:
		    # data sent in bulk packets
		    for weight, useconds in self.data_struct.iter_unpack(c.value[2:]):
		        now = useconds/1.0e6
		        self.save_value(kind, now, weight)
		elif kind == self.response_codes['cmd_resp']:
			self.cmd_response(c.value)

	def cmd_response(self, value):
		try:
			if self.last_cmd == 'get_app':
				self.log(f"FW version : {value[2:].decode('utf-8')}")
			elif self.last_cmd == 'get_batt':
				vdd, = struct.unpack("<I", value[2:])
				self.log(f"Battery level = {vdd} [mV]")
				
		except Exception as err:
			self.log(err)

	def enable_notifications(self):
		if self.peripheral is None:
			return
		self.peripheral.set_notify_value(self.read_characteristic, True)
							
	def get_fw_info(self):
		if self.peripheral is None:
			return
			
		self.last_cmd = 'get_app'
		try:
			self.peripheral.write_characteristic_value(
				self.write_characteristic, self.pack(0x6b), False)
		except Exception as err:
			self.log('failed to get FW version: ' + str(err))
	
	def pack(self, cmd):
		return cmd.to_bytes(2, byteorder='little')
	
	def get_batt(self):
		if self.peripheral is None:
			return
			
		self.last_cmd = 'get_batt'
		try:
			self.peripheral.write_characteristic_value(
				self.write_characteristic, self.pack(0x6f), False)
		except Exception as err:
			self.log('failed to get FW version: ' + str(err))
			
	def tare(self):
		if self.peripheral is None:
			return
			
		try:
			self.peripheral.write_characteristic_value(
				self.write_characteristic,
				self.pack(0x64), True
			)
		except Exception as err:
			self.log('failed to tare scale: ' + str(err))
			
	def start_logging_weight(self):
		if self.peripheral is None:
			return
		# enable notifications
		try:
			self.peripheral.set_notify_value(
				self.read_characteristic, True
			)
			self.peripheral.write_characteristic_value(
				self.write_characteristic,
				self.pack(0x65), False
			)
		except Exception as err:
			self.log('failed to start test' + str(err))
			
	def start_rfd_test(self):
		if self.peripheral is None:
			return

		# disable notifications
		try:
			self.peripheral.set_notify_value(
				self.read_characteristic, False
			)
			self.peripheral.write_characteristic_value(
				self.write_characteristic,
				self.pack(0x67), False
			)
		except Exception as err:
			self.log('failed to start test' + str(err))
			  
	def end_logging_weight(self):
		if self.peripheral is None:
			return
		try:
			self.peripheral.set_notify_value(
				self.read_characteristic, False
			)
			self.peripheral.write_characteristic_value(
				self.write_characteristic,
				self.pack(0x66), True
			)
		except Exception as err:
			self.log('failed to start test' + str(err))
			
	def sleep(self):
		if self.peripheral is None:
			return
		self.peripheral.write_characteristic_value(
				self.write_characteristic,
				self.pack(0x6e), True
			)
		self.peripheral = None
		
if __name__ == '__main__':
	import numpy as np
	import matplotlib.pyplot as plt
	
	class Wrapper:
	    def __init__(self):
	        self.wsamples = []
	        self.rfdsamples=[]
	        self.times = []
	    def log_rfd_sample(self, now, sample):
	        self.rfdsamples.append(sample)
	    def log_force_sample(self, now, sample):
	        #print('WEIGHT: ', now, sample)
	        self.wsamples.append(sample)
	        self.times.append(now)
	        
	wrap = Wrapper()
	delegate = TindeqProgressor(wrap)    
	print('scanning for peripherals')
	cb.set_central_delegate(delegate)
	cb.scan_for_peripherals()
	
	while not delegate.ready:
	    time.sleep(3)
	delegate.enable_notifications()
	delegate.get_fw_info()
	time.sleep(0.5)
	delegate.get_batt()
	
	time.sleep(1)
	print('go')
	startT = time.time()
	delegate.start_logging_weight()
	try:
		while time.time() - startT < 5:
			pass		
	except KeyboardInterrupt:
		cb.reset()
	finally:
		delegate.end_logging_weight()
		cb.reset()
		delegate.sleep()
	time.sleep(0.5)
	
	print(f'mean = {np.mean(wrap.wsamples)}')
	mean = np.mean(wrap.wsamples)
	prec = 100*np.std(wrap.wsamples)/mean
	print(f'accuracy = {prec}%')
	plt.plot(wrap.times, wrap.wsamples)
	plt.show()
