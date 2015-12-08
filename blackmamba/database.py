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
	name_queries = []
	name_queries.append("upper(name) LIKE '%s'"  % pg.escape_string(name.upper()))
	if not exact:
		name_queries.append("upper(name) LIKE '%s%%'" % pg.escape_string(name.upper()))
		
	entities = []
	used = set()
	for name_sql in name_queries:
		for table in "preferred", "names":
			sql = "SELECT type, id, name FROM %s WHERE %s AND %s LIMIT 100000;" % (table, type_sql, name_sql)
			result = dictionary.query(sql).getresult()
			result.sort(key = lambda r: r[2].lower())
			for entity in result:
				if (entity[0], entity[1]) not in used:
					entities.append(entity)
					used.add((entity[0], entity[1]))
	return entities


def preferred_type_name(qtype, dictionary=None):
	type_preferred = {
		-2 : "Organism",
		-21 : "Biological process",
		-22 : "Cellular component",
		-23 : "Molecular function",
		-25 : "Tissue",
		-26 : "Disease",
		-27 : "Environment"
	}
	if dictionary == None:
		dictionary = Connect("dictionary")
	if qtype in type_preferred:
		return type_preferred[qtype]
	elif qtype >= 0:
		rows = dictionary.query("SELECT name FROM preferred WHERE type=-2 AND id='%d';" % qtype).getresult()
		if len(rows) >= 1:
			return "%s protein" % rows[0][0]
		else:
			return "Protein"
	else:
		return ""


def canonical(qtype, qid, dictionary=None):
	canonical = ""
	sql = "SELECT canonical FROM canonical WHERE type=%d AND id='%s';" % (qtype, pg.escape_string(qid))
	try:
		if dictionary == None:
			dictionary = Connect("dictionary")
		canonical = dictionary.query(sql).getresult()[0][0]
	except:
		pass
	return canonical


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


def image(qtype, qid, dictionary=None):
	image = None
	sql = "SELECT image FROM images WHERE type=%d AND id='%s';" % (qtype, pg.escape_string(qid))
	try:
		if dictionary == None:
			dictionary = Connect("dictionary")
		image = dictionary.query(sql).getresult()[0][0]
	except:
		pass
	return image
	
	
def linkouts(qtype, qid, dictionary=None):
	links = []
	sql = "SELECT source, url FROM linkouts WHERE type=%d AND id='%s' ORDER BY priority ASC;" % (qtype, pg.escape_string(qid))
	try:
		if dictionary == None:
			dictionary = Connect("dictionary")
		links = dictionary.query(sql).getresult()
	except:
		pass
	return links


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


def preferred_name(qtype, qid, dictionary=None):
	if dictionary == None:
		dictionary = Connect("dictionary")
	rows = dictionary.query("SELECT name FROM preferred WHERE type=%d AND id='%s';" % (qtype, pg.escape_string(qid))).getresult()
	if len(rows) >= 1:
		return rows[0][0]
	else:
		return qid


def pharos(qtype, qid, dictionary=None):
	if dictionary == None:
		dictionary = Connect("dictionary")
	pharos = ()
	try:
		rows = dictionary.query("SELECT family, level FROM pharos WHERE type=%d AND id='%s';" % (qtype, pg.escape_string(qid))).getresult()
		pharos = rows[0]
	except:
		pass
	return pharos


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


def url(qtype, qid, dictionary=None):
	if qtype == -2:
		return "http://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?mode=Info&id=%s" % qid
	elif qtype <= -21 and qtype >= -24:
		return "http://www.ebi.ac.uk/QuickGO/GTerm?id=%s" % qid
	elif qtype == -25:
		return "http://purl.obolibrary.org/obo/%s" % qid.replace(":", "_")
	elif qtype == -26:
		return "http://purl.obolibrary.org/obo/%s" % qid.replace(":", "_")
	elif qtype == -27:
		return "http://purl.obolibrary.org/obo/%s" % qid.replace(":", "_")
	else:
		return None

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


def entity_dict(qtype, qid, dictionary=None):
	if dictionary == None:
		dictionary = Connect("dictionary")
	data = {}
	if qtype >= 0:
		data = {"@id" : "stringdb:%d.%s" % (qtype, qid)}
	elif qtype == -1:
		data = {"@id" : "stitchdb:%s" % qid}
	elif qtype == -2:
		data = {"@id" : "taxonomy:%s" % qid}
	elif ":" in qid:
		data = {"@id" : qid}
	else:
		data = {"@id" : "_:%s" % qid}
	data["name"] = preferred_name(qtype, qid, dictionary)
	value = canonical(qtype, qid, dictionary)
	if value != "":
		data["canonical"] = value
	value = description(qtype, qid, dictionary)
	if value != "":
		data["description"] = value
	return data


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
		mamba.http.HTTPResponse(self, description(qtype, qid)+"\n", "text/plain").send()


class GetSequence(mamba.task.Request):

	def main(self):
		rest = mamba.task.RestDecoder(self)
		qtype = int(rest["type"])
		qid = rest["id"]
		mamba.http.HTTPResponse(self, sequence(qtype, qid)+"\n", "text/plain").send()
