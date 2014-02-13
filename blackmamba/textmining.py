import math
import pg
import database
import html
import mamba.task
import xpage


class Textmining(xpage.XAjaxTable):

	def add_head(self):
		self.xtable.addhead("Name", "Z-score", "Confidence")

	def add_row(self, row, name, stars, format):
		if format == "html":
			self.xtable.addrow('''<span class="silent_link" onclick="open_popup(); blackmamba_header(%d,'%s','%s'); blackmamba_pager('Comentions','type1=%d&id1=%s&type2=%d&id2=%s',5,1,'%s');">%s</span>''' % (row["type2"], row["id2"], "blackmamba_popup_header", row["type1"], row["id1"], row["type2"], row["id2"], "blackmamba_popup_body", name), "%.1f" % row["evidence"], stars)
		elif format == "json":
			visible = "true"
			if "visible" in row and not row["visible"]:
				visible = "false"
			url = "http://%s/Entity?documents=10&type1=%d&type2=%d&id1=%s&id2=%s" % (self.http.headers["host"], row["type1"], row["type2"], row["id1"], row["id2"])
			self.json.append('''"%s":{"name":"%s","evidence":"%f","score":%f,"visible":%s,"url":"%s"}'''% (row["id2"], name, row["evidence"], row["score"], visible, url))

	def get_rows(self, rest, filter):
		qtype1 = int(rest["type1"])
		qtype2 = int(rest["type2"])
		qid1 = rest["id1"]
		if qtype2 == -1:
			return xpage.XAjaxTable.get_rows(self, rest)
		else:
			dictionary = database.Connect("dictionary")
			group = {}
			for row in dictionary.query("SELECT id1,id2 FROM groups WHERE type1=%d AND type2=%d" % (qtype2, qtype2)).getresult():
				a,b = row
				if a not in group:
					group[a] = set()
				if b not in group:
					group[b] = set()
				group[a].add(b)
				group[b].add(a)

			textmining = database.Connect(self.action.lower())
			sql = "SELECT * FROM pairs WHERE type1=%d AND id1='%s' AND type2=%d AND score>=0.5;" % (qtype1, pg.escape_string(qid1), qtype2)
			rescored_pairs = []
			for row in textmining.query(sql).getresult():
				qid2 = row[3]
				res = textmining.query("SELECT count FROM counts WHERE type=%d AND id='%s';" % (qtype2, qid2)).getresult()
				count = 0
				if len(res):
					count = int(res[0][0])
				evidence = float(row[4])
				score = float(row[5])
				rescore = evidence * math.log(count+1, 2)
				rescored_pairs.append((rescore, evidence, score, qid2))
			rescored_pairs.sort(reverse=True)

			used = set()
			for line in open(mamba.setup.config().globals["hidden"]):
				entity_type, identifier = line[:-1].split("\t")
				if int(entity_type) == qtype2:
					used.add(identifier)

			rows = []
			for rescore, evidence, score, qid2 in rescored_pairs:
				if qid2 not in used or not filter:
					row = {}
					row["type1"] = qtype1
					row["type2"] = qtype2
					row["id1"] = qid1
					row["id2"] = qid2;
					row["evidence"] = evidence
					row["score"] = score
					row["visible"] = qid2 not in used
					rows.append(row)
					used.add(qid2)
					if qid2 in group:
						for qid3 in group[qid2]:
							used.add(qid3)

			return sorted(rows, key=lambda row: row["evidence"], reverse=True)

	def get_sql(self, rest, filter):
		return "SELECT * FROM pairs WHERE type1=%d AND id1='%s' AND type2=%d AND score>=0.5 ORDER BY evidence DESC" % (int(rest["type1"]), pg.escape_string(rest["id1"]), int(rest["type2"]))

	def create_table(self, rest, parent=None):
		if "format" not in rest or rest["format"] == "html":
			popup = html.XDiv(parent, "popup", "blackmamba_popup")
			html.XDiv(popup, "popup_header", "blackmamba_popup_header")
			html.XDiv(popup, "popup_body", "blackmamba_popup_body")
		return xpage.XAjaxTable.create_table(self, rest, parent)
