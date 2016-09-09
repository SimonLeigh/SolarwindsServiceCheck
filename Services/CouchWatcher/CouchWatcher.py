#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import division
import sys
sys.path.append("/Services/CouchWatcher/config")
import datetime, db, logMaster, sourceCalc, ConfigParser, os, errorMessageTemplate, time, hashlib, math, re, sys


# ConfigParser object create
config = ConfigParser.ConfigParser()
# logMaster object create
logger = logMaster.Logger()
# sourceCalc object create
calc = sourceCalc.Calculate()
# errorMessageTemplate object create
err_msg = errorMessageTemplate.Message()
# Db object create
db = db.Db()



if __name__ == "__main__":
	try:
		while True:
			config.read("/Services/CouchWatcher/config/config.cfg")
			system_list = config.get("env","system_members").split(",")
			for cb_server in system_list:
				service = "CouchhWatcher (%s)" % cb_server
				if calc.calc(cb_server):
					config.read("/Services/CouchWatcher/config/config.cfg")
					server_table = config.get(cb_server,"table")
					cluster_on_db = [i[0] for i in db.readt("SELECT HOSTNAME FROM %s" % server_table)]
					cluster_reel = config.get(cb_server,"allservers").split(",")
					for i in cluster_on_db:
						if i not in cluster_reel:
							db.write("UPDATE {0} SET STATUS='Down', CLUSTERMEMBERSHIP='None' WHERE HOSTNAME='{1}'".format(server_table,i))
							msg = "'{0}' hostname / IP couchbase sunucunuza erişilemiyor.Lütfen kontrol ediniz.".format(i)
							logger.LogSave(service,"ERROR",msg)
				#else:
				#	if db.count("SELECT HOSTNAME FROM %s" % cb_server) > 0:
				#		status = "UPDATE %s SET STATUS='Down', CLUSTERMEMBERSHIP='None'" % cb_server
				#		db.write(status)
				#		msg = "Tüm couchbase cluster ulaşılamaz durumdadır.Sunucularınızı kontrol ediniz."
				#		logger.LogSave(service,"FATAL",msg)
				#	else:
				#		msg = "Tüm couchbase cluster ulaşılamaz durumdadır.Sunucularınızı kontrol ediniz."
				#		logger.LogSave(service,"FATAL",msg)
			time.sleep(30)
	except KeyboardInterrupt:
		print "\n\tScript sonlandırıldı.Görüşmek Üzere =)\n"
		sys.exit(0)
