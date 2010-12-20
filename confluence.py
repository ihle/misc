#!/usr/bin/env python

import re
import sys
import time
import urllib
import urllib2
import cookielib
import mimetypes
import unittest
from BeautifulSoup import BeautifulSoup

class ConfluenceDriver(object):
	def __init__(self, username, password, baseUrl, quiet=False):
		self.username = username
		self.password = password
		self.baseUrl = baseUrl
		cookielib.CookieJar()
		self.quiet = quiet
		self.url_opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookielib.CookieJar()))
		self.login()

	def fetch_url(self, url, params={}, headers={}):
		if not self.quiet:
			print "Fetching", url,
		if len(params):
			# POST (see http://docs.python.org/library/urllib2.html#urllib2.Request)
			request = urllib2.Request(url, urllib.urlencode(params), headers)
		else:
			# GET
			request = urllib2.Request(url, headers=headers)
		response = self.url_opener.open(request).read()
		if not self.quiet:
			print "done"

		# this file is used for debugging only...
		f = open("/tmp/output.html", "w")
		f.write(str(url)+"\n"+str(params)+"\n"+str(headers)+"\n")
		f.write(response)
		f.close()
		return response

	def login(self):
		home_page_content = self.fetch_url(self.baseUrl)
		if "Log in to Confluence" in home_page_content:
			response = self.fetch_url(self.baseUrl + "/login.action",
			                          {"os_username": self.username, "os_password": self.password, "login": "Log+In"})
			assert 'currently logged in as' in response
			if not self.quiet:
				print "Logged in as", self.username
		else:
			assert "Dashboard" in home_page_content

	def view_page(self, page_path):
		view_url = self.baseUrl + '/display/' + page_path
		page = self.fetch_url(view_url)
		return page

	def get_page_id(self, page_path):
		view_page = self.view_page(page_path)
		page_id = re.search(r'/editpage.action\?pageId=(\d+)', view_page).group(1)
		return page_id

	def page_attachments_list(self, page_path):
		page_id = self.get_page_id(page_path)
		attachments_url = self.baseUrl + '/pages/viewpageattachments.action?' + urllib.urlencode({'pageId': page_id})
		attachments_page = self.fetch_url(attachments_url)
		soup = BeautifulSoup(attachments_page)
		attachment_elements = soup.findAll('a', href=re.compile('^/download/attachments/'))
		return [self.baseUrl + elem['href'] for elem in attachment_elements]

	def page_children(self, page_path):
		page = self.view_page(page_path)
		soup = BeautifulSoup(page)
		child_div = soup.find('div', id='page-children')
		if child_div is None:
			return []
		else:
			children_anchors = child_div.findAll('a', href=re.compile('^/display/'))
			return [ConfluenceDriver.url_to_page_path(elem['href']) for elem in children_anchors]

	def edit_page(self, page_path, content):
		page_id = self.get_page_id(page_path)
		edit_url = self.baseUrl+'/pages/editpage.action?'+urllib.urlencode({'pageId':page_id})
		edit_page = self.fetch_url(edit_url)

		save_params = self.get_form_params({'id': 'editpageform'}, edit_page)
		save_params["mode"] = "markup"
		save_params['cancel'] = ""
		save_params['content'] = content
		save_params['pageId'] = page_id
		save_url = self.baseUrl + '/pages/doeditpage.action'
		save_response = self.fetch_url(save_url, save_params, {'Content-Type' : 'application/x-www-form-urlencoded'})

	def create_page(self, parent_page_path, page_title, content):
		view_page = self.view_page(parent_page_path)
		add_url = self.baseUrl+re.search(r'(/pages/createpage.action\?[^"\']+)[\'"]', view_page).group(1)
		add_url = add_url.replace('&amp;', '&') # stupid confluence... html encoded the url.
		add_page = self.fetch_url(add_url)

		# sanitise confluence unfriendly characters from title
		page_title = re.sub(r'[^a-zA-Z0-9_\- ]', '.', page_title)

		save_params = self.get_form_params({'id': 'createpageform'}, add_page)
		save_params["mode"] = "markup"
		save_params['content'] = content
		save_params['cancel'] = ""
		save_params['title'] = page_title
		save_params['newSpaceKey'] = save_params['spaceKey']
		save_url = self.baseUrl + '/pages/docreatepage.action'
		save_response = self.fetch_url(save_url, save_params, {'Content-Type' : 'application/x-www-form-urlencoded'})
		assert ('<title>%s' % page_title) in save_response

		soup = BeautifulSoup(save_response)
		new_page_path = soup.find('span', {'id': 'title-text'}).find('a').get('href')
		return ConfluenceDriver.url_to_page_path(new_page_path)

	def remove_page(self, page_path):
		page_id = self.get_page_id(page_path)
		remove_page = self.fetch_url(self.baseUrl + '/pages/removepage.action?'+urllib.urlencode({'pageId':page_id}))
		params = self.get_form_params({'name': 'removepageform'}, remove_page)
		params['cancel'] = ''
		remove_confirmation = self.fetch_url(self.baseUrl + '/pages/doremovepage.action?'+urllib.urlencode({'pageId':page_id}), params)

	@staticmethod
	def url_to_page_path(url):
		return re.search(r'/display/(.+)$', url).group(1)

	def get_form_params(self, find_dict, page):
		soup = BeautifulSoup(page)
		save_form = soup.find('form', find_dict)
		params = {}
		for input_field in save_form.findAll('input'):
			input_field_name = input_field.get('name')
			input_field_value = input_field.get('value')
			if input_field_name and input_field_value:
				params[input_field_name] = input_field_value
		return params

	def attach_file_to_page(self, page_path, file_name, file_content):
		page_id = self.get_page_id(page_path)
		attach_url = self.baseUrl + '/pages/doattachfile.action?'+urllib.urlencode({'pageId':page_id})
		content_header, post_body = self.encode_multipart_formdata([], [("file_0", file_name, file_content)])
		request = urllib2.Request(attach_url, post_body, content_header)
		attach_response = self.url_opener.open(request).read()

	def encode_multipart_formdata(self, fields, files):
		"""
		fields is a sequence of (name, value) elements for regular form fields.
		files is a sequence of (name, filename, value) elements for data to be uploaded as files
		Return (content_type, body) ready for httplib.HTTP instance
		"""
		def get_content_type(filename):
			return mimetypes.guess_type(filename)[0] or 'application/octet-stream'

		BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
		CRLF = '\r\n'
		L = []
		for (key, value) in fields:
			L.append('--' + BOUNDARY)
			L.append('Content-Disposition: form-data; name="%s"' % key)
			L.append('')
			L.append(value)
		for (key, filename, value) in files:
			L.append('--' + BOUNDARY)
			L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
			L.append('Content-Type: %s' % get_content_type(filename))
			L.append('')
			L.append(value)
		L.append('--' + BOUNDARY + '--')
		L.append('')
		body = CRLF.join(L)
		content_type = {'Content-type': 'multipart/form-data; boundary=%s' % BOUNDARY}
		return content_type, body

