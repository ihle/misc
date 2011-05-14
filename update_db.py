#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This is similar to liqubase et al (though much less sophisticated).
# http://mysql-python.sourceforge.net/MySQLdb.html#cursor-objects
# http://www.kitebird.com/articles/pydbapi.html
# http://blog.cherouvim.com/a-table-that-should-exist-in-all-projects-with-a-database/

# ## How to initialise:
# mkdir db_migrations
# cat 'create table schema_version ( `modified_dts` timestamp not null default CURRENT_TIMESTAMP, `id` varchar(256) not null, `desc` varchar(256), primary key (`id`)) ENGINE=InnoDB' > db_migrations/0000-create_schema_version.sql

# ## Then place scripts named XXXX-some_description_here.sql in the directory, (one command per line).
# e.g.
# cat 'alter table approval add form_hash varchar(64) default null' > db_migrations/0001-form_hash_column.sql

import sys
import MySQLdb
import glob
import re

def execute(connection, sql, DEBUG):
	try:
		cursor = connection.cursor()
		cursor.execute(sql)
		cursor.close()
		connection.commit()
		print sql
	except Exception, e:
		if DEBUG:
			print "Update skipped.", sql, e

def migrate(connection, key, desc, sql_lines):
	try:
		cursor = connection.cursor()
		cursor.execute("""select id from schema_version where id = %s""", (key))
		count = cursor.rowcount
		cursor.close()
		if count <= 0:
			cursor = connection.cursor()
			for sql in sql_lines.splitlines():
				cursor.execute(sql)
			cursor.execute("""insert into schema_version (`id`, `desc`) values (%s, %s)""", (key, desc))
			cursor.close()
			connection.commit()

			print "Applied schema update:", key, desc
	except Exception, e:
		print "Error during update:", key, "--", e

def do_it(dbhost, dbport=3306, dbuser='root', dbpasswd='', DEBUG = False):
	try:
		connection = MySQLdb.connect(host = dbhost, port = int(dbport), user = dbuser, passwd = dbpasswd, db = 'registry', use_unicode = True, charset = 'utf8')
		for s in sorted(glob.glob('db_migrations/*.sql')):
			parts = re.match("db_migrations/([0-9]{4})-(.*).sql", s)
			if parts:
				version = parts.group(1)
				comment = parts.group(2).replace('_', ' ')
				migrate(connection, version, comment, file(s).read())

		connection.close()
	except Exception, e:
		print "Unable to update database schema,", e

if __name__ == '__main__':
	do_it('localhost', dbpasswd='root', DEBUG=True)

