# Atlas Scientific code

import io         # used to create file streams
from io import open
import fcntl      # used to access I2C parameters like addresses

import time       # used for sleep delay and timestamps
import string     # helps parse strings
import sys


class AS_pH_I2C:
	#~ long_timeout = 1.5         	# the timeout needed to query readings and calibrations
	#~ short_timeout = .5         	# timeout for regular commands
	default_bus = 1         	# the default bus for I2C on the newer Raspberry Pis, certain older boards use bus 0
	default_address = 0x63    	# the default address for the sensor. Use i2cdetect -y 1 to check
	current_addr = default_address

	def __init__(self, address=default_address, bus=default_bus):
		# open two file streams, one for reading and one for writing
		# the specific I2C channel is selected with bus
		# it is usually 1, except for older revisions where its 0
		# wb and rb indicate binary read and write
		self.file_read = io.open("/dev/i2c-"+str(bus), "rb", buffering=0)
		self.file_write = io.open("/dev/i2c-"+str(bus), "wb", buffering=0)

		# initializes I2C to either a user specified or default address
		self.set_i2c_address(address)

	def set_i2c_address(self, addr):
		# set the I2C communications to the slave specified by the address
		# The commands for I2C dev using the ioctl functions are specified in
		# the i2c-dev.h file from i2c-tools
		I2C_SLAVE = 0x703
		fcntl.ioctl(self.file_read, I2C_SLAVE, addr)
		fcntl.ioctl(self.file_write, I2C_SLAVE, addr)
		self.current_addr = addr

	def write(self, cmd):
		# appends the null character and sends the string over I2C
		cmd += "\00"
		self.file_write.write(cmd.encode('latin1'))

	def read(self, num_of_bytes=31):
		# reads a specified number of bytes from I2C, then parses and displays the result
		res = self.file_read.read(num_of_bytes)         # read from the board
		if type(res[0]) is str:					# if python2 read
			response = [i for i in res if i != '\x00']
			if ord(response[0]) == 1:             # if the response isn't an error
				# change MSB to 0 for all received characters except the first and get a list of characters
				# NOTE: having to change the MSB to 0 is a glitch in the raspberry pi, and you shouldn't have to do this!
				char_list = list(map(lambda x: chr(ord(x) & ~0x80), list(response[1:])))
				return ''.join(char_list)     # convert the char list to a string and returns it
			else:
				return "Error " + str(ord(response[0]))
				pass
				
		else:									# if python3 read
			while(res[0] != 1):
				res = self.file_read.read(num_of_bytes)         # read from the board
				if res[0] == 1: 
					# change MSB to 0 for all received characters except the first and get a list of characters
					# NOTE: having to change the MSB to 0 is a glitch in the raspberry pi, and you shouldn't have to do this!
					char_list = list(map(lambda x: chr(x & ~0x80), list(res[1:])))
					str_response = str(''.join(char_list))
					return str_response
				else:
					return str(res[0])
					pass

	def query(self, string):
		self.write(string)
		return self.read()

	def close(self):
		self.file_read.close()
		self.file_write.close()

	def list_i2c_devices(self):
		prev_addr = self.current_addr # save the current address so we can restore it after
		i2c_devices = []
		for i in range (0,128):
			try:
				self.set_i2c_address(i)
				self.read(1)
				i2c_devices.append(i)
			except IOError:
				pass
		self.set_i2c_address(prev_addr) # restore the address we were using
		return i2c_devices
	
	def single_output(self):
		return self.query("R")
	
	def calibration(self, point = 'mid', pH = 7):
		command = 'cal'
		points = ['low','mid','high']
		pHs = [4,7,10]
		
		if point.lower() in points:
			point = point.lower()
		else:
			print("Error: Please use 'low', 'mid', or 'high' for point.\n")
			self.close()
		
		if int(pH) in pHs:
			pH = str(int(pH)) + '.00'
		else:
			print("Error: pH must be either 4, 7, or 10.\n")
			self.close()

		if int(pHs[points.index(point)]) == int(float(pH)):
			message = command + ',' + point + ',' + pH
		else:
			print(int(pHs[points.index(point)]), int(float(pH)))
			print("Error: Calibration must be matched.\nE.g. point = 'low' with pH = 4\npoint = 'mid' with pH = 7\npoint = 'high' with pH = 10.")
			self.close()
		self.query(message)
		return 0

	def check_calibration(self):
		a = str(self.query("Cal,?"))[:6]
		a = int(a[-1:])
		possible_states = ['Not Calibrated', 'Mid-Point Calibration', 'Two-Point Calibration', 'Three-Point Calibration']
		print(possible_states[a])
		return a
	
	def calibration_settling(self, tolerance = 0.05, window_size = 10):
		print("Waiting for device pH measurement to settle. This can take 1 - 2 minutes.")
		settle = 'yes'
		settling_iterator = 0
		last_values = [0]*window_size
		while(settle != 'complete'):
			if settle =='yes':
				start_time = time.time()
				previous_time = start_time
				while(time.time() - start_time < 120 and settle == 'yes'):
					if(time.time() - previous_time > 5):
						previous_time = time.time()
						print("\n", int(time.time() - start_time), "seconds have elapsed waiting for pH to settle.")
						print("Last recorded pH values:", last_values)
						print("Current max difference between maximum and minimum values (not less than tolerance):", round(max(last_values) - min(last_values),3))
					pH = self.query("R")[:5]
					try: 
						pH = float(pH)
					except KeyboardInterrupt:
						device.close()
						sys.exit()
					except:
						pass
					if type(pH) == float:
						last_values.insert(0, pH)
						last_values.pop()
						if all(measurement >0 for measurement in last_values) and (max(last_values) - min(last_values) < tolerance):
							return 0
				return 1
				

