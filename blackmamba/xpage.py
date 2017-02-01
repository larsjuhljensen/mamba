import hashlib
import math
import os
import pg
import re
import urllib
import pandas as pd
import numpy as np

import database
import html
import visualization

import mamba.setup
import mamba.task

_single_design = None

def get_design():
	global _single_design
	if not _single_design:
		_single_design = {}
		_single_design["TITLE"] = "BlackMamba"
		_single_design["SUBTITLE"] = ""
		_single_design["CONTENT"] = ""
		_single_design["FOOTER"] = ""
		if "design" in mamba.setup.config().globals:
			name = None
			text = []
			for line in open(mamba.setup.config().globals["design"]):
				match = re.match("\[([A-Z]+(:([A-Z]+))?)\][ \t\r]*\n", line)
				if match:
					if name != None:
						_single_design[name] = "".join(text).strip()
					name = match.group(1)
					text = []
				else:
					text.append(line)
			if name != None:
				_single_design[name] = "".join(text).strip()
	return _single_design


class XAjaxContainer(html.XDiv):
	
	def __init__(self, parent, url, query, limit=10, page=1):
		md5 = hashlib.md5()
		md5.update(url+query)
		container = md5.hexdigest()
		html.XDiv.__init__(self, parent, "ajax_table", container)
		html.XScript(self, "blackmamba_pager('%s', '%s', %d, %d, '%s');" % (url, query, limit, page, container))


class XPagesDiv(html.XDiv):

	def __init__(self, parent, url, rest, count):
		html.XDiv.__init__(self, parent, "table_pages")
		limit = int(rest["limit"])
		if count > limit:
			page = int(rest["page"])
			query = []
			for key in rest:
				if key != "limit" and key != "page":
					query.append(urllib.quote(key)+"="+urllib.quote(rest[key]))
			query = '&'.join(query)
			container = rest["container"]
			if page > 1:
				html.XText(html.XSpan(self, {"class":"silent_link","id":container+"_prev","onclick":"blackmamba_pager('%s', '%s', %d, %d, '%s')" % (url, query, limit, page-1, container)}), "&lt;&nbsp;Prev")
			if count > page*limit:
				if page > 1:
					html.XText(self, "&nbsp;|&nbsp;")
				html.XText(html.XSpan(self, {"class":"silent_link","id":container+"_next","onclick":"blackmamba_pager('%s', '%s', %d, %d, '%s')" % (url, query, limit, page+1, container)}), "Next&nbsp;&gt;")


class XAjaxTable(mamba.task.Request):
	
	def create_table(self, rest, parent=None):
		dictionary = database.Connect("dictionary")
		format = "html"
		if "format" in rest:
			format = rest["format"]
		filter = False
		if format == "html" and "id2" not in rest:
			filter = True
		rows = self.get_rows(rest, filter)
		if format == "html":
			if rows is not None:
				if len(rows):
					self.xtable = html.XDataTable(parent)
					self.xtable["width"] = "100%"
					self.add_head()
				else:
					html.XP(parent, "No evidence of this type.", attr = {"class" : "clear"})
			else:
				html.XP(parent, "No evidence of this type.", attr = {"class" : "clear"})
		elif format == "json":
			self.json = []
		limit = 10
		if "limit" in rest:
			limit = int(rest["limit"])
		page = 1
		if "page" in rest:
			page = int(rest["page"])
		count = 0
		if rows is not None:
			if len(rows):
				for row in rows:
					count += 1
					if count > limit*page:
						break
					if count > limit*(page-1):
						name = html.xcase(database.preferred_name(int(rest["type2"]), row["id2"], dictionary))
						stars = int(math.ceil(row["score"]))
						stars = '<span class="stars">%s</span>' % "".join(["&#9733;"]*stars + ["&#9734;"]*(5-stars))
						self.add_row(row, name, stars, format)
		return count
	
	def get_rows(self, rest, filter):
		limit = 10
		if "limit" in rest:
			limit = int(rest["limit"])
		page = 1
		if "page" in rest:
			page = int(rest["page"])
		evidence = database.Connect(self.action.lower())
	def get_sql(self, rest, filter):
		if "id2" in rest:
			if filter:
				return "SELECT * FROM pairs WHERE type1=%d AND id1='%s' AND type2=%d AND id2='%s' AND explicit='t' ORDER BY score DESC" % (int(rest["type1"]), pg.escape_string(rest["id1"]), int(rest["type2"]), pg.escape_string(rest["id2"]))
			else:
				return "SELECT * FROM pairs WHERE type1=%d AND id1='%s' AND type2=%d AND id2='%s' ORDER BY score DESC" % (int(rest["type1"]), pg.escape_string(rest["id1"]), int(rest["type2"]), pg.escape_string(rest["id2"]))
		else:
			if filter:
				return "SELECT * FROM pairs WHERE type1=%d AND id1='%s' AND type2=%d AND explicit='t' ORDER BY score DESC" % (int(rest["type1"]), pg.escape_string(rest["id1"]), int(rest["type2"]))
			else:
				return "SELECT * FROM pairs WHERE type1=%d AND id1='%s' AND type2=%d ORDER BY score DESC" % (int(rest["type1"]), pg.escape_string(rest["id1"]), int(rest["type2"]))
	
	def main(self):
		self.action = self.http.get_action()
		rest = mamba.task.RestDecoder(self)
		format = "html"
		if "format" in rest:
			format = rest["format"]
		if format == "html":
			title = self.action
			if "title" in rest:
				title = rest["title"]
			xroot = html.XNode(None)
			html.XDiv(xroot, "table_title").text = title
			xpages = html.XNode(xroot)
			XPagesDiv(xpages, self.action, rest, self.create_table(rest, xroot))
			mamba.http.HTTPResponse(self, xroot.tohtml()).send()
		elif format == "json":
			limit = 10
			if "limit" in rest:
				limit = int(rest["limit"])
			page = 1
			if "page" in rest:
				page = int(rest["page"])
			count = self.create_table(rest)
			more = "false"
			if count > page*limit:
				more = "true"
			mamba.http.HTTPResponse(self, "[{%s},%s]\n" % (",".join(self.json), more), "application/json").send()


