#!/usr/bin/python
# -*- coding: utf-8 -*-

import ConfigParser
import logMaster
import re
import os
from subprocess import Popen, PIPE

class RestCreator(object):
	def __init__(self):
		self.logger = logMaster.Logger()
		self.config = ConfigParser.ConfigParser()
		self.system_name = "RestAPI File Creator"
		self.CreateScriptFile()
		
	def MatchFunctionName(self, endpoint_name):
		usabe_stat_list = {"Couchbase":{"machinestats":"MachineStats", "bucketstats":"BucketStats", "clusterbasicstats":"BasicClusterStats"},\
		"RabbitMQ":{"nodestats":"NodeStats", "queuestats":"QueueStats"},\
		"Elasticsearch":{"statics":"GeneralStats"},\
		"GoogleAnalaytics":{"totalvisitors":"ActiveUser", "totalvisitorsperapp":"ActiveUserPerApp"}\
		}
		if bool(re.match(".*couchbase.*",endpoint_name)):
			return (usabe_stat_list["Couchbase"], "cb")
		elif bool(re.match(".*rabbitmq.*",endpoint_name)):
			return (usabe_stat_list["RabbitMQ"], "rb")
		elif bool(re.match(".*elastic.*",endpoint_name)):
			return (usabe_stat_list["Elasticsearch"], "el")
		elif bool(re.match(".*analytics.*",endpoint_name)):
			return (usabe_stat_list["GoogleAnalaytics"], "an")
		else:
			return (False, 0)
		
	def CreatePrefix(self):
		prefix = """
#!/usr/bin/python
# -*- coding: utf-8 -*-

from flask import Flask, jsonify, abort, make_response, request, url_for, render_template, g
from flask_httpauth import HTTPBasicAuth
from subprocess import PIPE,Popen
import datetime
import os
import sys
sys.path.append("{0}/class/config".format(os.path.dirname(os.path.realpath(__file__))))
sys.path.append("{0}/class".format(os.path.dirname(os.path.realpath(__file__))))
import sysauth
import logMaster
import sysquery

app = Flask(__name__)
auth = HTTPBasicAuth()

logger = logMaster.Logger()
cb = sysquery.Couchbase()
rb = sysquery.Rabbitmq()
el = sysquery.Elasticsearch()
an = sysquery.GoogleAnalaytics()
"""
		return prefix
		
	def CreateSuffix(self):
		suffix = """
@auth.verify_password
def verify_password(username,password):
	ip = request.headers.get("X-Real-IP")
	requestpath = request.path
	validator = sysauth.Auth()
	g.result = validator.validate(username,password,ip,requestpath)
	if g.result == True:
		msg = '{0} , {1} , {2} ,RESPONSE:200 OK'.format(ip,username,requestpath)
		logger.LogSave('REST SERVICE','ACCESS',msg)
		return True
	else:
		msg = '{0} , {1} , {2} , RESPONSE:401 UNAUTHORIZED'.format(ip,username,requestpath)
		logger.LogSave('REST SERVICE','INFO',msg)
		abort(401)

@app.errorhandler(401)
def auth_error(error):
    return make_response(jsonify({'error': g.result}), 401)
	
@app.errorhandler(404)
def notfound_error(error):
	ip = request.headers.get("X-Real-IP")
        requestpath = request.path
	msg = '{0} , {1} , {2} ,RESPONSE:404 NOT FOUND'.format(ip,"sysroot",requestpath)
        logger.LogSave('REST SERVICE','ACCESS',msg)
	return make_response(jsonify({'error': 'Aradiginiz endpoint bulunamadi yada artik sistemde yer almiyor.'}), 404)

@app.errorhandler(500)
def internal_server_error(error):
    msg = 'Sunucu bir hata ile karsilasti.Lutfen loglari inceleyin.'
    logger.LogSave('REST SERVICE','CRITIC',msg)
    return make_response(jsonify({'error': 'Sistem yoneticinizle gorusun'}), 500)

if __name__ == '__main__':
	pidfile = "{0}/pid".format(os.path.dirname(os.path.realpath(__file__)))
	pid = str(os.getpid())
	if os.path.isfile(pidfile):
		os.unlink(pidfile)
	file(pidfile, 'w').write(pid)
	app.run("127.0.0.1",5000,debug=True)
"""
		return suffix
		
	def CreateEndpoints(self):
		self.config.read("/Services/Babysitter/config/config.cfg")
		api_version = self.config.get("rest_creator","api_version")
		endpoint_names = self.config.get("rest_creator","endpoint_names").split(",")
		all_endpoints = []
		for endpoints in endpoint_names:
			endpoint_list = []
			get_metrics = self.config.get(endpoints,"get_metrics").split(",")
			if bool(re.match(".*analytics.*",endpoints)) == False:
				db_table = self.config.get(endpoints,"db_table")
			temporary_stats = self.MatchFunctionName(endpoints)
			if temporary_stats[0] == False:
				error_msg = "Tanimlamak istediginiz endpoint alani, desteklnenen bir izleme sistemini icermiyor.Ilgili alan '{0}' .".format(endpoints)
				logger.LogSave(self.system_name, "ERROR", error_msg)
				continue
			usabe_stats = temporary_stats[0]
			function_object_name = temporary_stats[1]
			for metric in get_metrics:
				endpoint_url = "{0}/{1}/{2}".format(api_version, endpoints, metric)
				def_name = "{0}_{1}".format(endpoints, metric)
				if bool(re.match(".*analytics.*",endpoints)) == False:
					statics_function = "{0}.{1}('{2}')".format(function_object_name, usabe_stats[metric], db_table)
				else:
					statics_function = "{0}.{1}()".format(function_object_name, usabe_stats[metric])
				create_endpoint = """
@app.route('"""+endpoint_url+"""',methods=['GET'])
@auth.login_required
def """+def_name+"""():
	stats = """+statics_function+"""
	try:
		return jsonify({'stats':stats})
	except ValueError:
		abort(500)
"""
				self.logger.LogSave(self.system_name,"INFO","'{0}' isimli bir endpoint oluşturuldu.".format(endpoint_url))
				endpoint_list.append(create_endpoint)
			all_endpoints.append("\n".join(endpoint_list))
		return "".join(all_endpoints)
		
	def CreateScriptFile(self):
		script_file_path = "/Services/RestServices/RestServices.py"
		pidfile = "/Services/RestServices/pid"
		#if os.path.isfile(pidfile):
		#	cmd = "kill -9 $(cat {0}) 2>&1 > /dev/null && nohup /usr/bin/python {1} &".format(pidfile, script_file_path)
		#else:
		#	cmd = "nohup /usr/bin/python {0} &".format(script_file_path)
		cmd = "/etc/init.d/solarwinds_services RestServices restart 2>&1 > /dev/null"
		with open(script_file_path, "w") as script:
			script.write("{0}\n{1}\n{2}".format(self.CreatePrefix(), self.CreateEndpoints(), self.CreateSuffix()))
		Popen([cmd], stdout=PIPE, stderr=PIPE, shell=True)
		self.logger.LogSave(self.system_name,"INFO","Script başlatıldı.RestAPI kullanılabilir durumda.")
