import json
import pg
import re

import database
import mamba.task
import mamba.util


def entity_dict(qtype, qid, dictionary=None):
	if dictionary == None:
		dictionary = database.Connect("dictionary")
		data = {}
	if qtype >= 0:
		data = {"@id" : "stringdb:%d.%s" % (qtype, qid)}
	elif qtype == -1:
		data = {"@id" : "stitchdb:%s" % qid}
	elif qtype == -2:
		data = {"@id" : "taxonomy:%s" % qid}
	elif qtype <= -21 and qtype >= -24:
		data = {"@id" : "%s" % qid}
	elif qtype == -25:
		data = {"@id" : "%s" % qid}
	elif qtype == -26:
		data = {"@id" : "%s" % qid}
	elif qtype == -27:
		data = {"@id" : "%s" % qid}
	else:
		 {"@id" : qid}
	data["name"] = database.preferred_name(qtype, qid, dictionary)
	canonical = database.canonical(qtype, qid, dictionary)
	if canonical != "":
		data["canonical"] = canonical
	description = database.description(qtype, qid, dictionary)
	if description != "":
		data["description"] = description
 	return data

	
class annotations(mamba.task.Request):
	
	def main(self):
		match = re.match("/document/([0-9]+)/annotations(/([0-9]*))?", self.http.path)
		if match and "JSON-LD" in mamba.setup.config().sections:
			document = int(match.group(1))
			annotation = None
			if match.group(3) != None and match.group(3) != "":
				annotation = int(match.group(3))
			settings = mamba.setup.config().sections["JSON-LD"]
			types = [float(i) for i in settings["types"].split(" ")]
			textmining = database.Connect("textmining")
			sql = "SELECT * FROM documents WHERE document=%d;" % document
			records = textmining.query(sql).dictresult()
			used = set()
			if len(records):
				data = {}
				data["@context"] = "http://nlplab.org/ns/restoa-context-20150307.json"
				sql = "SELECT * FROM matches WHERE document=%d;" % document
				records = textmining.query(sql).dictresult()
				data["@id"] = "/document/%d/annotations" % document
				if "license" in settings:
					data["dctypes:license"] = settings["license"]
				data["@graph"] = []
				index = -1
				prev_start = None
				for record in records:
					if record["type"] in types:
						start = record["start"]
						stop = record["stop"]+1
						qtype = int(record["type"])
						qid = record["id"]
						if start != prev_start:
							index += 1
							data["@graph"].append({})
							data["@graph"][index]["@id"] = "/document/%d/annotations/%d" % (document, index)
							data["@graph"][index]["target"] = "/document/%d#char=%d,%d" % (document, start, stop)
							data["@graph"][index]["body"] = entity_dict(qtype, qid)
							prev_start = start
							used = set()
						elif qtype >= -1 or qtype not in used:
							if type(data["@graph"][index]["body"]) is dict:
								data["@graph"][index]["body"] = [data["@graph"][index]["body"]]
							data["@graph"][index]["body"].append(entity_dict(qtype, qid))
						used.add(qtype)
				if annotation == None:
					mamba.http.HTTPResponse(self, json.dumps(data, separators=(',',':'), sort_keys=True), "application/ld+json").send()
				elif annotation < len(data["@graph"]):
					data["@id"] = data["@graph"][annotation]["@id"]
					data["target"] = data["@graph"][annotation]["target"]
					data["body"] = data["@graph"][annotation]["body"]
					del data["@graph"]
					mamba.http.HTTPResponse(self, json.dumps(data, separators=(',',':'), sort_keys=True), "application/ld+json").send()
				else:
					mamba.http.HTTPErrorResponse(self, 404, "Not Found").send()
			else:
				mamba.http.HTTPErrorResponse(self, 404, "Not Found").send()
		else:
			mamba.http.HTTPErrorResponse(self, 400, "Bad Request").send()