class Combined(XAjaxTable):
	
	def add_head(self):
		self.xtable.addhead("Name", "Source", "Evidence")
	
	def add_row(self, row, name, stars, format):
		if format == "html":
			if 'url' in row and row['url'] != "":
				link = '<a class="silent_link" target = _blank href="%s">%%s</a>' % (row["url"])
				self.xtable.addrow(link % name, link % row["source"], link % row["evidence"])
			else:
				self.xtable.addrow(name,row["source"],row["evidence"])
		elif format == "json":
			visible = "false"
			if row["explicit"] == "t":
				visible = "true"
			if "url" in row and row["url"] != "":
				self.json.append('''"%s":{"name":"%s","source":"%s","evidence":"%s","visible":%s,"url":"%s"}'''% (row["id2"], name, row["source"], row["evidence"], visible, row["url"]))
			else:
				self.json.append('''"%s":{"name":"%s","source":"%s","evidence":"%s","visible":%s}'''% (row["id2"], name, row["source"], row["evidence"], visible))
	
	def get_rows(self, rest, filter):
		db_list = rest["dbs"].split(',')
		evidences = []
		limit = int(rest["limit"])*int(rest["page"])+1
		for db in db_list:
			evidence = database.Connect(db)
			evidences.extend(evidence.query(self.get_sql(rest, filter)+" LIMIT %d;" % (limit)).dictresult())
		return evidences
						
	def get_sql(self, rest, filter):
		if filter:
			return "SELECT * FROM pairs WHERE type1=%d AND id1='%s' AND type2=%d AND explicit='t' AND score>=2 ORDER BY score DESC" % (int(rest["type1"]), pg.escape_string(rest["id1"]), int(rest["type2"]))
		else:
			return "SELECT * FROM pairs WHERE type1=%d AND id1='%s' AND type2=%d AND score>=2 ORDER BY score DESC" % (int(rest["type1"]), pg.escape_string(rest["id1"]), int(rest["type2"]))


