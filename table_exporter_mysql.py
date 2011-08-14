#!/usr/bin/env python
# -*- coding: utf-8 -*-

# http://mysql-python.sourceforge.net/MySQLdb.html#cursor-objects
# http://www.kitebird.com/articles/pydbapi.html

import csv
import sys
import MySQLdb

if __name__ == '__main__':
	from optparse import OptionParser, OptionGroup
	parser = OptionParser('%prog [options] HOST PORT MYSQLDB MYSQLUSERNAME MYSQLPASSWORD QUERY')
	options, args = parser.parse_args()

	if len(args) < 5:
		import doctest
		doctest.testmod()
		parser.error('Not enough parameters for me to work with.')
		sys.exit()

	host = args[0]
	port = int(args[1])
	mysqldb = args[2]
	username = args[3]
	password = args[4]
	query = args[5]

	csv_writer = csv.writer(sys.stdout)

	connection = MySQLdb.connect (host = host, port = port, user = username, passwd = password, db = mysqldb)

	cursor = connection.cursor()
	cursor.execute(query)

	fields = cursor.description
	csv_writer.writerow([f[0] for f in cursor.description])
	row = cursor.fetchone()
	while row:
		csv_writer.writerow([unicode(str(r), encoding="ascii", errors='ignore') for r in row])
		row = cursor.fetchone()
	cursor.close()
	connection.close()

