#!/usr/bin/env python

# Reads an imap inbox, and writes the calendar entries into a file (if they aren't already in there).
# There is an accompanying script (msg me if interested) which parses the todo file & displays
# notification messages when an event / todo item becomes due.

# Add this to the crontab:
#$ crontab -e
## m	h	dom	mon	dow	command
#*/10	*	*	*	*	/home/ben/bin/dump_calendar.py /home/ben/.todo_file_config

# $cat /home/ben/.google_cal_config
# [imap source]
# username=user
# password=cnffjbeq
# host=your.imap.host
# port=143
# mail_search_days=1
# [todo]
# filename=~/Desktop/TODO

# how to rot13 encode (for the password):
# e.g. python -c "print 'SOMESILLYPASSWORD'.encode('rot13')"

import ConfigParser
import datetime
import imap_utils
import os
import sys

def save_items_in_todo_file(todofile, items):
	f = open(todofile, 'rw+')
	todos = f.read()
	for i in items:
		if i not in todos:
			f.write("\n")
			f.write(i)
			print i
	f.close()

def convert_event_into_todo_strings(event):
	what = imap_utils.safe_get_event_value(event, 'summary.value', 'From IMAP')
	where = imap_utils.safe_get_event_value(event, 'location.value', 'Unspecified')
	when = imap_utils.safe_get_event_value(event, 'dtstart.value', datetime.datetime.now())
	return "+ %s - [IMAP] %s: %s" % (when.strftime("%Y-%m-%d %H:%M"), where, what)

if __name__ == '__main__':
	config_filename = os.path.expanduser(sys.argv[1])
	config = ConfigParser.ConfigParser()
	config.readfp(open(config_filename))
	imap_username = config.get('imap source', 'username')
	imap_password = config.get('imap source', 'password').encode('rot13')
	imap_host = config.get('imap source', 'host')
	imap_port = config.getint('imap source', 'port')
	search_from = config.getint('imap source', 'mail_search_days')
	todo_filename = os.path.expanduser(config.get('todo', 'filename'))

	# look at the last 1 day of email.
	search_from = (datetime.datetime.now()-datetime.timedelta(search_from))

	events = imap_utils.get_calendar_items(imap_username, imap_password, imap_host, imap_port,
	                                                    mark_read=False,
	                                                    criteria=['SINCE', search_from.strftime("%d-%b-%Y")])
	todo_events = [convert_event_into_todo_strings(e) for e in events]

	save_items_in_todo_file(todo_filename, todo_events)