class Groups(XAjaxTable):
	def create_table(self, rest, parent=None):
		dictionary = database.Connect("dictionary")
		species = mamba.setup.config().sections['HOMOLOGS'][rest["key"]]
		format = "html"
		if "format" in rest:
			format = rest["format"]
		filter = False
		if format == "html":
			filter = True
			self.xtable = html.XDataTable(parent)
			self.xtable["width"] = "100%"
		elif format == "json":
			self.json = []
		limit = int(rest["limit"])
		page = int(rest["page"])
		count = 0
		rows = self.get_rows(rest, species, filter)
		if len(rows):
			self.add_head()
			for r in rows:
				count += 1
				if count > page*limit:
					break
				if count > limit*(page-1):
	
					name = html.xcase(database.preferred_name(int(r["type1"]), r["id1"], dictionary))
					organism = html.xcase(database.preferred_type_name(int(r["type1"]), dictionary))
					self.add_row(r, name, organism, format)
		else:
			html.XText(parent,"No evidences in this channel")
		return count
	
	def add_head(self):
		self.xtable.addhead("Name", "Organism")
	
	def add_row(self, row, name, organism, format):
		if format == "html":
			if 'url' in row and row['url'] != "":
				link = '<a class="silent_link" href="%s">%%s</a>' % (row["url"])
				self.xtable.addrow(link % name, link % organism)
			else:
				self.xtable.addrow(name,organism)
		elif format == "json":
			visible = "true"
			if "url" in row and row["url"] != "":
				self.json.append('''"%s":{"name":"%s","organism":"%s","visible":%s,"url":%s}'''% (row["id1"], name,organism, visible,row["url"]))
			else:	
				self.json.append('''"%s":{"name":"%s","organism":"%s","visible":%s}'''% (row["id1"], name,organism, visible))
			
	def get_rows(self, rest, filter):
		db = rest["db"]
		evidence = database.Connect(db)
		return evidence.query(self.get_sql(rest, filter)).dictresult()
		
	def get_sql(self, rest, species, filter):
		sql = "SELECT id1,type1 FROM groups where type2 = %d and id1!='%s' and type1 IN (%s) and id2 IN (SELECT id2 FROM groups WHERE type1=%d AND id1='%s' AND type2=%d)" % (int(rest["key"]),pg.escape_string(rest["id1"]), species,int(rest["type1"]),pg.escape_string(rest["id1"]),int(rest["key"]))
		return sql

class OrthoGroups(Groups):
        def create_table(self, rest, parent=None):
                dictionary = database.Connect("dictionary")
		species = mamba.setup.config().sections['HOMOLOGS'][rest["key"]]
                format = "html"
                if "format" in rest:
                        format = rest["format"]
                filter = False
                if format == "html":
                        filter = True
                        self.xtable = html.XDataTable(parent)
                        self.xtable["width"] = "100%"
                elif format == "json":
                        self.json = []
                limit = int(rest["limit"])
                page = int(rest["page"])
                count = 0
                rows = self.get_rows(rest, species, filter)
                if len(rows):
                        self.add_head()
                        for r in rows:
                                count += 1
                                if count > page*limit:
                                        break
                                if count > limit*(page-1):
                                        name = html.xcase(database.preferred_name(int(r["type1"]), r["id1"], dictionary))
                                        organism = html.xcase(database.preferred_type_name(int(r["type1"]), dictionary))
                                        homology = html.xcase(r["homology"])
                                        self.add_row(r, name, organism, homology, format)
                else:
                        html.XText(parent,"No evidences in this channel")
                return count

        def add_head(self):
                self.xtable.addhead("Name", "Organism", "Homology")

        def add_row(self, row, name, organism, homology, format):
                if format == "html":
                        if 'url' in row and row['url'] != "":
                                link = '<a class="silent_link" href="%s">%%s</a>' % (row["url"])
                                self.xtable.addrow(link % name, link % organism, link % homology)
                        else:
                                self.xtable.addrow(name, organism, homology)
                elif format == "json":
                        visible = "true"
                        if "url" in row and row["url"] != "":
                                self.json.append('''"%s":{"name":"%s", "organism":"%s", "homology":%s, "visible":%s, "url":%s}'''% (row["id1"], name, organism, homology, visible,row["url"]))
                        else:
                                self.json.append('''"%s":{"name":"%s", "organism":"%s", "homology":%s, "visible":%s}'''% (row["id1"], name, organism, homology, visible))

        def get_rows(self, rest, species, filter):
                db = rest["db"]
		result = []
                evidence = database.Connect(db)
                groups = evidence.query(self.get_sql(rest, species, filter)).dictresult()
                orthologs = evidence.query(self.get_orthologs_sql(rest, species, filter)).getresult()
		if len(orthologs):
			orthologs = [r[0] for r in orthologs]
		result = [dict(i,**{'homology':'ortholog'}) if  i.values()[0] in orthologs or i.values()[1] in orthologs else dict(i,**{'homology':'paralog'}) for i in groups]
                
		return result

        def get_orthologs_sql(self, rest, species,  filter):
		sql = "SELECT id2 FROM orthologs WHERE type1=%d AND id1 = '%s' AND type2 IN (%s);" % (int(rest["type1"]),pg.escape_string(rest["id1"]), species)
		return sql

