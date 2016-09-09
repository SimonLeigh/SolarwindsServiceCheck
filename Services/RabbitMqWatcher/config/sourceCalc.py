#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
import ConfigParser, logMaster, requests, sys, sendMail, math, re, time, db, datetime, MySQLdb

class Calculate(object):
	def __init__(self):
		""" Gerekli kaynaklarin hesaplanmasi icin kullanilmaktadir. """
		self.config = ConfigParser.ConfigParser()
		self.config.read("/Services/RabbitMqWatcher/config/config.cfg")
		self.logger = logMaster.Logger()
		#self.mailler = sendMail.Mail()
		self.sender = "RabbitMqWatcher System"
		self.to = self.config.get("contact","tech")
		self.db = db.Db()
		
	def __findCluster(self):
		""" Konfigürasyon dosyasında verilen server parametresi kullanılarak, sisteme ait diğer serverları tespit ediyoruz. """
		url = "http://{0}:15672/api/nodes".format(self.mainserver)
		r = requests.get(url,auth=(self.user,self.password))
		r = r.json()
		v,servers = [], [r[i]["name"] for i in range(len(r))]
		for i in servers:
			if i is not None:
				v.append("{0}.n11.local".format(i.split("@")[1]))
			else:
				self.logger.LogSave(self.service,"INFO","Sistemde cluster bulunmuyor.")
		if len(v) > 1:
			self.allserver = v
			v.remove(self.config.get(self.server_section,"server"))
			if self.setConf(v,self.server_section,"clusterMembers") == True:
				self.logger.LogSave(self.service,"INFO","clusterMembers parametresi set edildi.")
			else:
				self.logger.LogSave(self.service,"ERROR","Configürasyon kayıt edilemedi.")
				return False
		else:
			self.logger.LogSave(self.service,"INFO","Sistemde cluster bulunmuyor.")
		
	def __checkLive(self,server):
		""" Sunucunun durumunun sağlıklı olup olmadığını kontrol eder. """
		url = "http://{0}:15672/api/nodes".format(server)
		try:
			r = requests.get(url,auth=(self.user,self.password))
			if r.status_code == 200:
				return True
			else:
				return False
		except requests.exceptions.ConnectionError:
			return False
			
	def setConf(self,confArray,section,name=None,add=False):
		""" Tespit edilen parametrelerin, gerekli dosyalara işlenmesini sağlıyoruz. """
		th = ConfigParser.ConfigParser()
		th.read("/Services/RabbitMqWatcher/config/config.cfg")
		try:
			if add == True:
				if self.config.has_section(section) == False:
					th.add_section(section)
					for k,v in confArray.items():
						th.set(section,k,v)
				else:
					for k,v in confArray.items():
						th.set(section,k,v)
			else:
				item = ",".join(map(str,confArray))
				th.set(section,name,item)
		except ConfigParser.NoSectionError:
			setconf_err = "Configürasyon kayıt edilemedi.'{0}' adında bir section yer almıyor.".format(section)
			self.logger.LogSave(self.service,"ERROR",setconf_err)
			return False
		with open('/Services/RabbitMqWatcher/config/config.cfg', 'wb') as configfile:
			th.write(configfile)
			return True
			
	def __findSource(self):
		""" Ana sunucu ve cluster sunucuların kaynaklarını bulur ve belirlenen aralıklara göre eşik değerlerini belirler. """
		timestamp = datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')
		if self.mainserver == self.config.get(self.server_section,"server"):
			try:
				self.allserver.append(self.config.get(self.server_section,"server"))
			except AttributeError:
				self.allserver = []
				self.allserver.append(self.config.get(self.server_section,"server"))
			finally:
				self.setConf(self.allserver,self.server_section,"allservers")
		else:
			self.allserver = self.config.get(self.server_section,"clusterMembers").split(",")
			self.setConf(self.allserver,self.server_section,"allservers")
			
		for i in self.allserver:
			status = self.__checkLive(i)
			if status == True:
				url = "http://{0}:15672/api/nodes/{1}".format(self.mainserver,"rabbit@{0}".format(i.split(".")[0]))
				r = requests.get(url,auth=(self.user,self.password))
				r = r.json()
				try:
					address = "rabbit@{0}".format(i.split(".")[0])
					status = "OK" if self.__checkLive(i) else "Down"
					clustermembership = "OK" if self.__checkLive(i) else "None"
					runing = "True" if r["running"] == True else "False"
					uptime = math.ceil(r["uptime"] / 100) if r["running"] == True else "None" # saniye cinsinden
					disk_free = math.ceil(r["disk_free"] / 1024 / 1024) if r["running"] == True else "None"
					disk_free_alarm = math.ceil(r["disk_free_alarm"] / 1024 / 1024) if r["running"] == True else "None"
					disk_free_limit = math.ceil(r["disk_free_limit"] / 1024 / 1024) if r["running"] == True else "None"
					mem_used = math.ceil(r["mem_used"] / 1024 / 1024) if r["running"] == True else "None"
					mem_alarm = math.ceil(r["mem_alarm"] / 1024 / 1024) if r["running"] == True else "None"
					mem_limit = math.ceil(r["mem_limit"] / 1024 / 1024) if r["running"] == True else "None"
					fd_total = r["fd_total"] if r["running"] == True else "None"
					fd_used = r["fd_used"] if r["running"] == True else "None"
					sockets_total = r["sockets_total"] if r["running"] == True else "None"
					sockets_used = r["sockets_used"] if r["running"] == True else "None"
				except:
					self.db.write("UPDATE {0}_nodes SET STATUS='Down', CLUSTERMEMBERSHIP='None' WHERE HOSTNAME='{1}'".format(self.table,i))
                                	msg = "'{0}' hostname / IP rabbitmq_nodes sunucunuza erişilemiyor.Lütfen kontrol ediniz.".format(i)
                                	self.logger.LogSave(self.service,"ERROR",msg)
				try:
					param = "INSERT INTO {16}_nodes(HOSTNAME, STATUS, CLUSTERMEMBERSHIP, RUNING, UPTIME, DISK_FREE, DISK_FREE_ALARM, DISK_FREE_LIMIT, MEM_USED, MEM_ALARM, MEM_LIMIT, FD_TOTAL, FD_USED, SOCKETS_TOTAL, SOCKETS_USED,LAST_MIDFIED) VALUES (\"{0}\",\"{1}\",\"{2}\",\"{3}\",\"{4}\",\"{5}\",\"{6}\",\"{7}\",\"{8}\",\"{9}\",\"{10}\",\"{11}\",\"{12}\",\"{13}\",\"{14}\",\"{15}\")".format(address,status,clustermembership,runing,uptime,disk_free,disk_free_alarm,disk_free_limit,mem_used,mem_alarm,mem_limit,fd_total,fd_used,sockets_total,sockets_used,timestamp,self.table)
					self.db.write(param)
					msg = "'{0}' hostname / IP adresi için değerler DB ye yazıldı.".format(i)
					self.logger.LogSave(self.service,"INFO",msg)
				except MySQLdb.IntegrityError:
					param = "UPDATE {16}_nodes SET STATUS=\"{0}\", CLUSTERMEMBERSHIP=\"{1}\", RUNING=\"{2}\", UPTIME=\"{3}\", DISK_FREE=\"{4}\", DISK_FREE_ALARM=\"{5}\", DISK_FREE_LIMIT=\"{6}\", MEM_USED=\"{7}\", MEM_ALARM=\"{8}\", MEM_LIMIT=\"{9}\", FD_TOTAL=\"{10}\", FD_USED=\"{11}\", SOCKETS_TOTAL=\"{12}\", SOCKETS_USED=\"{13}\", LAST_MIDFIED=\"{14}\" WHERE HOSTNAME=\"{15}\"".format(status,clustermembership,runing,uptime,disk_free,disk_free_alarm,disk_free_limit,mem_used,mem_alarm,mem_limit,fd_total,fd_used,sockets_total,sockets_used,timestamp,address,self.table)
					self.db.write(param)
					msg = "'{0}' hostname / IP adresi için değerler update edildi.".format(i)
					self.logger.LogSave(self.service,"INFO",msg)
				except MySQLdb.ProgrammingError:
					table_create = "CREATE TABLE {0}_nodes(HOSTNAME VARCHAR(40) PRIMARY KEY, STATUS VARCHAR(30), CLUSTERMEMBERSHIP VARCHAR(30), RUNING VARCHAR(20), UPTIME VARCHAR(20), DISK_FREE VARCHAR(30), DISK_FREE_ALARM VARCHAR(30), DISK_FREE_LIMIT VARCHAR(30), MEM_USED VARCHAR(30), MEM_ALARM VARCHAR(30), MEM_LIMIT VARCHAR(30), FD_TOTAL VARCHAR(30), FD_USED VARCHAR(30), SOCKETS_TOTAL VARCHAR(30), SOCKETS_USED VARCHAR(30),LAST_MIDFIED DATETIME)".format(self.table)
					self.db.write(table_create)
					param = "INSERT INTO {16}_nodes(HOSTNAME, STATUS, CLUSTERMEMBERSHIP, RUNING, UPTIME, DISK_FREE, DISK_FREE_ALARM, DISK_FREE_LIMIT, MEM_USED, MEM_ALARM, MEM_LIMIT, FD_TOTAL, FD_USED, SOCKETS_TOTAL, SOCKETS_USED,LAST_MIDFIED) VALUES (\"{0}\",\"{1}\",\"{2}\",\"{3}\",\"{4}\",\"{5}\",\"{6}\",\"{7}\",\"{8}\",\"{9}\",\"{10}\",\"{11}\",\"{12}\",\"{13}\",\"{14}\",\"{15}\")".format(address,status,clustermembership,runing,uptime,disk_free,disk_free_alarm,disk_free_limit,mem_used,mem_alarm,mem_limit,fd_total,fd_used,sockets_total,sockets_used,timestamp,self.table)
                                        self.db.write(param)
                                        msg = "'{0}' hostname / IP adresi için değerler DB ye yazıldı.".format(i)
                                        self.logger.LogSave(self.service,"INFO",msg)
				#self.allserver = []
			else:
				self.db.write("UPDATE {0}_nodes SET STATUS='Down', CLUSTERMEMBERSHIP='None' WHERE HOSTNAME='{1}'".format(self.table,i))
				msg = "'{0}' hostname / IP rabbitmq_nodes sunucunuza erişilemiyor.Lütfen kontrol ediniz.".format(i)
				self.logger.LogSave(self.service,"ERROR",msg)
		self.allserver = []
		
	def __findQueues(self):
		url = "http://{0}:15672/api/queues".format(self.mainserver)
		r = requests.get(url,auth=(self.user,self.password))
		queue_names, detail_url = [i["name"] for i in r.json()], "http://{0}:15672/api/queues/%2F".format(self.mainserver)
		timestamp = datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')
		for queue in queue_names:
			dst = "{0}/{1}".format(detail_url,queue)
			d = requests.get(dst,auth=(self.user,self.password))
			items = d.json()
			name = items["name"]
			status = "Online" if items["state"] == "running" else "Offline"
			state = items["state"]
			consumers = items["consumers"] if items["state"] == "running" else "0"
			sync_slave_nodes = ",".join(items["synchronised_slave_nodes"]) if type(items["synchronised_slave_nodes"]) == list else items["synchronised_slave_nodes"]
			msg_uncack = items["messages_unacknowledged"] if items["state"] == "running" else "0"
			msg_ready = items["messages_ready"] if items["state"] == "running" else "0"
			node = items["node"] if items["node"] != "" else "None"
			disk_reads = items["disk_reads"] if items["state"] == "running" else "0"
			disk_writes = items["disk_writes"] if items["state"] == "running" else "0"
			deliver_get = items["message_stats"]["deliver_details"]["rate"] if items["state"] == "running" and "message_stats" in items else "0"
			publish_get = items["message_stats"]["publish_details"]["rate"] if items["state"] == "running" and "message_stats" in items else "0"
			try:
				param = "INSERT INTO {13}_queues VALUES (\"{0}\",\"{1}\",\"{2}\",\"{3}\",\"{4}\",\"{5}\",\"{6}\",\"{7}\",\"{8}\",\"{9}\",\"{10}\",\"{11}\",\"{12}\")".format(name,status,state,consumers,sync_slave_nodes,msg_uncack,msg_ready,node,disk_reads,disk_writes,deliver_get,publish_get,timestamp,self.table)
				self.db.write(param)
				msg = "'{0}' queues için değerler db ye yazıldı.".format(name)
				self.logger.LogSave(self.service,"INFO",msg)
			except MySQLdb.IntegrityError:
				param = "UPDATE {13}_queues SET STATUS=\"{0}\", STATE=\"{1}\", CONSUMERS=\"{2}\", SYNCRONISED_SLAVE_NODES=\"{3}\", MSG_UNACKNOVLEDGED=\"{4}\", MSG_READY=\"{5}\", NODE=\"{6}\", DISK_READS=\"{7}\", DISK_WRITES=\"{8}\", DELIVER_GET=\"{9}\", PUBLISH_GET=\"{10}\", LAST_MIDFIED=\"{11}\" WHERE QUEUENAME=\"{12}\"".format(status,state,consumers,sync_slave_nodes,msg_uncack,msg_ready,node,disk_reads,disk_writes,deliver_get,publish_get,timestamp,name,self.table)
				self.db.write(param)
				msg = "'{0}' queues için değerler update edildi.".format(name)
				self.logger.LogSave(self.service,"INFO",msg)
			except MySQLdb.ProgrammingError:
				table_create = "CREATE TABLE {0}_queues(QUEUENAME VARCHAR(200) PRIMARY KEY, STATUS VARCHAR(30), STATE VARCHAR(30), CONSUMERS VARCHAR(10), SYNCRONISED_SLAVE_NODES VARCHAR(300), MSG_UNACKNOVLEDGED VARCHAR(50), MSG_READY VARCHAR(50), NODE VARCHAR(50), DISK_READS VARCHAR(50), DISK_WRITES VARCHAR(50), DELIVER_GET VARCHAR(50), PUBLISH_GET VARCHAR(50), LAST_MIDFIED DATETIME)".format(self.table)
				self.db.write(table_create)
				param = "INSERT INTO {13}_queues VALUES (\"{0}\",\"{1}\",\"{2}\",\"{3}\",\"{4}\",\"{5}\",\"{6}\",\"{7}\",\"{8}\",\"{9}\",\"{10}\",\"{11}\",\"{12}\")".format(name,status,state,consumers,sync_slave_nodes,msg_uncack,msg_ready,node,disk_reads,disk_writes,deliver_get,publish_get,timestamp,self.table)
                                self.db.write(param)
                                msg = "'{0}' queues için değerler db ye yazıldı.".format(name)
                                self.logger.LogSave(self.service,"INFO",msg)

		self.setConf(queue_names,self.server_section,"queueNames")
			
	def calc(self, server):
		""" Ana işlemleri yapan fonksiyon.Sunucu kontrolü,ana sunucuya ulaşılamıyorsa cluster içinden yeni sunucu seçimi ve gerekli hataların loglanması. """
		self.config.read("/Services/RabbitMqWatcher/config/config.cfg")
		self.server_section = server
		self.service = "Source Calculator (%s)" % self.server_section
                self.user = self.config.get(self.server_section,"ruser")
                self.password = self.config.get(self.server_section,"rpass")
		self.table = self.config.get(self.server_section,"table")
		try:
			if self.__checkLive(self.config.get(self.server_section,"server")) == False:
				self.logger.LogSave(self.service,"ERROR","{0} hostname / IP sunucunuza ulaşılamadı.'clusterMembers' içinden herhangi bir sunucuya ulaşılması denenecek.".format(self.config.get(self.server_section,"server")))
				raise ValueError()
			else:
				self.mainserver = self.config.get(self.server_section,"server")
				self.logger.LogSave(self.service,"INFO","'mainserver' olarak {0} hostname / IP adresi belirlendi.".format(self.mainserver))
				try:
					self.__findCluster()
					self.__findSource()
					self.__findQueues()
					return True
				except:
					return False
		except ValueError:
			try:
				self.servers = self.config.get(self.server_section,"clusterMembers").split(",")
				for i in self.servers:
					if i != "":
						if self.__checkLive(i) == True:
							self.mainserver = i
							self.logger.LogSave(self.service,"INFO","'mainserver' olarak {0} hostname / IP adresi belirlendi.".format(i))
							try:
								self.__findSource()
								self.__findQueues()
								return True
							except:
								return False
						elif i == self.servers[-1]:
							if self.checkLive(i) == False:
								self.logger.LogSave(self.service,"FATAL","Cluster içinde hiçbir sunucuya ulaşılamıyor.Sunucuları kontrol ediniz.")
								#self.servers.append(self.config.get(self.server_section,"server"))
								#err = self.error_msgger.unreachable(self.servers)
								#self.mailler.send_message(err[1],err[0],self.sender,self.to)
								return False
					else:
						self.logger.LogSave(self.service,"FATAL","'clusterMembers' parametresi altında hiç sunucu bulunmuyor.Sistemlerinizi kontrol ediniz.")
						return False
			except ConfigParser.NoOptionError:
				self.logger.LogSave(self.service,"FATAL","'clusterMembers' parametresi tanımlı değil yada sistemde cluster makina bulunmuyor.")
				return False
			
