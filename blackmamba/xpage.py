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
		html.XScript(parent, "Hammer(document.getElementById('%s')).on('swipeleft', function(event) {document.getElementById('%s_next').onclick();}).on('swiperight', function(event) {document.getElementById('%s_prev').onclick();});" % (container, container, container))


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
	
	def create_table(self, parent, rest):
		dictionary = database.Connect("dictionary")
		self.xtable = html.XDataTable(parent)
		self.xtable["width"] = "100%"
		self.add_head()
		limit = int(rest["limit"])
		page = int(rest["page"])
		count = 0
		for r in self.get_rows(rest):
			count += 1
			if count > page*limit:
				break
			if count > limit*(page-1):
				name = html.xcase(database.preferred_name(int(rest["type2"]), r["id2"], dictionary))
				stars = int(math.ceil(r['score']))
				stars = '<span class="stars">%s</span>' % "".join(["&#9733;"]*stars + ["&#9734;"]*(5-stars))
				self.add_row(r, name, stars)
		return count
	
	def get_rows(self, rest):
		evidence = database.Connect(self.action.lower())
		return evidence.query(self.get_sql(rest)+" LIMIT %d;" % (int(rest["limit"])*int(rest["page"])+1)).dictresult()
		
	def main(self):
		self.action = self.http.get_action()
		rest = mamba.task.RestDecoder(self)
		if "title" in rest:
			title = rest["title"]
		else:
			title = self.action

		xroot = html.XNode(None)
		html.XDiv(xroot, "table_title").text = title
		xpages = html.XNode(xroot)
		XPagesDiv(xpages, self.action, rest, self.create_table(xroot, rest))
		
		mamba.http.HTTPResponse(self, xroot.tohtml()).send()


class Knowledge(XAjaxTable):
	
	def add_head(self):
		self.xtable.addhead("Name", "Source", "Evidence", "Confidence")
	
	def add_row(self, row, name, stars):
		if 'url' in row and row['url'] != "":
			name = html.XLink(None, row['url'], name, '_blank', {"class":"silent_link"})
		self.xtable.addrow(name, row['source'], row['evidence'], stars)
	
	def get_sql(self, rest):
		return "SELECT * FROM pairs WHERE type1=%d AND id1='%s' AND type2=%d AND explicit='t' ORDER BY score DESC" % (int(rest["type1"]), pg.escape_string(rest["id1"]), int(rest["type2"]))


class Experiments(XAjaxTable):
	
	def add_head(self):
		self.xtable.addhead("Name", "Source", "Evidence", "Confidence")
	
	def add_row(self, row, name, stars):
		if 'url' in row and row['url'] != "":
			name = html.XLink(None, row['url'], name, '_blank', {"class":"silent_link"})
		self.xtable.addrow(name, row['source'], row['evidence'], stars)
	
	def get_sql(self, rest):
		return "SELECT * FROM pairs WHERE type1=%d AND id1='%s' AND type2=%d AND explicit='t' ORDER BY score DESC" % (int(rest["type1"]), pg.escape_string(rest["id1"]), int(rest["type2"]))


class Predictions(XAjaxTable):
	
	def add_head(self):
		self.xtable.addhead("Name", "Source", "Evidence", "Confidence")
	
	def add_row(self, row, name, stars):
		self.xtable.addrow(name, row['source'], row['evidence'], stars)
		
	def get_sql(self, rest):
		return "SELECT * FROM pairs WHERE type1=%d AND id1='%s' AND type2=%d AND explicit='t' ORDER BY score DESC" % (int(rest["type1"]), pg.escape_string(rest["id1"]), int(rest["type2"]))


class XPage(html.XNakedPage):
	
	def __init__(self, page_class=None, page_name=None):
		design = get_design()
		if page_name:
			html.XNakedPage.__init__(self, "%s - %s" % (design["TITLE"], page_name))
		else:
			html.XNakedPage.__init__(self, design["TITLE"])
		self.head.search = (design["TITLE"], "/OpenSearchDescription")
		self.head.css = map(str.strip, design["CSS"].split("\n"))
		left = html.XDiv(self.header, "header_left")
		html.XLink(html.XH1(left), "/", design["TITLE"])
		html.XLink(html.XP(left), "/", design["SUBTITLE"])
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
		html.XP(self, html.xcase(database.description(qtype, qid, dictionary, userdata)), {"class":"description"})
		maxsyn = 5
		synonyms = database.synonyms(qtype, qid, dictionary, userdata)
		if len(synonyms):
			if len(synonyms) > 1 or synonyms[0].lower() != name.lower():
				text = "Synonyms:&nbsp;&nbsp;%s" % ",&nbsp;&nbsp;".join(map(str.strip, synonyms[:maxsyn]))
				if len(synonyms) > maxsyn:
					text += " ..."
				html.XP(self, text, {"class":"synonyms"})