class ConfluenceUnitTest(unittest.TestCase):
	def setUp(self):
		url = 'https://confluence.wotifgroup.com'
		self.test_page = "dev/driver+test"
		self.driver = ConfluenceDriver('bihle', 'bihle01', url, quiet=True)
		self.time_suffix = time.strftime('%s')

	def test_view_page_returns_a_page(self):
		page = self.driver.view_page(self.test_page)
		self.assertTrue("driver test" in page)

	def test_created_page_returns_created_path(self):
		created_page_path = self.driver.create_page(self.test_page, "sub page test"+self.time_suffix, "a sub page... please delete me")
		self.assertEquals("dev/sub+page+test"+self.time_suffix, created_page_path)
		self.driver.remove_page(created_page_path)

	def test_created_page_is_attached_to_parent(self):
		created_page_path = self.driver.create_page(self.test_page, "sub page test"+self.time_suffix, "a sub page... please delete me")
		created_page = self.driver.view_page(self.test_page)
		self.assertEquals(True, 'driver test' in created_page)
		self.driver.remove_page(created_page_path)

	def test_that_removed_page_gives_404(self):
		created_page_path = self.driver.create_page(self.test_page, "sub page test"+self.time_suffix, "a sub page... please delete me")
		self.driver.remove_page(created_page_path)
		try:
			created_page = self.driver.view_page(created_page_path)
		except Exception as e:
			self.assertEquals(True, '404' in str(e))
			return
		self.fail("No error returned---should have been a 404")

	def test_get_children_returns_nothing_when_no_children(self):
		children = self.driver.page_children(self.test_page)
		self.assertEquals([], children)

	def test_get_children_returns_list_when_child_added(self):
		created_page_path = self.driver.create_page(self.test_page, "sub page test"+self.time_suffix, "a sub page... please delete me")
		children = self.driver.page_children(self.test_page)
		self.assertEquals(True, u'dev/sub+page+test'+self.time_suffix in children)
		self.driver.remove_page(created_page_path)

	def test_get_attachments_returns_nothing_when_no_attachments(self):
		created_page_path = self.driver.create_page(self.test_page, "sub page test"+self.time_suffix, "a sub page... please delete me")
		attachments = self.driver.page_attachments_list(created_page_path)
		self.assertEquals([], attachments)
		self.driver.remove_page(created_page_path)

	def test_get_attachments_returns_list_when_attachement_added(self):
		created_page_path = self.driver.create_page(self.test_page, "sub page test"+self.time_suffix, "a sub page... please delete me")
		self.driver.attach_file_to_page(created_page_path, "file_name.txt", "blah blah this is the inside of the file")
		attachments = self.driver.page_attachments_list(created_page_path)
		self.assertEquals(1, len(attachments))
		self.assertEquals(True, 'file_name.txt' in attachments[0])
		self.driver.remove_page(created_page_path)

if __name__ == '__main__':
	# test some stuff...
	unittest.main()
	sys.exit(1)

	# living usage examples follow:

	confluenceUser = 'bihle'
	confluencePass = 'xxxx'
	confluenceUrl = 'https://confluence'
	state_page_path = "spacekey/Some+Page+Here"
	driver = ConfluenceDriver(confluenceUser, confluencePass, confluenceUrl)

	# Idempotent.calls
	page = driver.view_page(state_page_path)

	children = driver.page_children(state_page_path)

	attachment_urls = driver.page_attachments_list(state_page_path)

	# These are 'destructive' calls
	new_page_path = driver.create_page(state_page_path, "something 2010-08-16 15:35:54", "a sub page...")

	driver.edit_page(new_page_path, "This text will appear as the page content.")

	driver.attach_file_to_page(new_page_path, "file_name.txt", "blah blah this is the inside of the file")

#	confluenceDriver.remove_page(new_page_path)

