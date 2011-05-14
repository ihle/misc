#!/usr/bin/env python

# http://vobject.skyhouseconsulting.com/usage.html
# http://docs.python.org/library/imaplib.html
# http://www.example-code.com/csharp/imap-search-critera.asp
# Ubuntu: apt-get isntall python-voject


import vobject
import imaplib
import mailbox

def get_calendar_items(username, password, host, port=143, mark_read=True, criteria=['UNSEEN']):
	imap = imaplib.IMAP4(host, port)
	imap.login(username, password)
	imap.select('Inbox', True)
	unseen_nums = imap.search(None, 'UNSEEN')[1][0].split()
	typ, data = imap.search(None, *criteria)
	items = []
	for num in data[0].split():
		typ, message_data = imap.fetch(num, '(RFC822)')

		# make the message unread again if it was before, if the 'mark_read' flag is not set
		if not mark_read and num in unseen_nums:
			imap.store(num, '-FLAGS', '\\Seen')
		msg = mailbox.Message(message_data[0][1])
		for part in msg.walk():
			try:
				if part.get_content_type() == "text/calendar":
					calendar = part.get_payload(decode=1)
					item = vobject.readOne(calendar).vevent
					# ignore event acceptance etc. todo: update attendance list on reciept of one of these...
					if item.summary.value.split(":")[0] not in ['Accepted', 'Declined', 'Tentative']:
						items.append(item)
			except Exception:
				pass
	imap.close()
	imap.logout()
	return items

def safe_get_event_value(event, attribute, default=''):
	vals = attribute.split('.')
	try:
		current = getattr(event, vals[0])
		for v in vals[1:]:
			current = getattr(current, v)
			if current == None:
				return default
		return current
	except AttributeError:
		return default