class CorrOrthoGroups(OrthoGroups):
        def add_head(self):
                self.xtable.addhead("Name", "Organism", "Homology", "Correlation")

        def add_row(self, row, name, organism, homology, format):
                if format == "html":
                        if row.has_key("url") and row["url"] !="":
                                link = '<a class="silent_link" target = _blank href="%s">%%s</a>' % (row["url"])
                                self.xtable.addrow(link % name, link % organism, link % homology, link % row["correlation"])
                        else:
                                self.xtable.addrow(name, organism, homology, row["correlation"])
                elif format == "json":
                        visible = "true"
			self.json.append('''"%s":{"name":"%s","organism":"%s", "homology": %s, "correlation": %s, "visible":%s,"url":%s}'''% (row["id1"], name,organism, homology, row["correlation"], visible,row["url"]))

        def get_rows(self, rest, species, filter):
                ortho_evidences = OrthoGroups.get_rows(self,rest,species, filter)
                organism = int(rest["type1"])
                id = pg.escape_string(rest["id1"])
                entity_type = int(rest["type2"])

                return self.get_correlation(ortho_evidences, organism, id, entity_type)

	def get_entity_sql(self, id1,id2, type1, type2, entity_type, common):
		if len(common):
		        csql = ",".join(["'%s'" % id for id in common])
        		sql = "SELECT id1, id2, score FROM pairs WHERE type1 IN (%d, %d) AND id1 IN('%s', '%s') AND type2 = %d  AND id2 IN (%s)" % (type1, type2,id1, id2, entity_type, csql)
		else:
			sql = "SELECT id1, id2, score FROM pairs WHERE type1 IN (%d, %d) AND id1 IN('%s', '%s') AND type2 = %d" % (type1, type2,id1, id2, entity_type)

        	return sql
	
	def build_url(self, id, type):
	        fix_url = '/Entity?figures=tissues_body_human&knowledge=10&experiments=10&homologs=10&type1=TYPE&type2=-25&id1=ID'
        	
		return fix_url.replace('ID',id).replace('TYPE',type)

	def get_common_sql(self, type2):
		sql = "SELECT DISTINCT id FROM colors WHERE type=%d" % type2
		return sql

	def get_correlation(self, data, type2, id2, entity_type):
		evidences = []
		if len(data):
			integration_db = database.Connect("integration")
			common = mamba.setup.config().sections['LABELS'][str(entity_type)].split(',')
			vectors = []
			for row in data:
				evidence = {}
				id1 = row["id1"]
				type1 = row["type1"]
				homology = row["homology"]
				url = self.build_url(id1,str(type1))
				evidence.update({"type1":type1, "id1":id1, "homology":homology, "url":url})
				vectors = integration_db.query(self.get_entity_sql(id1,id2, type1, type2, entity_type, common)).getresult()
				if(len(vectors) > 0):
					df = pd.DataFrame(vectors)
					df = df.pivot(index=0, columns=1, values=2)
					df = df.fillna(0)
					if df.shape[0] > 1:
						pcorrelation = np.corrcoef(df.values[0],df.values[1],0)[0,1]
						#pcorrelation, pvalue  = pearsonr(df.iloc[0],df.iloc[1])
						evidence.update({"correlation": "%.2f" % pcorrelation})
						evidences.append(evidence)
		if len(evidences) > 1:
			dfEvidences = pd.DataFrame.from_dict(evidences)
			results = dfEvidences.sort_values(by=['homology','correlation'], ascending=[True, False]).reset_index().T.to_dict().values()
		else:
			results = evidences
		return results

class Knowledge(XAjaxTable):
	
	def add_head(self):
		self.xtable.addhead("Name", "Source", "Evidence", "Confidence")
	
	def add_row(self, row, name, stars, format):
		if format == "html":
			if 'url' in row and row['url'] != "":
				name = html.XLink(None, row['url'], name, '_blank', {"class":"silent_link"})
			self.xtable.addrow(name, row["source"], row["evidence"], stars)
		elif format == "json":
			visible = "false"
			if row["explicit"] == "t":
				visible = "true"
			if "url" in row and row["url"] != "":
				self.json.append('''"%s":{"name":"%s","source":"%s","evidence":"%s","score":%s,"visible":%s,"url":"%s"}'''% (row["id2"], name, row["source"], row["evidence"], row["score"], visible, row["url"]))
			else:
				self.json.append('''"%s":{"name":"%s","source":"%s","evidence":"%s","score":%s,"visible":%s}'''% (row["id2"], name, row["source"], row["evidence"], row["score"], visible))


