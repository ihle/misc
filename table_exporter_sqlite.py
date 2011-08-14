#!/usr/bin/env python
# -*- coding: utf-8 -*-

# http://mysql-python.sourceforge.net/MySQLdb.html#cursor-objects
# http://www.kitebird.com/articles/pydbapi.html

# E.g. extract GNUCash transactiosns to CSV:
# http://cloud.github.com/downloads/jralls/gnucash/gnucash_erd.png
# ./table_exporter_sqlite.py /tmp/accounts.sqlite3 \
# "select accounts.name, post_date, (1.0*value_num/value_denom) from splits \
# join accounts on account_guid = accounts.guid \
# join transactions on tx_guid = transactions.guid \
# where accounts.name = 'Groceries'" \
# | sed -e 's/\(,[0-9]\{4\}\)\([0-9][0-9]\)\([0-9][0-9]\)[0-9]*,/\1-\2-\3,/'

## That last sed is to convert dates into ISO8601 format

import csv
import sys
import sqlite3

if __name__ == '__main__':
	from optparse import OptionParser, OptionGroup
	parser = OptionParser('%prog [options] DB_FILE QUERY')
	options, args = parser.parse_args()

	if len(args) < 2:
		import doctest
		doctest.testmod()
		parser.error('Not enough parameters for me to work with.')
		sys.exit()

	db_file = args[0]
	query = args[1]

	csv_writer = csv.writer(sys.stdout)

	sqlite = sqlite3.connect(db_file)
	sqlite.text_factory = str

	cursor = sqlite.cursor()
	cursor.execute(query)

	fields = cursor.description
	csv_writer.writerow([f[0] for f in cursor.description])
	for row in cursor:
		csv_writer.writerow([unicode(str(r), encoding="ascii", errors='ignore') for r in row])
	cursor.close()

