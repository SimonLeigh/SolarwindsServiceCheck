
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


@app.route('/sys/api/v0.1/dmall_couchbase/machinestats',methods=['GET'])
@auth.login_required
def dmall_couchbase_machinestats():
	stats = cb.MachineStats('dmall_couchbase')
	try:
		return jsonify({'stats':stats})
	except ValueError:
		abort(500)


@app.route('/sys/api/v0.1/dmall_couchbase/bucketstats',methods=['GET'])
@auth.login_required
def dmall_couchbase_bucketstats():
	stats = cb.BucketStats('dmall_couchbase')
	try:
		return jsonify({'stats':stats})
	except ValueError:
		abort(500)


@app.route('/sys/api/v0.1/dmall_couchbase/clusterbasicstats',methods=['GET'])
@auth.login_required
def dmall_couchbase_clusterbasicstats():
	stats = cb.BasicClusterStats('dmall_couchbase')
	try:
		return jsonify({'stats':stats})
	except ValueError:
		abort(500)

@app.route('/sys/api/v0.1/bazaar_couchbase/machinestats',methods=['GET'])
@auth.login_required
def bazaar_couchbase_machinestats():
	stats = cb.MachineStats('bazaar_couchbase')
	try:
		return jsonify({'stats':stats})
	except ValueError:
		abort(500)


@app.route('/sys/api/v0.1/bazaar_couchbase/bucketstats',methods=['GET'])
@auth.login_required
def bazaar_couchbase_bucketstats():
	stats = cb.BucketStats('bazaar_couchbase')
	try:
		return jsonify({'stats':stats})
	except ValueError:
		abort(500)


@app.route('/sys/api/v0.1/bazaar_couchbase/clusterbasicstats',methods=['GET'])
@auth.login_required
def bazaar_couchbase_clusterbasicstats():
	stats = cb.BasicClusterStats('bazaar_couchbase')
	try:
		return jsonify({'stats':stats})
	except ValueError:
		abort(500)

@app.route('/sys/api/v0.1/rta_elastic/statics',methods=['GET'])
@auth.login_required
def rta_elastic_statics():
	stats = el.GeneralStats('rta_elasticsearch')
	try:
		return jsonify({'stats':stats})
	except ValueError:
		abort(500)

@app.route('/sys/api/v0.1/dmall_elastic/statics',methods=['GET'])
@auth.login_required
def dmall_elastic_statics():
	stats = el.GeneralStats('dmall_elasticsearch')
	try:
		return jsonify({'stats':stats})
	except ValueError:
		abort(500)

@app.route('/sys/api/v0.1/analytics/totalvisitors',methods=['GET'])
@auth.login_required
def analytics_n11_totalvisitors():
	stats = an.ActiveUser()
	try:
		return jsonify({'stats':stats})
	except ValueError:
		abort(500)


@app.route('/sys/api/v0.1/analytics/totalvisitorsperapp',methods=['GET'])
@auth.login_required
def analytics_n11_totalvisitorsperapp():
	stats = an.ActiveUserPerApp()
	try:
		return jsonify({'stats':stats})
	except ValueError:
		abort(500)

@app.route('/sys/api/v0.1/dmall_rabbitmq/nodestats',methods=['GET'])
@auth.login_required
def dmall_rabbitmq_nodestats():
	stats = rb.NodeStats('dmall_rabbitmq')
	try:
		return jsonify({'stats':stats})
	except ValueError:
		abort(500)


@app.route('/sys/api/v0.1/dmall_rabbitmq/queuestats',methods=['GET'])
@auth.login_required
def dmall_rabbitmq_queuestats():
	stats = rb.QueueStats('dmall_rabbitmq')
	try:
		return jsonify({'stats':stats})
	except ValueError:
		abort(500)


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
