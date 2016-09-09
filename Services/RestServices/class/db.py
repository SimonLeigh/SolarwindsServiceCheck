#!/usr/bin/env python
# -*- coding: utf-8 -*-

import MySQLdb as mdb

class Db(object):
	def __init__(self):
		self.conn = mdb.connect(host="localhost", user="watcher", passwd="Qazxsw123*", db="sensorMetric")
		self.vt = self.conn.cursor()

	def write(self, query):
		self.vt.execute(query)
		self.conn.commit()
		return True

	def count(self, query):
		self.vt.execute(query)
		return self.vt.rowcount

	def readt(self, query):
		self.vt.execute(query)
		return self.vt.fetchall()