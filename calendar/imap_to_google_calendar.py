#!/usr/bin/env python

# Add this to the crontab:
#$ crontab -e
## m	h	dom	mon	dow	command
#*/10	*	*	*	*	/home/ben/bin/dump_calendar_to_google.py /home/ben/.google_cal_config

#$ cat /home/ben/.google_cal_config
# [imap source]
# username=user
# password=cnffjbeq
# host=your.imap.host
# port=143
# mail_search_days=1
# [google]
# username=somebody@gmail.com
# password=tbbtyr_cnffjbeq
# calendar_id=domain.com_2asdfljkh23kljiuasdfhlui3jkq23da.calendar.google.com

# password is rot13 encoded
# e.g. python -c "print 'SOMESILLYPASSWORD'.encode('rot13')" > /home/ben/.password

# Ubuntu: apt-get install python-gdata
# http://code.google.com/apis/calendar/data/1.0/developers_guide_python.html#CreatingEvents

import atom
import datetime
import gdata.calendar.service
import imaplib
import imap_utils
import mailbox
import sys
import os
import ConfigParser

# TODO: There must be an easier way...
class UTC(datetime.tzinfo):
	def utcoffset(self, dt):
		return datetime.timedelta(0)
	def tzname(self, dt):
		return "UTC"
	def dst(self, dt):
		return datetime.timedelta(0)
	@staticmethod
	def to_utc_str(t):
		return t.astimezone(UTC()).strftime('%Y-%m-%dT%H:%M:%S.000Z')

def save_item_if_not_already_there(username, password, item, calendar_id='default'):
	calendar_service = gdata.calendar.service.CalendarService()
	calendar_service.email = username
	calendar_service.password = password
	calendar_service.source = 'imap_to_google_calendar'
	calendar_service.ProgrammaticLogin()

	if not len(find_entry(calendar_service, calendar_id, item)):
		# Create the event
		google_event = add_to_google_calendar(calendar_service, item, calendar_id)
		if google_event is not None:
			return {'what': '[%s]: %s' % (google_event.title.text, google_event.GetHtmlLink().href)}
	return {}

def find_entry(calendar_service, calendar_id, item):
	# check if the entry is already there
	query = gdata.calendar.service.CalendarEventQuery(calendar_id, 'private', 'full', item.summary.value)
	query.start_min = UTC.to_utc_str(item.dtstart.value + datetime.timedelta(hours=-1))
	query.start_max = UTC.to_utc_str(item.dtstart.value + datetime.timedelta(hours=1))
	feed = calendar_service.CalendarQuery(query)

	# Go through and check the title is the same...
	# TODO: may need to make this check body text too.
	return [f for f in feed.entry if f.title.text.strip() == item.summary.value.strip()]

def add_to_google_calendar(calendar_service, item, calendar_id='default'):
	title = imap_utils.safe_get_event_value(item, 'summary.value', 'Imported Event')
	description = imap_utils.safe_get_event_value(item, 'description.value', 'Imported Event')
	where = imap_utils.safe_get_event_value(item, 'location.value', 'Unspecified')
	start_time = imap_utils.safe_get_event_value(item, 'dtstart.value', datetime.datetime.now())
	end_time = imap_utils.safe_get_event_value(item, 'dtend.value', datetime.datetime.now() + datetime.timedelta(hours=1))
	attendees = ["%s [%s]" % (a.cn_paramlist[0], a.value) for a in imap_utils.safe_get_event_value(item, 'attendee_list', [])]

	# tack the attendees list to the bottom of the thing (should really add it to 'event.who')
	if len(attendees):
		description = description + "\n-- Attendees:\n" + "\n".join(attendees)

	event = gdata.calendar.CalendarEventEntry()
	event.title = atom.Title(text=title)
	event.content = atom.Content(text=description)
	event.where.append(gdata.calendar.Where(value_string=where))

	if start_time is None:
		# Use current time for the start_time
		start_time = datetime.datetime.now()
	if end_time is None:
		# have the event last 1 hour
		end_time = datetime.datetime.now() + datetime.timedelta(hour=1)

	# http://code.google.com/apis/calendar/data/1.0/developers_guide_python.html#Reminders
	event.when.append(gdata.calendar.When(start_time=UTC.to_utc_str(start_time),
	                                        end_time=UTC.to_utc_str(end_time),
	                                        reminder=gdata.calendar.Reminder(minutes=1, method='alert')
	                                      ))

	new_event = calendar_service.InsertEvent(event, '/calendar/feeds/%s/private/full' % calendar_id)

	return new_event

if __name__ == '__main__':
	config_filename = os.path.expanduser(sys.argv[1])
	config = ConfigParser.ConfigParser()
	config.readfp(open(config_filename))
	imap_username = config.get('imap source', 'username')
	imap_password = config.get('imap source', 'password').encode('rot13')
	imap_host = config.get('imap source', 'host')
	imap_port = config.getint('imap source', 'port')
	search_from = config.getint('imap source', 'mail_search_days')
	google_username = config.get('google', 'username')
	google_password = config.get('google', 'password').encode('rot13')
	calendar_id = config.get('google', 'calendar_id')

	search_from = (datetime.datetime.now()-datetime.timedelta(search_from))
	events = imap_utils.get_calendar_items(imap_username, imap_password, imap_host, imap_port,
	                            mark_read=True,
	                            criteria=['SINCE', search_from.strftime("%d-%b-%Y")])
	for i in events:
		e = save_item_if_not_already_there(google_username, google_password, i, calendar_id)
		if e:
			print e.get('what', '')

