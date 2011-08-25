import MySQLdb
import sqlite3

table_name = "notes"
columns = ["id", "title", "description", "created", "updated", "due", "status_id", "priority_id", "user_id", "tags"]

try:
	conn = MySQLdb.connect (host = "localhost", user = "root", passwd = "root", db = "notes")
	cursor = conn.cursor()
except MySQLdb.Error, e:
	print "Error %d: %s" % (e.args[0], e.args[1])
	sys.exit(1)

sqlite = sqlite3.connect("converted.sqlite3")
sqlite.text_factory = str

with sqlite:
	select_query = "SELECT %s FROM %s" % (", ".join(columns), table_name)
	print select_query
	cursor.execute(select_query)
	rows = cursor.fetchall()
	for row in rows:
		if row == None:
			break
		print row
		insert_query = 'insert into %s (%s) values (%s)' % (table_name, ", ".join(columns), ", ".join(["?"]*len(columns)))
		print insert_query, row
		sqlite.execute(insert_query , tuple(row))

