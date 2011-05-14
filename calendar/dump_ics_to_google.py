#!/usr/bin/env python

## This is out of date.

# pass in google account username, password, calendar id, and ics filenames.
# pushes calendar entry into google calendar (yes, this is a somewhat limited use case).

import gdata.calendar.service, atom, vobject
import getpass, imaplib, mailbox, datetime, re, os, sys
import imap_to_google_calendar

if __name__ == '__main__':
	google_username = sys.argv[1]
	google_password = sys.argv[2]
	calendar_id = sys.argv[3]
	filenames = sys.argv[4:]

	for filename in filenames:
		event = vobject.readOne(file(filename).read().strip()).vevent
		e = imap_to_google_calendar.save_item_if_not_already_there(google_username, google_password, event, calendar_id)
		print e.get('what', '')