class KnowledgeIndirect(XAjaxTable):
	
	def create_table(self, rest, parent=None):
		dictionary = database.Connect("dictionary")
		format = "html"
		if "format" in rest:
			format = rest["format"]
		filter = False
		if format == "html":
			filter = True
			self.xtable = html.XDataTable(parent)
			self.xtable["width"] = "100%"
		elif format == "json":
			self.json = []
		limit = int(rest["limit"])
		page = int(rest["page"])
		count = 0
		rows = self.get_rows(rest, filter)
		if len(rows):
			self.add_head()
			for r in rows:
				count += 1
				if count > page*limit:
					break
				if count > limit*(page-1):
					connection = html.xcase(database.preferred_name(int(rest["type2"]), r["id2"], dictionary))
					name = html.xcase(database.preferred_name(int(rest["type1"]), r["id1"], dictionary))
					#self.add_row(r, connection, name, format)
					table_rows[connection].append((r,name))
			
			for c in table_rows:
				span = len(table_rows[c])
				for r,name in table_rows[c]:
					self.add_row(r, c, name, format, span)
					span = 0
		else:
			html.XText(parent,"No evidences in this channel")
		return count
	
	def add_head(self):
		self.xtable.addhead("Connected by","Name", "Source", "Evidence", "Confidence")
	
	def get_rows(self, rest, filter):
		db = rest["db"]
		evidence = database.Connect(db)
		return evidence.query(self.get_sql(rest, filter)).dictresult()
	
	def add_row(self, row, connection, name, stars, format, span):
		if format == "html":
			source = link % row['source']
			evidence = link % row['evidence']
			if 'url' in row and row['url'] !="":
				link = '<a class="silent_link" target = _blank href="%s">%%s</a>' % (row["url"])
				name = link % name
				source = link % source
				evidence = link % evidence
				stars = link % stars
			if span > 0:
				c = (connection, {'rowspan': str(span)})
				self.xtable.addrow(c, name, source, evidence, stars)
			else:
				self.xtable.addrow(name, source, evidence, stars)
		elif format == "json":
			visible = "false"
			if row["explicit"] == "t":
				visible = "true"
			if "url" in row and row["url"] != "":
				self.json.append('''"%s":{"connection":"%s", "name":"%s","source":"%s","evidence":"%s","score":%s,"visible":%s,"url":"%s"}'''% (row["id2"], connection, name, row["source"], row["evidence"], row["score"], visible, row["url"]))
			else:
				self.json.append('''"%s":{"connection":"%s", "name":"%s","source":"%s","evidence":"%s","score":%s,"visible":%s}'''% (row["id2"], connection, name, row["source"], row["evidence"], row["score"], visible))
	
	def get_sql(self, rest, filter):
		return "SELECT type2 as type1, id2 as id1, id1 as id2, type1 as type2, evidence, score, explicit, url FROM pairs WHERE type1=%d AND type2 = %d AND id2!='%s' AND source = '%s' AND id1 IN (SELECT id2 FROM pairs WHERE type1=%d AND id1= '%s' AND type2=%d AND source = '%s' AND explicit='t');" % (int(rest["type2"]), int(rest["type1"]), pg.escape_string(rest["id1"]), pg.escape_string(rest["source"]),int(rest["type1"]),pg.escape_string(rest["id1"]), int(rest["type2"]),pg.escape_string(rest["source"]))


class Experiments(XAjaxTable):
	
	def add_head(self):
		self.xtable.addhead("Name", "Source", "Evidence", "Confidence")
	
	def add_row(self, row, name, stars, format):
		if format == "html":
			if "url" in row and row["url"] != "":
				name = html.XLink(None, row['url'], name, '_blank', {"class":"silent_link"})
			self.xtable.addrow(name, row["source"], row["evidence"], stars)
		elif format == "json":
			visible = "false"
			if row["explicit"] == "t":
				visible = "true"
			if "url" in row and row["url"] != "":
				self.json.append('''"%s":{"name":"%s","source":"%s","evidence":"%s","score":%s,"visible":%s,"url":"%s"}'''% (row["id2"], name, row["source"], row["evidence"], row["score"], visible, row["url"]))
			else:
				self.json.append('''"%s":{"name":"%s","source":"%s","evidence":"%s","score":%s,"visible":%s}'''% (row["id2"], name, row["source"], row["evidence"], row["score"], visible))


class Predictions(XAjaxTable):
	
	def add_head(self):
		self.xtable.addhead("Name", "Source", "Evidence", "Confidence")
	
	def add_row(self, row, name, stars, format):
		if format == "html":
			self.xtable.addrow(name, row["source"], row["evidence"], stars)
		elif format == "json":
			visible = "false"
			if row["explicit"] == "t":
				visible = "true"
			self.json.append('''"%s":{"name":"%s","source":"%s","evidence":"%s","score":%s,"visible":%s}'''% (row["id2"], name, row["source"], row["evidence"], row["score"], visible))


