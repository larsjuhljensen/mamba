import json
import pg

import database
import mamba.task
import mamba.util


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
			node = database.entity_dict(qtype, qid, dictionary)
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
