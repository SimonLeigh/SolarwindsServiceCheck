#!/usr/bin/env python

import ConfigParser
import os
import datetime

class Logger(object):
	def __init__(self):
		config = ConfigParser.ConfigParser()
		config.read("/Services/Babysitter/config/config.cfg")
		self.path = config.get("log","path")
		try:
			os.listdir(self.path)
		except OSError:
			os.makedirs(self.path,0755)
		self.path = "{0}Babysitter.txt".format(self.path)

	def LogSave(self,scname,level,msg):
		self.timestamp = datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S")
		self.service_name = scname
		self.msg = msg
		self.level = level
		log_file = open(self.path,"a")
		self.log = "[{0}] [{1}] [{3}] [{2}]\n".format(str(self.timestamp), str(self.service_name), str(self.msg), str(self.level))
		log_file.write(self.log)
		log_file.close()