class Integration(XAjaxTable):
	
	def add_head(self):
		self.xtable.addhead("Name", "Confidence")
	
	def add_row(self, row, name, stars, format):
		if format == "html":
			self.xtable.addrow(name, stars)
		elif format == "json":
			self.json.append('''"%s":{"name":"%s","score":%s}''' % (row["id2"], name, row["score"]))
	
	def get_sql(self, rest, filter):
		if "id2" in rest:
			return "SELECT * FROM pairs WHERE type1=%d AND id1='%s' AND type2=%d AND id2='%s' ORDER BY score DESC" % (int(rest["type1"]), pg.escape_string(rest["id1"]), int(rest["type2"]), pg.escape_string(rest["id2"]))
		else:
			return "SELECT * FROM pairs WHERE type1=%d AND id1='%s' AND type2=%d ORDER BY score DESC" % (int(rest["type1"]), pg.escape_string(rest["id1"]), int(rest["type2"]))

		
class XPage(html.XNakedPage):
	
	def __init__(self, page_class=None, page_name=None):
		design = get_design()
		if page_name:
			html.XNakedPage.__init__(self, "%s - %s" % (design["TITLE"], page_name))
		else:
			html.XNakedPage.__init__(self, design["TITLE"])
		self.head.search = (design["TITLE"], "/OpenSearchDescription")
		if "CSS" in design:
			self.head.css += map(str.strip, design["CSS"].split("\n"))
		if page_class != None:
			key = "CSS:"+page_class.upper()
			if key in design:
				self.head.css += map(str.strip, design[key].split("\n"))
		if "KEYWORDS" in design:
			self.head.keywords += map(str.strip, design["KEYWORDS"].split("\n"))
		if page_class != None:
			key = "KEYWORDS:"+page_class.upper()
			if key in design:
				self.head.keywords += map(str.strip, design[key].split("\n"))
		if "SCRIPTS" in design:
			self.head.scripts += map(str.strip, design["SCRIPTS"].split("\n"))
		if page_class != None:
			key = "SCRIPTS:"+page_class.upper()
			if key in design:
				self.head.scripts += map(str.strip, design[key].split("\n"))
		left = html.XDiv(self.header, "header_left")
		title = design["TITLE"]
		subtitle = design["SUBTITLE"]
		if page_class != None:
			key = "TITLE:"+page_class.upper()
			if key in design:
				title = design[key]
			key = "SUBTITLE:"+page_class.upper()
			if key in design:
				subtitle = design[key]
		html.XLink(html.XH1(left), "/", title, attr = {"id" : "title"})
		html.XLink(html.XP(left), "/", subtitle, attr = {"id" : "subtitle"})
		if "LOGO" in design:
			if "LINK" in design:
				html.XImg(html.XLink(html.XDiv(self.header, "header_right"), design["LINK"]), design["LOGO"])
			else:
				html.XImg(html.XDiv(self.header, "header_right"), design["LOGO"])
		menu = html.XDiv(self.header, "menu")
		if "MENU" in design:
			for item in design["MENU"].split("\n"):
				if item.replace(" ", "").upper() == page_class.upper():
					html.XText(html.XSpan(menu), item)
				else:
					html.XLink(menu, item, item, None, {"class":"silent_link"})
		if "CONTENT" in design:
			html.XText(self.content, design["CONTENT"])
		if page_class != None:
			key = "CONTENT:"+page_class.upper()
			if key in design:
				html.XText(self.content, design[key])
		if page_class != None:
			key = "FOOTER:"+page_class.upper()
			if key in design:
				html.XText(self.footer, design[key])
		html.XText(self.footer, design["FOOTER"])


class AssociationsSection(html.XSection):

	def __init__(self, parent, qtype1, qid1, qtype2, dictionary = None, name = None):
		maptype = {}
		maptype[-21]   = "%s processes"
		maptype[-22]   = "%s localizations"
		maptype[-23]   = "%s functions"
		maptype[-25]   = "%s tissues"
		maptype[-26]   = "%s disease associations"
		maptype[-27]   = "%s environments"
		maptype[-33]   = "%s phenotypes"
		maptype[-35]   = "%s PTMs"
		maptype[-36]   = "%s phenotypes"
		maptype[-1]    = "Chemical compounds associated with %s"
		maptype[0]     = "Genes for %s"
		maptype[4896]  = "Fission yeast genes for %s"
		maptype[4932]  = "Budding yeast genes for %s"
		maptype[6239]  = "C. elegans genes for %s"
		maptype[7227]  = "Fly genes for %s"
		maptype[9606]  = "Human genes for %s"
		maptype[10090] = "Mouse genes for %s"
		maptype[10116] = "Rat genes for %s"
		if name == None:
			if dictionary == None:
				dictionary = database.Connect("dictionary")
			name = database.preferred_name(qtype1, qid1)
		if qtype2 in maptype:
			text = maptype[qtype2] % name
		else:
			text = name
		html.XSection.__init__(self, parent, html.xcase(text))


