#!/usr/bin/python

import io 			# for file streams
from io import open
import fcntl 			# for I2C addresses
from time import sleep# for sleep
import string		#to parse strings received/sent

class pH_I2C:
	short_timeout = 0.5 # 300 ms processing delay
