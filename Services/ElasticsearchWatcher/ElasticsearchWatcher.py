#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
import sys
sys.path.append("/Services/ElasticsearchWatcher/config")
import datetime, db, sendMail, logMaster, sourceCalc, ConfigParser, os, time, hashlib, math, re, sys


# ConfigParser object create
config = ConfigParser.ConfigParser()
# logMaster object create
logger = logMaster.Logger()
# sourceCalc object create
calc = sourceCalc.Calculate()
# Db object create
db = db.Db()

if __name__ == "__main__":
	try:
		while True:
			config.read("/Services/ElasticsearchWatcher/config/config.cfg")
			try:
				system_list = config.get("env","system_members").split(",")
			except:
				system_list = [config.get("env","system_members")]
			for el_server in system_list:
				if calc.calc(el_server):
					pass
			time.sleep(30)
	except KeyboardInterrupt:
		print "\n\tScript sonlandırıldı.Görüşmek Üzere =)\n"
		sys.exit(0)