class document(mamba.task.Request):
	
	def main(self):
		match = re.match("/document/([0-9]+)", self.http.path)
		if match == None:
			mamba.http.HTTPErrorResponse(self, 400, "Bad Request").send()
		else:
			document = int(match.group(1))
			textmining = database.Connect("textmining")
			sql = "SELECT * FROM documents WHERE document=%d;" % document
			records = textmining.query(sql).dictresult()
			if len(records):
				text = "\n".join(mamba.util.string_to_bytes(records[0]["text"]).split("\t"))
				mamba.http.HTTPResponse(self, text, "text/plain").send()
			else:
				mamba.http.HTTPErrorResponse(self, 404, "Not Found").send()


class network(mamba.task.Request):
	
	def main(self):
		dictionary = database.Connect("dictionary")
		stringdb = database.Connect("string")
		rest = mamba.task.RestDecoder(self)
		qentities = []
		if "entities" in rest:
			qentities = rest["entities"].split("\n")
		qexisting = []
		if "existing" in rest:
			qexisting = rest["existing"].split("\n")
		qmaxscore = 1000
		if "maxscore" in rest:
			qmaxscore = int(1000*float(rest["maxscore"]))
		qscore = 0;
		if "score" in rest:
			qscore = int(1000*float(rest["score"]))
		qadditional = 0
		if "additional" in rest:
			qadditional = int(rest["additional"])
			qselected = []
			if "selected" in rest:
				qselected = rest["selected"].split("\n")
			else:
				qselected = qentities+qexisting
			sql1 = ",".join(["'%s'" % pg.escape_string(x) for x in qselected])
			sql2 = ",".join(["'%s'" % pg.escape_string(x) for x in qentities+qexisting])
			sql = "SELECT entity2,sum(score) AS sum FROM links WHERE entity1 IN (%s) AND entity2 NOT IN (%s) AND score >= %d GROUP BY entity2 ORDER BY sum DESC LIMIT %d;" % (sql1, sql2, qscore, qadditional)
			for (entity, score) in stringdb.query(sql).getresult():
				qentities.append(entity)
		data = {}
		data["nodes"] = []
		for qentity in qentities:
			qtype, qid = qentity.split(".", 1)
			qtype = int(qtype)
			node = entity_dict(qtype, qid, dictionary)
			image = database.image(qtype, qid, dictionary)
			if image != None:
				node["image"] = image
			sequence = database.sequence(qtype, qid, dictionary)
			if sequence != "":
				node["sequence"] = sequence
			data["nodes"].append(node)
		data["edges"] = []
		sql1 = ",".join(["'%s'" % pg.escape_string(x) for x in qentities])
		sql2 = ",".join(["'%s'" % pg.escape_string(x) for x in qexisting])
		if len(qentities):
			if len(qexisting):
				sql = "SELECT * FROM links WHERE entity1 IN (%s) AND ((entity2 IN (%s) AND entity1 < entity2) OR (entity2 IN (%s) AND score < %d)) AND score >= %d;" % (sql1, sql1, sql2, qmaxscore, qscore)
			else:
				sql = "SELECT * FROM links WHERE entity1 IN (%s) AND entity2 IN (%s) AND entity1 < entity2 AND score >= %d;" % (sql1, sql1, qscore)
		else:
			if len(qexisting):
				sql = "SELECT * FROM links WHERE entity1 IN (%s) AND entity2 IN (%s) AND entity1 < entity2 AND score < %d AND score >= %d;" % (sql2, sql2, qmaxscore, qscore) 
		for (entity1, entity2, nscore, fscore, pscore, ascore, escore, dscore, tscore, score) in stringdb.query(sql).getresult():
			scores = {}
			if nscore > 0:
				scores["neighborhood"] = float(nscore)/1000
			if fscore > 0:
				scores["fusion"] = float(fscore)/1000
			if pscore > 0:
				scores["cooccurrence"] = float(pscore)/1000
			if ascore > 0:
				scores["coexpression"] = float(ascore)/1000
			if escore > 0:
				scores["experiments"] = float(escore)/1000
			if dscore > 0:
				scores["databases"] = float(dscore)/1000
			if tscore > 0:
				scores["textmining"] = float(tscore)/1000
			edge = {}
			edge["source"] = entity1
			edge["target"] = entity2
			edge["scores"] = scores
			data["edges"].append(edge)
		mamba.http.HTTPResponse(self, json.dumps(data, separators=(',',':'), sort_keys=True), "application/ld+json").send()
