#	Example usage: (a bit overkill for most scenarios).
#
#	import SimpleEmailHandler
#	log_format = '[%(asctime)s] %(thread)15s %(threadName)15s %(levelname)-10s %(message)s'
#	log_datefmt = '%Y/%m/%d %I:%M:%S %p'
#	log_cfg = { # defaults...
#		'version': 1,
#		'disable_existing_loggers': False,
#		"loggers": {"": {'handlers': ['email'], 'level': 'DEBUG', 'propagate': True}},
#		'handlers': {
#			'email': { 'class':'SimpleEmailHandler.SimpleEmailHandler', 'level': 'WARNING', 'mailhost': 'localhost', 'fromaddr': 'thislogger@serveraddress.com', 'toaddrs': ["alert@myaddress.com"], 'environ':environ, 'formatter': 'default' },
#		},
#		'formatters': { 'default': { 'format':log_format, 'datefmt': log_datefmt } },
#	}

class SimpleEmailHandler(logging.Handler):
	def __init__(self, mailhost, fromaddr, toaddrs, environ={}):
		logging.Handler.__init__(self)
		self.fromaddr = fromaddr
		self.mailhost = mailhost
		self.toaddrs = toaddrs
		self.environ = environ

	def emit(self, record):
		import traceback

		subject = '%s %s' % (
			record.levelname,
			record.getMessage()[0:20]
		)

		request = None

		if record.exc_info:
			exc_info = record.exc_info
			stack_trace = '\n'.join(traceback.format_exception(*record.exc_info))
		else:
			exc_info = (None, record.msg, None)
			stack_trace = 'No stack trace available'

		message = []
		message.append(self.format(record))
		message.append('')
		message.append(stack_trace)
		message.append('')

		for k,v in self.environ.items():
			message.append("%s:\t%s" % (k,v))

		message = "\n".join(message)

		import smtplib
		from email.mime.text import MIMEText
		msg = MIMEText(message)
		msg['Subject'] = subject
		msg['From'] = self.fromaddr
		msg['To'] = self.toaddrs[0]
		msg_str = msg.as_string()
		server = smtplib.SMTP(self.mailhost)
		server.sendmail(self.fromaddr, self.toaddrs, msg_str)
		server.quit()