class EntityHeader(html.XNode):

	def __init__(self, parent, qtype, qid, dictionary = None, userdata = None):
		html.XNode.__init__(self, parent)
		try:
			if userdata == None:
				userdata = database.Connect("userdata")
		except:
			pass
		try:
			if dictionary == None:
				dictionary = database.Connect("dictionary")
		except:
			pass
		name = database.preferred_name(qtype, qid, dictionary)
		html.XP(self, "%s [%s]" % (html.xcase(name), qid), {"class":"name"})
		description = database.description(qtype, qid, dictionary, userdata)
		if description != "":
			html.XP(self, html.xcase(description), {"class":"description"})
		maxsyn = 5
		synonyms = database.synonyms(qtype, qid, dictionary, userdata)
		if len(synonyms):
			if len(synonyms) > 1 or synonyms[0].lower() != name.lower():
				text = "Synonyms:&nbsp;&nbsp;%s" % ",&nbsp;&nbsp;".join(map(str.strip, synonyms[:maxsyn]))
				if len(synonyms) > maxsyn:
					text += " ..."
				html.XP(self, text, {"class":"synonyms"})
		linkouts = database.linkouts(qtype, qid, dictionary)
		if len(linkouts):
			source_urls = {}
			sources = []
			for linkout in linkouts:
				source = linkout[0]
				url = linkout[1]
				if source in source_urls:
					source_urls[source].append(url)
				else:
					source_urls[source] = [url]
					sources.append(source)
			text = ["Linkouts:"]
			for source in sources:
				text.append("&nbsp;&nbsp;")
				if len(source_urls[source]) == 1:
					text.append('''<a class="silent_link" href="%s">%s</a>''' % (source_urls[source][0], source))
				else:
					text.append(source)
					i = 1
					for url in source_urls[source]:
						text.append('''&nbsp;<a class="silent_link" href="%s">#%d</a>''' % (url, i))
						i += 1
			html.XP(self, "".join(text), {"class":"linkouts"})


class About(mamba.task.Request):
	
	def main(self):
		page = XPage("About", "About")
		mamba.http.HTMLResponse(self, page.tohtml()).send()


class Downloads(mamba.task.Request):
	
	def main(self):
		page = XPage("Downloads", "Downloads")
		mamba.http.HTMLResponse(self, page.tohtml()).send()