class Downloads(mamba.task.Request):
	
	def main(self):
		page = XPage("Downloads", "Downloads")
		mamba.http.HTMLResponse(self, page.tohtml()).send()


class Entity(mamba.task.Request):
	
	def main(self):
		rest = mamba.task.RestDecoder(self)
		dictionary = database.Connect("dictionary")
		
		qfigures = []
		nnetwork     = 0
		nknowledge   = 0
		nexperiments = 0
		ntextmining  = 0
		npredictions = 0
		ndocuments   = 0
		
		if "figures" in rest:
			qfigures = rest["figures"].split(",")
		if "network" in rest:
			nnetwork = int(rest["network"])
		if "knowledge" in rest:
			nknowledge = int(rest["knowledge"])
		if "experiments" in rest:
			nexperiments = int(rest["experiments"])
		if "textmining" in rest:
			ntextmining = int(rest["textmining"])
		if "predictions" in rest:
			npredictions = int(rest["predictions"])
		if "documents" in rest:
			ndocuments = int(rest["documents"])
		
		qtype1 = int(rest["type1"])
		qid1 = rest["id1"]
		if "type2" in rest:
			qtype2 = int(rest["type2"])
		
		name = database.preferred_name(qtype1, qid1, dictionary)
		page = XPage("Entity", name)
		
		associations = None
		if len(qfigures) or nknowledge or ntextmining or npredictions:
			associations = AssociationsSection(page.content, qtype1, qid1, qtype2, dictionary)
		
		documents = None
		if ndocuments:
			documents = html.XSection(page.content, html.xcase("Literature on %s" % name))
		
		if associations:
			EntityHeader(associations.body, qtype1, qid1, dictionary)
		elif documents:
			EntityHeader(documents.body, qtype1, qid1, dictionary)
		
		for n, qfigure in enumerate(qfigures):
			visualization.AjaxSVG(associations.body, "visualization%d" % n, qfigure, qtype1, qid1)
		if nnetwork:
			network_link = html.XLink(associations.body, "StringNetworkLink?type1=%d&id1=%s&type2=%d&limit=%d" % (qtype1, qid1, qtype2, nnetwork))
			html.XImg(network_link, "StringNetworkImage?type1=%d&id1=%s&type2=%d&limit=%d" % (qtype1, qid1, qtype2, nnetwork))
		if nknowledge:
			XAjaxContainer(associations.body, "Knowledge", "type1=%d&id1=%s&type2=%d" % (qtype1, qid1, qtype2), nknowledge)
		if nexperiments:
			XAjaxContainer(associations.body, "Experiments", "type1=%d&id1=%s&type2=%d" % (qtype1, qid1, qtype2), nexperiments)
		if ntextmining:
			XAjaxContainer(associations.body, "Textmining", "type1=%d&id1=%s&type2=%d&title=Text+mining" % (qtype1, qid1, qtype2), ntextmining)
		if npredictions:
			XAjaxContainer(associations.body, "Predictions", "type1=%d&id1=%s&type2=%d" % (qtype1, qid1, qtype2), npredictions)
		
		if ndocuments:
			XAjaxContainer(documents.body, "Mentions", "type=%d&id=%s" % (qtype1, qid1), ndocuments)
		
		mamba.http.HTMLResponse(self, page.tohtml()).send()


class OpenSearchDescription(mamba.task.Request):
	
	def main(self):
		design = get_design()
		xml = '''<?xml version="1.0"?><OpenSearchDescription xmlns="http://a9.com/-/spec/opensearch/1.1/"><ShortName>%s</ShortName><Description>%s</Description><Url type="text/html" method="get" template="http://%s/Search?query={searchTerms}"/></OpenSearchDescription>''' % (design["TITLE"], design["SUBTITLE"], self.http.headers["Host"])
		mamba.http.HTTPResponse(self, xml, "application/opensearchdescription+xml").send()
