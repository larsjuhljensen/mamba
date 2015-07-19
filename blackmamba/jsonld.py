import json
import pg
import re

import database
import mamba.task
import mamba.util


def entity_dict(qtype, qid):
	if qtype >= 0:
		return {"@id" : "stringdb:%d.%s" % (qtype, qid)}
	elif qtype == -1:
		return {"@id" : "stitchdb:%s" % qid}
	elif qtype == -2:
		return {"@id" : "taxonomy:%s" % qid}
	elif qtype <= -21 and qtype >= -24:
		return {"@id" : "%s" % qid}
	elif qtype == -25:
		return {"@id" : "%s" % qid}
	elif qtype == -26:
		return {"@id" : "%s" % qid}
	elif qtype == -27:
		return {"@id" : "%s" % qid}
	else:
		return {"@id" : qid}

	
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
		rest = mamba.task.RestDecoder(self)
		qentities = []
		if "entities" in rest:
			qentities = rest["entities"].split("\n")
		qexisting = []
		if "existing" in rest:
			qexisting = rest["existing"].split("\n")
		qscore = 0.0;
		if "score" in rest:
			qscore = float(rest["score"])
		data = {}
		data["nodes"] = []
		dictionary = database.Connect("dictionary")
		for qentity in qentities:
			qtype, qid = qentity.split(".", 1)
			qtype = int(qtype)
			node = {}
			node["@id"] = "_:%d.%s" % (qtype, qid)
			node["name"] = database.preferred_name(qtype, qid, dictionary)
			image = database.image(qtype, qid, dictionary)
			if image != None:
				node["image"] = image
			data["nodes"].append(node)
		data["edges"] = []
		stringdb = database.Connect("string")
		entities_sql = ",".join(["'%s'" % pg.escape_string(x) for x in qentities])
		if len(qexisting):
			existing_sql = ",".join(["'%s'" % pg.escape_string(x) for x in qexisting])
			sql = "SELECT * FROM links WHERE entity1 IN (%s) AND ((entity2 IN (%s) AND entity1 < entity2) OR entity2 IN (%s)) AND score >= %d;" % (entities_sql, entities_sql, existing_sql, int(1000*qscore))
		else:
			sql = "SELECT * FROM links WHERE entity1 IN (%s) AND entity2 IN (%s) AND entity1 < entity2 AND score >= %d;" % (entities_sql, entities_sql, int(1000*qscore))
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