def main2():
	device = AS_pH_I2C()
	
	device.check_calibration()
	print(device.query("T,?"))
	response = input("Do you wish to calibrate the device (y/n)? ").lower()
	while(response != 'y' and response != 'n'):
		response = input("Do you wish to calibrate the device (y/n)? ").lower()
	
	if response == 'y':
		pHs = [7,4,10]
		points = ['mid', 'low', 'high']
		calibration_input = 0
		for pH_iterator in range(3):
			a = "Please place the pH probe into a pH " + str(pHs[pH_iterator]) + " solution. \nType y when ready to calibrate or n to end: "
			while calibration_input not in ['y','n']:
				calibration_input = input(a).lower()
			if calibration_input == 'n': 
				device.close()
				print("Calibration ended. Calibration for pH", str(pHs[pH_iterator]), "not completed.\n")
				sys.exit()
			
			settle_result = 'fail'
			tolerance = 'none'
			retry = 'none'

			while settle_result != 0:			
				while(type(tolerance) != float or tolerance <= 0):
					try:
						tolerance = float(input("What would you like the pH tolerance for settling to be? 0.03 is recommended: "))
					except:
						pass
				settle_result = int(device.calibration_settling(tolerance = tolerance, window_size = 10))
				if settle_result == 1:
					print(settle_result)
					while(retry != 'y' and retry != 'n'):
						retry = input("More than 2 minutes have elapsed since settle time began. Would you like to continue (y/n)?").lower()			
					if retry == 'n': 
						device.close()
						print("Calibration ended. Calibration for pH", str(pHs[pH_iterator]), "not completed.\n")
						sys.exit()
					settle_result = 'fail'
					tolerance = 'none'
					retry = 'none'
			print("Calibrating pH",str(pHs[pH_iterator]),"...")
			device.calibration(point = points[pH_iterator], pH = pHs[pH_iterator])
			print("Calibrated pH",str(pHs[pH_iterator]),".\n\n")
			calibration_input = 0
		
	elif response == 'n':
		pass
	while(1):
		print(device.query("R"))
		

if __name__ == '__main__':
	main2()
