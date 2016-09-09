#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
sys.path.append("/Services/Babysitter/config")
import time
import ConfigParser
import logMaster
import db
import DesginRestAPI

logger = logMaster.Logger()
config = ConfigParser.ConfigParser()
db = db.Db()
creator = DesginRestAPI.RestCreator()
watcher = "Babysitter"

def DiscoverNewEndpoints():
	config.read("/Services/Babysitter/config/config.cfg")
	discoverable_list = config.get("rest_creator","endpoint_names").split(",")
	for system in discoverable_list:
		try:
			is_new = config.get(system, "new")
			creator.CreateScriptFile()
			logger.LogSave(watcher, "INFO", "'{0}' sistemi icin yeni bir endpoint olusturuldu.".format(system))
			config.remove_option(system,"new")
			with open("/Services/Babysitter/config/config.cfg", "wb") as mainconfig:
				config.write(mainconfig)
			return True
		except ConfigParser.NoOptionError:
			pass

def main():
	config.read("/Services/Babysitter/config/config.cfg")
	system_delay_second = config.get("env","followed_delay")
	config_files = config.get("env","config_files").split(",")
	for sys_config in config_files:
		main_config = ConfigParser.ConfigParser()
		main_config.read(sys_config)
		main_system_name = sys_config.split("/")[2]
		system_list, new_system_list = main_config.get("env","system_members").split(","), main_config.get("env","system_members").split(",")
		for system in system_list:
			if main_config.get(system,"deleted") == "True":
				table_name = main_config.get(system,"table")
				try:
					new_system_list.remove(system)
				except ValueError:
					logger.LogSave(watcher,"INFO","{0} sistemine ait olan '{1}' isimli sistem, 'system_members' altında tanımlı değildi.".format(main_system_name,system))
				try:
					main_config.set("env","system_members",",".join(new_system_list))
					main_config.remove_section(system)
					with open(sys_config, 'wb') as configfile:
						main_config.write(configfile)
					config.read("/Services/Babysitter/config/config.cfg")
					config.remove_section(system)
					rest_members = config.get("rest_creator","endpoint_names").split(",")
					rest_members.remove(system)
					config.set("rest_creator","endpoint_names",",".join(rest_members))
					with open("/Services/Babysitter/config/config.cfg", "wb") as mainconfig:
						config.write(mainconfig)
					try:
						if main_system_name == "RabbitMqWatcher":
							query1 = "DROP TABLE {0}_nodes".format(table_name)
							query2 = "DROP TABLE {0}_queues".format(table_name)
							db.write(query1)
							db.write(query2)
						else:
							query = "DROP TABLE {0}".format(table_name)
							db.write(query)
						creator.CreateScriptFile()
						logger.LogSave(watcher,"INFO","{0} sistemine ait {1} isimli config alanı / alanları silindi.".format(main_system_name, ",".join(system_list)))
					except:
						logger.LogSave(watcher,"ERROR","{0} sistemine ait {1} isimli tablo silinirken bir sorun oluştu.".format(main_system_name, table_name))
						continue
				except:
					logger.LogSave(watcher,"ERROR","{0} sistemine ait {1} isimli config alanı silinirken bir sorun oluştu.".format(main_system_name, system))
					continue
	return system_delay_second

if __name__ == "__main__":
	try:
		while True:
			DiscoverNewEndpoints()
			time.sleep(int(main()))
	except KeyboardInterrupt:
		sys.exit(0)
