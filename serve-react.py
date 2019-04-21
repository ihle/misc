#!/usr/bin/python3

import os
import sys
import flask
import logging

logging.basicConfig(level=logging.INFO)

app = flask.Flask(__name__)
app.logger.setLevel(logging.INFO)

logger = logging.getLogger('application')
logger.debug(app.url_map)
logger.debug(os.environ)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

def configure_server(public_path):
	@app.errorhandler(Exception)
	def handle_error(error):
		# handle server faults (i.e. "non http" exceptions that get raised.
		response = flask.make_response("<html><body>Sorry, an error occured</body></html>", 500)

		import traceback
		type_, value_, traceback_ = sys.exc_info()
		trace = traceback.format_tb(traceback_)

		import pprint
		message = ""
		message += "*Stack Trace* \n```%s, %s:\n%s```\n" % (type(error), error.message, "".join(trace))

		return flask.make_response("Uh Oh!", 500)

	@app.errorhandler(404)
	def default(*args, **kwargs):
		page = flask.request.path[1:]

		try:
			contents = open(os.path.join(public_path,page)).read()
		except IOError as e:
			logger.info("couldn't access %s on the file system, will try index.html instead", os.path.join(public_path,page))
			try:
				page = "index.html"
				contents = open(os.path.join(public_path,page)).read()
			except FileNotFoundError as e:
				logger.error("couldn't find index.html")
				return flask.make_response("<html><body>I couldn't find the file you asked for, and couldn't find index.html!</body></html>", 404)

		import mimetypes
		mime, _ = mimetypes.guess_type(page)

		if not mime:
			mime = "text/html"
 
		response = flask.make_response(contents, 200)
		response.headers['Content-type'] = mime
		return response

	# log each request -- sadly we do it this way so that we are stil inside the request / response context.... otherwise we can't get the session data :-/
	access_logger = logging.getLogger('access')
	access_logger.setLevel(logging.INFO)
	@app.after_request
	def log_request(response):
		access_logger.info("\t".join([flask.request.environ.get('REMOTE_ADDR', "no_ip"), flask.session.get('user',{}).get('email', '???'), flask.request.method, flask.request.url, str(response.status_code), str(response.content_length)]))

		# Defeat IE's caching of XMLRPC calls
		response.headers['Cache-Control'] = 'no-cache'
		response.headers['Expires'] = '-1'
		response.headers['Pragma'] = 'no-cache'

		return response

def run_server():
	try:
		import pyqrcode, socket
		# via https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		ip = "127.0.0.1"
		try:
			# doesn't even have to be reachable
			s.connect(('10.255.255.255', 1))
			ip = s.getsockname()[0]
		finally:
			s.close()

		url = 'http://'+ip+":5000"
		qr = pyqrcode.create(url)
		print(qr.terminal(quiet_zone=1))
		logger.info("external address: "+ url)
	except Exception as e:
		logger.info("qrcode not installed, not showing QR", e)

	app.run(host=app.config.get('LISTEN_HOST', '0.0.0.0'), threaded=True)

if __name__ == '__main__':
	path = './'
	if len(sys.argv) > 1:
		path = sys.argv[1]
	configure_server(path)
	run_server()
