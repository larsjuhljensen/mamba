import pg
import random
import re
import database
import html
import xpage
import mamba.task


class StringNetwork(mamba.task.Request):
	
	def main(self):
		rest = mamba.task.RestDecoder(self)
		
		qtype1 = int(rest["type1"])
		qid1 = rest["id1"]
		qtype2 = int(rest["type2"])
		limit = int(rest["limit"])
		
		scores = {}
		sql = "SELECT id2, score FROM pairs WHERE type1=%d AND id1='%s' AND type2=%d ORDER BY score DESC LIMIT %d;" % (qtype1, pg.escape_string(qid1), qtype2, limit)
		for evidence in ["knowledge", "textmining", "predictions"]:
			connection = database.Connect(evidence)
			for row in connection.query(sql).getresult():
				entity = "%d.%s" % (qtype2, row[0])
				score = row[1]
				if entity not in scores or score > scores[entity]:
					scores[entity] = score
		entities = sorted(scores.iterkeys(), key=scores.get, reverse=True)[0:limit]
		payload = "http://%s/%032x/StringPayload/%d.%s" % (self.http.headers["Host"], random.getrandbits(128), qtype1, pg.escape_string(qid1))
		url = "%s?caller_identity=blackmamba&identifiers=%s&limit=0&network_flavor=confidence&required_score=700&external_payload=%s" % (self.get_url(), "%0D".join(entities), payload)
		mamba.http.HTTPRedirect(self, url).send()


class StringNetworkImage(StringNetwork):
	
	def get_url(self):
		return "http://string-db.org/api/image/networkList"


class StringNetworkLink(StringNetwork):
	
	def get_url(self):
		return "http://string-db.org/newstring_cgi/show_network_section.pl"


class StringPayload(mamba.task.Request):

	def main(self):
		action = self.http.get_action()
		design = xpage.get_design()
		if action == "StringPayload":
			json = '''{"edges_webservice":"http://%s/StringPayloadEdges","name":"%s"}''' % (self.http.headers["Host"], design["TITLE"])
		elif re.match("-?[0-9]+\.", action):
			json = '''{"nodes_webservice":"http://%s/StringPayloadEntity/%s","name":"%s"}''' % (self.http.headers["Host"], action, design["TITLE"])
		else:
			json = '''{"nodes_webservice":"http://%s/StringPayloadFigure/%s","name":"%s"}''' % (self.http.headers["Host"], action, design["TITLE"])
		mamba.http.HTTPResponse(self, json, "application/json").send()


class StringPayloadEdges(mamba.task.Request):
	
	def main(self):
		rest = mamba.task.RestDecoder(self)
		tsv = []
		only_internal = False
		if "only_internal" in rest:
			only_internal = bool(rest["only_internal"])
		if "identifiers" in rest:
			entities = rest["identifiers"].split(" ")
			for evidence in ["knowledge", "textmining", "predictions"]:
				connection = database.Connect(evidence)
				for entity1 in entities:
					qtype, qid = entity1.split(".", 1)
					sql = "SELECT id2, score FROM pairs WHERE type1=%d AND id1='%s' AND type2=%d AND score >= 0.5" % (int(qtype), pg.escape_string(qid), int(qtype))
					for row in connection.query(sql).getresult():
						entity2 = "%s.%s" % (qtype, row[0])
						if (entity2 in entities) == only_internal:
							score = 0.9*row[1]/5
							tsv.append("%s\t%s\t%s\t%f\n" % (entity1, entity2, evidence, score))
		mamba.http.HTTPResponse(self, "".join(tsv), "text/plain").send()


class StringPayloadNodes(mamba.task.Request):
	
	def get_colors(self, entities):
		return {}
	
	def get_links(self, entities):
		return {}
	
	def main(self):
		rest = mamba.task.RestDecoder(self)
		tsv = []
		if "identifiers" in rest:
			entities = rest["identifiers"].split(" ")
			colors = self.get_colors(entities)
			links = self.get_links(entities)
			for entity in entities:
				color = ""
				if entity in colors:
					color = colors[entity]
				link = ""
				if entity in links:
					link = links[entity]
				tsv.append("%s\t%s\t\t%s\n" % (entity, color, link))
		mamba.http.HTTPResponse(self, "".join(tsv), "text/plain").send()


class StringPayloadEntity(StringPayloadNodes):
	
	def get_colors(self, entities):
		colors = {}
		scores = self.get_scores(entities)
		for entity in scores:
			color = int(255*(1-scores[entity]/5))
			colors[entity] = "#%02x%02x%02x" % (color, color, color)
		return colors
	
	def get_links(self, entities):
		links = {}
		search = mamba.setup.config().sections["SEARCH"]
		qtype2, qid2 = self.http.get_action().split(".", 1)
		for entity in entities:
			qtype1, qid1 = entity.split(".", 1)
			if qtype1 in search:
				links[entity] = "http://"+self.http.headers["Host"]+search[qtype1]+qid1
		return links
	
	def get_scores(self, entities):
		scores = {}
		qtype2, qid2 = self.http.get_action().split(".", 1)
		for evidence in ["knowledge", "textmining", "predictions"]:
			connection = database.Connect(evidence)
			if connection != None:
				for entity in entities:
					qtype1, qid1 = entity.split(".", 1)
					sql = "SELECT score FROM pairs WHERE type1=%d AND id1='%s' AND type2=%d AND id2='%s';" % (int(qtype1), pg.escape_string(qid1), int(qtype2), pg.escape_string(qid2))
					rows = connection.query(sql).getresult()
					if len(rows):
						score = float(rows[0][0])
						if entity not in scores or score > scores[entity]:
							scores[entity] = score
		return scores


class StringPayloadFigure(StringPayloadNodes):
	
	def get_colors(self, entities):
		colors = {}
		visualization = database.Connect("visualization")
		if visualization != None:
			label = self.http.get_action()
			for entity in entities:
				qtype, qid = entity.split(".", 1)
				sql = "SELECT color FROM colors WHERE type=%d AND id='%s' AND label='%s';" % (int(qtype), pg.escape_string(qid), pg.escape_string(label))
				rows = visualization.query(sql).getresult()
				if len(rows):
					colors[entity] = rows[0][0]
		return colors