class Entity(mamba.task.Request):
	
	def main(self):
		rest = mamba.task.RestDecoder(self)
		dictionary = database.Connect("dictionary")
		if 'GROUPS' in mamba.setup.config().sections:
			groups = mamba.setup.config().sections['GROUPS']
		
		order = []
		qfigures = []
		qtimecourses = []
		nnetwork     = 0
		nknowledge   = 0
		nexperiments = 0
		ntextmining  = 0
		npredictions = 0
		ndocuments   = 0
		
		if "order" in rest:
			order = rest["order"].split(",")
		if "figures" in rest:
			qfigures = rest["figures"].split(",")
			if "figures" not in order:
				order.append("figures")
		if "timecourses" in rest:
			qtimecourses = rest["timecourses"].split(",")
			if "timecourses" not in order:
				order.append("timecourses")
		if "network" in rest:
			nnetwork = int(rest["network"])
			if "network" not in order:
				order.append("network")
		if "knowledge" in rest:
			nknowledge = int(rest["knowledge"])
			if "knowledge" not in order:
				order.append("knowledge")
		if "experiments" in rest:
			nexperiments = int(rest["experiments"])
			if "experiments" not in order:
				order.append("experiments")
		if "textmining" in rest:
			ntextmining = int(rest["textmining"])
			if "textmining" not in order:
				order.append("textmining")
		if "predictions" in rest:
			npredictions = int(rest["predictions"])
			if "predictions" not in order:
				order.append("predictions")
		if "documents" in rest:
			ndocuments = int(rest["documents"])
			if "documents" not in order:
				order.append("documents")
		if "homologs" in rest:
			order.append("homologs")
		
		qtype1 = int(rest["type1"])
		qid1 = rest["id1"]
		qtype2 = None
		if "type2" in rest:
			qtype2 = int(rest["type2"])
		qid2 = None
		if "id2" in rest:
			qid2 = rest["id2"]
		
		name1 = database.preferred_name(qtype1, qid1, dictionary)
		name2 = None
		if qtype2 != None and qid2 != None:
			name2 = database.preferred_name(qtype2, qid2, dictionary)
		page = XPage("Entity", name1)
		
		associations = None
		if len(qfigures) or len(qtimecourses) or nknowledge or nexperiments or ntextmining or npredictions:
			associations = AssociationsSection(page.content, qtype1, qid1, qtype2, dictionary)
		
		documents = None
		if ndocuments:
			if name2 == None:
				documents = html.XSection(page.content, html.xcase("Literature on %s" % name1))
			else:
				documents = html.XSection(page.content, html.xcase("Literature associating %s and %s" % (name1, name2)))
		
		if associations:
			EntityHeader(associations.body, qtype1, qid1, dictionary)
		elif documents:
			EntityHeader(documents.body, qtype1, qid1, dictionary)
		
		for section in order:
			if section == "figures":
				for n, qfigure in enumerate(qfigures):
					container = html.XDiv(associations.body, "blackmamba_visualization%d_div" % n)
					visualization.SVG(container, qfigure, qtype1, qid1)
			elif section == "timecourses":
				container = html.XDiv(associations.body,"ajax_timecourses", "blackmamba_timecourses_div")
				html.XScript(container, "blackmamba_timecourses('id=%s&sources=%s', '%s');" % (qid1, ",".join(qtimecourses), "blackmamba_timecourses_div",true))
			elif section == "network":
				network_link = html.XLink(associations.body, "StringNetworkLink?type1=%d&id1=%s&type2=%d&limit=%d" % (qtype1, qid1, qtype2, nnetwork))
				html.XImg(network_link, "StringNetworkImage?type1=%d&id1=%s&type2=%d&limit=%d" % (qtype1, qid1, qtype2, nnetwork))
			elif section == "knowledge":
				if qtype2 == None or qid2 == None:
					XAjaxContainer(associations.body, "Knowledge", "type1=%d&id1=%s&type2=%d" % (qtype1, qid1, qtype2), nknowledge)
				else:
					XAjaxContainer(associations.body, "Knowledge", "type1=%d&id1=%s&type2=%d&id2=%s" % (qtype1, qid1, qtype2, qid2), nknowledge)
			elif section == "experiments":
				if qtype2 == None or qid2 == None:
					XAjaxContainer(associations.body, "Experiments", "type1=%d&id1=%s&type2=%d" % (qtype1, qid1, qtype2), nexperiments)
				else:
					XAjaxContainer(associations.body, "Experiments", "type1=%d&id1=%s&type2=%d&id2=%s" % (qtype1, qid1, qtype2, qid2), nexperiments)
			elif section == "textmining":
				if qtype2 == None or qid2 == None:
					XAjaxContainer(associations.body, "Textmining", "type1=%d&id1=%s&type2=%d&title=Text+mining" % (qtype1, qid1, qtype2), ntextmining)
				else:
					XAjaxContainer(associations.body, "Textmining", "type1=%d&id1=%s&type2=%d&id2=%s&title=Text+mining" % (qtype1, qid1, qtype2, qid2), ntextmining)
			elif section == "predictions":
				if qtype2 == None or qid2 == None:
					XAjaxContainer(associations.body, "Predictions", "type1=%d&id1=%s&type2=%d" % (qtype1, qid1, qtype2), npredictions)
				else:
					XAjaxContainer(associations.body, "Predictions", "type1=%d&id1=%s&type2=%d&id2=%s" % (qtype1, qid1, qtype2, qid2), npredictions)
			elif section == "documents":
				if qtype2 == None or qid2 == None:
					XAjaxContainer(documents.body, "Mentions", "type=%d&id=%s" % (qtype1, qid1), ndocuments)
				else:
					XAjaxContainer(documents.body, "Comentions", "type1=%d&id1=%s&type2=%d&id2=%s" % (qtype1, qid1, qtype2, qid2), ndocuments)
			elif section == "homologs":
				if qtype2 is not None:
					for key in groups:
            					db = groups[key]
						title = "Orthologs and paralogs"
				        	XAjaxContainer(associations.body, "CorrOrthoGroups", "title=%s&type1=%d&id1=%s&type2=%d&key=%d&db=%s" % (title,qtype1, qid1, qtype2,int(key),db), 10)
		
		mamba.http.HTMLResponse(self, page.tohtml()).send()


class OpenSearchDescription(mamba.task.Request):
	
	def main(self):
		design = get_design()
		xml = '''<?xml version="1.0"?><OpenSearchDescription xmlns="http://a9.com/-/spec/opensearch/1.1/"><ShortName>%s</ShortName><Description>%s</Description><Url type="text/html" method="get" template="http://%s/Search?query={searchTerms}"/></OpenSearchDescription>''' % (design["TITLE"], design["SUBTITLE"], self.http.headers["Host"])
		mamba.http.HTTPResponse(self, xml, "application/opensearchdescription+xml").send()
