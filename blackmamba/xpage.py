import hashlib
import math
import os
import pg
import re
import urllib

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
		if format == "html":
			filter = True
			self.xtable = html.XDataTable(parent)
			self.xtable["width"] = "100%"
			self.add_head()
		elif format == "json":
			self.json = []
		limit = int(rest["limit"])
		page = int(rest["page"])
		count = 0
		for r in self.get_rows(rest, filter):
			count += 1
			if count > page*limit:
				break
			if count > limit*(page-1):
				name = html.xcase(database.preferred_name(int(rest["type2"]), r["id2"], dictionary))
				stars = int(math.ceil(r['score']))
				stars = '<span class="stars">%s</span>' % "".join(["&#9733;"]*stars + ["&#9734;"]*(5-stars))
				self.add_row(r, name, stars, format)
		return count
	
	def get_rows(self, rest, filter):
		evidence = database.Connect(self.action.lower())
		return evidence.query(self.get_sql(rest, filter)+" LIMIT %d;" % (int(rest["limit"])*int(rest["page"])+1)).dictresult()
		
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
			limit = int(rest["limit"])
			page = int(rest["page"])
			count = self.create_table(rest)
			more = "false"
			if count > page*limit:
				more = "true"
			mamba.http.HTTPResponse(self, "[{%s},%s]\n" % (",".join(self.json), more), "application/json").send()


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
	
	def get_sql(self, rest, filter):
		if filter:
			return "SELECT * FROM pairs WHERE type1=%d AND id1='%s' AND type2=%d AND explicit='t' ORDER BY score DESC" % (int(rest["type1"]), pg.escape_string(rest["id1"]), int(rest["type2"]))
		else:
			return "SELECT * FROM pairs WHERE type1=%d AND id1='%s' AND type2=%d ORDER BY score DESC" % (int(rest["type1"]), pg.escape_string(rest["id1"]), int(rest["type2"]))


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
	
	def get_sql(self, rest, filter):
		if filter:
			return "SELECT * FROM pairs WHERE type1=%d AND id1='%s' AND type2=%d AND explicit='t' ORDER BY score DESC" % (int(rest["type1"]), pg.escape_string(rest["id1"]), int(rest["type2"]))
		else:
			return "SELECT * FROM pairs WHERE type1=%d AND id1='%s' AND type2=%d ORDER BY score DESC" % (int(rest["type1"]), pg.escape_string(rest["id1"]), int(rest["type2"]))


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
		
	def get_sql(self, rest, filter):
		if filter:
			return "SELECT * FROM pairs WHERE type1=%d AND id1='%s' AND type2=%d AND explicit='t' ORDER BY score DESC" % (int(rest["type1"]), pg.escape_string(rest["id1"]), int(rest["type2"]))
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
		html.XLink(html.XH1(left), "/", title)
		html.XLink(html.XP(left), "/", subtitle)
		if "LOGO" in design:
			if "LINK" in design:
				html.XImg(html.XLink(html.XDiv(self.header, "header_right"), design["LINK"]), design["LOGO"])
			else:
				html.XImg(html.XDiv(self.header, "header_right"), design["LOGO"])
		menu = html.XDiv(self.header, "menu")
		if "MENU" in design:
			for item in design["MENU"].split("\n"):
				if item.upper() == page_class.upper():
					html.XText(html.XSpan(menu), item)
				else:
					html.XLink(menu, "/"+item, item, None, {"class":"silent_link"})
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
		maptype[-1]    = "Chemical compounds associated with %s"
		maptype[0]     = "Genes for %s"
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
		
		order = []
		qfigures = []
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
		if len(qfigures) or nknowledge or nexperiments or ntextmining or npredictions:
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
			elif section == "network":
				network_link = html.XLink(associations.body, "StringNetworkLink?type1=%d&id1=%s&type2=%d&limit=%d" % (qtype1, qid1, qtype2, nnetwork))
				html.XImg(network_link, "StringNetworkImage?type1=%d&id1=%s&type2=%d&limit=%d" % (qtype1, qid1, qtype2, nnetwork))
			elif section == "knowledge":
				XAjaxContainer(associations.body, "Knowledge", "type1=%d&id1=%s&type2=%d" % (qtype1, qid1, qtype2), nknowledge)
			elif section == "experiments":
				XAjaxContainer(associations.body, "Experiments", "type1=%d&id1=%s&type2=%d" % (qtype1, qid1, qtype2), nexperiments)
			elif section == "textmining":
				XAjaxContainer(associations.body, "Textmining", "type1=%d&id1=%s&type2=%d&title=Text+mining" % (qtype1, qid1, qtype2), ntextmining)
			elif section == "predictions":
				XAjaxContainer(associations.body, "Predictions", "type1=%d&id1=%s&type2=%d" % (qtype1, qid1, qtype2), npredictions)
			elif section == "documents":
				if qtype2 == None or qid2 == None:
					XAjaxContainer(documents.body, "Mentions", "type=%d&id=%s" % (qtype1, qid1), ndocuments)
				else:
					XAjaxContainer(documents.body, "Comentions", "type1=%d&id1=%s&type2=%d&id2=%s" % (qtype1, qid1, qtype2, qid2), ndocuments)
		
		mamba.http.HTMLResponse(self, page.tohtml()).send()


class OpenSearchDescription(mamba.task.Request):
	
	def main(self):
		design = get_design()
		xml = '''<?xml version="1.0"?><OpenSearchDescription xmlns="http://a9.com/-/spec/opensearch/1.1/"><ShortName>%s</ShortName><Description>%s</Description><Url type="text/html" method="get" template="http://%s/Search?query={searchTerms}"/></OpenSearchDescription>''' % (design["TITLE"], design["SUBTITLE"], self.http.headers["Host"])
		mamba.http.HTTPResponse(self, xml, "application/opensearchdescription+xml").send()
