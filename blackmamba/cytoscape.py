import json
import pg

import database
import visualization
import mamba.task
import mamba.util


class network(mamba.task.Request):
	
	def main(self):
		dictionarydb = database.Connect("dictionary")
		stringdb = database.Connect("string")
		visualizationdb = database.Connect("visualization")
		rest = mamba.task.RestDecoder(self)
		if "database" in rest:
			networkdb = database.Connect(rest["database"])
		else:
			networkdb = database.Connect("string")
		qentities = []
		if "entities" in rest:
			qentities = rest["entities"].split("\n")
		qexisting = []
		if "existing" in rest:
			qexisting = rest["existing"].split("\n")
		qfilter = None
		if "filter" in rest:
			qfilter = rest["filter"]
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
			sql3 = ""
			if qfilter is not None:
				sql3 = "AND entity2 LIKE '%s'" % pg.escape_string(qfilter)
			sql = "SELECT entity2,sum(score) AS sum FROM links WHERE entity1 IN (%s) AND entity2 NOT IN (%s) %s AND score >= %d GROUP BY entity2 ORDER BY sum DESC LIMIT %d;" % (sql1, sql2, sql3, qscore, qadditional)
			for (entity, score) in networkdb.query(sql).getresult():
				qentities.append(entity)
		data = {}
		data["nodes"] = []
		for qentity in qentities:
			if "." in qentity:
				qtype, qid = qentity.split(".", 1)
				qtype = int(qtype)
			else:
				qtype = -1
				qid = qentity
			node = database.entity_dict(qtype, qid, dictionarydb)
			value = database.image(qtype, qid, dictionarydb)
			if value != None:
				node["image"] = value
			value = database.pharos(qtype, qid, dictionarydb)
			if value != ():
				node["pharos family"] = value[0]
				node["pharos level"] = value[1]
			value = database.sequence(qtype, qid, dictionarydb)
			if value != "":
				node["sequence"] = value
			value = database.smiles(qtype, qid, dictionarydb)
			if value != "":
				node["smiles"] = value
			for label, score in visualization.scores_dict("subcell_cell_%%", qtype, qid, visualizationdb).iteritems():
				if ":" not in label:
					node["compartment "+label] = score
			for label, score in visualization.scores_dict("tissues_body_%%", qtype, qid, visualizationdb).iteritems():
				if ":" not in label:
					node["tissue "+label] = score
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
		for (entity1, entity2, sscore, nscore, fscore, pscore, ascore, escore, dscore, tscore, score) in networkdb.query(sql).getresult():
			scores = {}
			if sscore > 0:
				scores["similarity"] = float(sscore)/1000
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
