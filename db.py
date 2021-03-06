import datetime
import re

import MySQLdb

from query import Select, Update, Insert, Tables, Fields, Values, Filter, Order


def cursor(database = 'secconfdb', username = 'secconfdb', password = ''):
	try:
		connection = MySQLdb.connect(
			host = 'localhost', db = database, user = username, passwd = password)

		connection.cursor().execute("""
				SET NAMES utf8;
				SET CHARACTER SET utf8;
				SET character_set_connection=utf8;
			""")

		return connection.cursor()

	except MySQLdb.OperationalError, (errno, message):
		if errno in (1044, 1045, 1142): raise UnauthorizedAccessException(message)
		else: raise


def get_tags(names = None, ids = None):
	where = Filter(None)
	if names is not None:
		where = Filter("name in ('%s')" % "','".join(names))

	if type(ids) == str:
		ids = [ str(int(x)) for x in ids.split(',') ]

	if ids is not None:
		where = Filter("tag in (%s)" % ','.join(ids))

	query = Select(
			fields = Fields([ 'tag', 'name' ]),
			source = Tables('Tags'),
			filter = where,
			order = Order('name'))

	results = query.execute(cursor())

	return [ (i.tag, i.name) for i in results ]


def deadlines(tags = []):
	query = Select(
			filter = Filter.upcomingDeadlines() & Filter.tags(tags),
			order = Order.deadline())
	return query.execute(cursor())

def upcoming(tags = []):
	query = Select(
			filter = Filter.upcoming() & Filter.tags(tags),
			order = Order.start_date())
	return query.execute(cursor())

def recent(tags = []):
	query = Select(
			filter = Filter.recent() & Filter.tags(tags),
			order = Order.start_date(reverse = True))
	return query.execute(cursor())

def locations():
	return Select(
			source = Tables.locations(),
			fields = Fields.locations(),
			filter = Filter(None),
			order = Order.locations()
		).execute(cursor())

def meeting_types():
	return Select(
			source = Tables('MeetingTypes'),
			fields = Fields.meeting_types(),
			filter = Filter(None),
			order  = Order(None),
		).execute(cursor())

def most_recent():
	return Select(
			fields = Fields.events(),
			source = Tables.events(),
			filter = Filter("""
	startDate = (
		select max(startDate) from ConferenceInstances AS ci
			where ci.conference = ConferenceInstances.conference)
	"""),
			order = Order("startDate"),
		).execute(cursor())

def conferences():
	return Select(
			fields = Fields.conference(),
			source = Tables.conference(),
			filter = Filter(None),
			order = Order("abbreviation"),
		).execute(cursor())

def conference(id = None, abbreviation = None):
	assert (id is not None) ^ (abbreviation is not None)

	filter = None
	if id is not None: filter = Filter("conference = %d" % id)
	else: filter = Filter("abbreviation = '%s'" % abbreviation)

	c = cursor()

	conferences = Select(
			fields = Fields.conference(),
			source = Tables.conference(),
			filter = filter,
			order = Order(None),
		).execute(c)

	if len(conferences) == 0: return None
	else: return conferences[0].__dict__


def conference_events(id = None, abbreviation = None):
	conf = conference(id, abbreviation)
	if conf['parent']:
		conf['parent'] = conference(id = int(conf['parent']))

	if conf['tags'] and len(conf['tags']) > 0:
		conf['tags'] = [
			name for (id, name) in get_tags(ids = conf['tags'].split(',')) ]
	else:
		conf['tags'] = []

	events = Select(
			filter = Filter('conference = %d' % conf['conference']),
			order = Order.start_date(reverse = True),
		).execute(cursor())

	return (conf, events)


class UnauthorizedAccessException(Exception):
	def __init__(*args):
		Exception.__init__(*args)


def update(table_name, key, values, credentials):
	query = Update(
			table = Tables(table_name, use_from = False),
			values = Values('SET', values),
			filter = Filter("%s = %d" % key)
		)

	try: query.execute(cursor(**credentials))
	except MySQLdb.OperationalError, (errno, text):
		if errno == 1142: raise UnauthorizedAccessException(text)
		else: raise


def create(table_name, values, credentials):
	query = Insert(
			table = Tables(table_name, use_from = False),
			fields = Fields(values.keys()),
			values = Values('VALUES', values),
		)

	try: query.execute(cursor(**credentials))
	except MySQLdb.OperationalError, (errno, text):
		if errno == 1142: raise UnauthorizedAccessException(text)
		else: raise


def get(table_name):
	return Select(
			source = Tables(table_name),
			fields = Fields('*'),
			filter = Filter(None),
			order = Order(None),
		).execute(cursor())

