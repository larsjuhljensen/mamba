import pg
import re
import mamba.setup


def Connect(database):
	if database in mamba.setup.config().globals:
		conn_str = mamba.setup.config().globals[database].split(":")
		return pg.connect(host=conn_str[0], port=int(conn_str[1]), user=conn_str[2], dbname=conn_str[3])
	else:
		return None

def find_entities(qtypes, name, dictionary=None, exact=False):
	if dictionary == None:
		dictionary = Connect("dictionary")
	if len(qtypes) > 1:
		type_sql = "type IN (%s)" % pg.escape_string(",".join(map(str, qtypes)))
	else:
		type_sql = "type=%d" % qtypes[0]
	if exact:
		name_sql = "upper(name) LIKE '%s'"  % pg.escape_string(name.upper())
	else:
		name_sql = "upper(name) LIKE '%s%%'" % pg.escape_string(name.upper())
	sql = "SELECT type, id, name FROM names WHERE %s AND %s LIMIT 100000;" % (type_sql, name_sql)
	result = dictionary.query(sql).getresult()
	result.sort(key = lambda r: r[2].lower())
	return result


def preferred_name(qtype, qid, dictionary=None):
	if dictionary == None:
		dictionary = Connect("dictionary")
	rows = dictionary.query("SELECT name FROM preferred WHERE type=%d AND id='%s';" % (qtype, pg.escape_string(qid))).getresult()
	if len(rows) >= 1:
		return rows[0][0]
	else:
		return qid


def description(qtype, qid, dictionary=None, userdata=None):
	text = ""
	sql = "SELECT text FROM texts WHERE type=%d AND id='%s';" % (qtype, pg.escape_string(qid))
	try:
		if userdata == None:
			userdata = Connect("userdata")
		text = userdata.query(sql).getresult()[0][0]
	except:
		pass
	try:
		if dictionary == None:
			dictionary = Connect("dictionary")
		text = dictionary.query(sql).getresult()[0][0]
	except:
		pass
	return text


def names(name, entity_types, dictionary=None):
	if dictionary == None:
		dictionary = Connect("dictionary")
	name = pg.escape_string(name.upper())
	qtypes = []
	for qtype in entity_type:
		if qtype == "0":
			qtypes.append("type>0")
		else:
			qtypes.append("type="+qtype)
	return dictionary.query("SELECT type, id, name FROM names WHERE (%s) AND name LIKE '%s%%';" % (" OR ".join(qtypes), name)).getresult()


def sequence(qtype, qid, dictionary=None):
	if dictionary == None:
		dictionary = Connect("dictionary")
	sequence = ""
	try:
		rows = dictionary.query("SELECT sequence FROM sequences WHERE type=%d AND id='%s';" % (qtype, pg.escape_string(qid))).getresult()
		sequence =  rows[0][0]
	except:
		pass
	return sequence

def synonyms(qtype, qid, dictionary=None, userdata=None):
	names = []
	seen = set()
	try:
		if userdata == None:
			userdata = Connect("userdata")
		rows = dictionary.query("SELECT * FROM names WHERE type=%d AND id='%s';" % (qtype, pg.escape_string(qid))).getresult()
		for row in rows:
			name = row[2]
			added = row[3]
			compact = re.sub("[- _]()\[\]", "", name)
			if compact not in seen:
				if added:
					names.append(name)
				seen.add(compact)
	except:
		pass
	try:
		if dictionary == None:
			dictionary = Connect("dictionary")
		rows = dictionary.query("SELECT * FROM names WHERE type=%d AND id='%s';" % (qtype, pg.escape_string(qid))).getresult()
		for row in rows:
			name = row[2]
			compact = re.sub("[- _]()\[\]", "", name)
			if compact not in seen:
				names.append(name)
				seen.add(compact)
	except:
		pass
	return names


def mentions(qtype, qid, textmining=None):
	if textmining == None:
		textmining = Connect("textmining")
	rows = textmining.query("SELECT documents FROM mentions WHERE type=%d AND id='%s';" % (qtype, pg.escape_string(qid))).getresult()
	if len(rows):
		return rows[0][0].split()
	else:
		return []


def count(qtype, qid, textmining=None):
	if textmining == None:
		textmining = Connect("textmining")
	rows = textmining.query("SELECT count FROM counts WHERE type=%d AND id='%s';" % (qtype, pg.escape_string(qid))).getresult()
	if len(rows):
		return rows[0][0]
	else:
		return 0


def entity_names(qtype, qid, dictionary=None):
	if dictionary == None:
		dictionary = Connect("dictionary")
	names = []
	for row in dictionary.query("SELECT name FROM names WHERE type=%d AND id='%s';" % (qtype, pg.escape_string(qid))).getresult():
		names.append(row[0])
	return names


class GetSynonyms(mamba.task.Request):
	
	def main(self):
		rest = mamba.task.RestDecoder(self)
		
		qtype = int(rest["type"])
		qid = rest["id"]
		limit = 1000
		if "limit" in rest:
			limit = int(rest["limit"])
		
		text = "\n".join(map(str.strip, synonyms(qtype, qid)[:limit]))+"\n"
		mamba.http.HTTPResponse(self, text, "text/plain").send()


class GetDescription(mamba.task.Request):
	
	def main(self):
		rest = mamba.task.RestDecoder(self)
		
		qtype = int(rest["type"])
		qid = rest["id"]
		
		text = description(qtype, qid)+"\n"
		mamba.http.HTTPResponse(self, text, "text/plain").send()
