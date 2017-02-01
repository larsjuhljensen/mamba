import pg
import database
import hashlib
import re
import subprocess

import html
import xpage

import mamba.setup
import mamba.task


class Table(html.XNode):
	
	def __init__(self, parent, dictionary, query, section, limit, page, container):
		html.XNode.__init__(self, parent)
		if len(query) < 2:
			html.XP(self, "Query '%s' too short." % query)
			return
		qtypes = mamba.setup.config().sections[section.upper()]
		entities = database.find_entities(map(int, qtypes.keys()), query, dictionary)
		if len(entities):
			html.XDiv(self, "table_title").text = "Search results"
			xpages = html.XDiv(self, "table_pages")
			xtable = html.XDataTable(self)
			xtable["width"] = "100%"
			xtable.addhead("Matched name", "Primary name", "Type", "Identifier")
			seen = set()
			count = 0
			for qtype, qid, name in entities:
				if (qtype, qid) not in seen:
					seen.add((qtype, qid))
					if count >= limit*(page-1) and count < page*limit:
						preferred = database.preferred_name(qtype, qid, dictionary)
						type = database.preferred_type_name(qtype, dictionary)
						link = '<a class="silent_link" href="%s%s">%%s</a>' % (qtypes[str(qtype)], qid)
						xtable.addrow(link % html.xcase(name), link % html.xcase(preferred), link % type, link % qid)
					count += 1
					if count > page*limit:
						break
			if count > limit:
				if page > 1:
					html.XText(html.XSpan(xpages, {"class":"silent_link","onclick":"blackmamba_search('EntityQuery', '%s', %d, %d, '%s')" % (section, limit, page-1, container)}), "&lt;&nbsp;Prev")
				if count > page*limit:
					if page > 1:
						html.XText(xpages, "&nbsp;|&nbsp;")
					html.XText(html.XSpan(xpages, {"class":"silent_link","onclick":"blackmamba_search('EntityQuery', '%s', %d, %d, '%s')" % (section, limit, page+1, container)}), "Next&nbsp;&gt;")
		else:
			html.XP(self, "Nothing found for '%s'" % query)


class SequenceTable(html.XNode):
	
	def __init__(self, parent, dictionary, results, qtypes, num_results, section, limit, page, container):
		html.XNode.__init__(self, parent)
		entities = []
		if num_results:
			sorted_results = {}
			seen = set()
			for qtype in results.keys():
				for r in results[qtype]:
					qid,evalue = r.split("\t")
					if (qtype,qid) not in seen:
						if not sorted_results.has_key(evalue):
							sorted_results[evalue] = []
						sorted_results[evalue].append((qtype,qid))
			
			sorted_evalues = sorted(sorted_results.keys(),key = float)
			
			html.XDiv(self, "table_title").text = "Search results"
			xpages = html.XDiv(self, "table_pages")
			xtable = html.XDataTable(self)
			xtable["width"] = "100%"
			xtable.addhead("Matched name", "Primary name", "Type", "Identifier", "e-value")
			count = 0
			for evalue in sorted_evalues:
				for qtype, qid in sorted_results[evalue]:
					if count >= limit*(page-1) and count < page*limit:
						preferred = database.preferred_name(qtype, qid, dictionary)
						type = database.preferred_type_name(qtype, dictionary)
						link = '<a class="silent_link" href="%s%s">%%s</a>' % (qtypes[str(qtype)], qid)
						xtable.addrow(link % html.xcase(qid), link % html.xcase(preferred), link % type, link % qid, link % evalue)
					count += 1
					if count > page*limit:
						break
			if count > limit:
				if page > 1:
					html.XText(html.XSpan(xpages, {"class":"silent_link","onclick":"blackmamba_search('SequenceQuery', '%s', %d, %d, '%s')" % (section, limit, page-1, container)}), "&lt;&nbsp;Prev")
				if count > page*limit:
					if page > 1:
						html.XText(xpages, "&nbsp;|&nbsp;")
					html.XText(html.XSpan(xpages, {"class":"silent_link","onclick":"blackmamba_search('SequenceQuery', '%s', %d, %d, '%s')" % (section, limit, page+1, container)}), "Next&nbsp;&gt;")
		else:
			html.XP(self, "Nothing found for the specified sequence")


class EntityQuery(mamba.task.Request):
	
	def main(self):
		rest = mamba.task.RestDecoder(self)
		query = ""
		if "query" in rest:
			query = rest["query"]
		section = ""
		if "section" in rest:
			section = rest["section"]
		types = []
		if "types" in rest:
			types = map(int, rest["types"].split())
		elif section != "":
			types = map(int, mamba.setup.config().sections[section.upper()].keys())
		limit = 20
		if "limit" in rest:
			limit = int(rest["limit"])
		page = 1
		if "page" in rest:
			page = int(rest["page"])
		format = "html"
		if "format" in rest:
			format = rest["format"]
		dictionary = database.Connect("dictionary")
		if format == "html":
			container = rest["container"]
			mamba.http.HTMLResponse(self, Table(None, dictionary, query, section, limit, page, container).tohtml()).send()
		elif format == "json":
			entities = database.find_entities(types, query, dictionary)
			seen = set()
			count = 0
			more = "false"
			json = []
			for qtype, qid, name in entities:
				if (qtype, qid) not in seen:
					seen.add((qtype, qid))
					count += 1
					if count <= limit:
						preferred = database.preferred_name(qtype, qid, dictionary)
						json.append('{"type":%d,"id":"%s","matched":"%s","primary":"%s"}' % (qtype, qid, name, preferred))
					else:
						more = "true"
						break
			mamba.http.HTTPResponse(self, "[[%s],%s]\n" % (",".join(json), more), "application/json").send()


class Fetch(mamba.task.Request):
	
	def main(self):	
		rest = mamba.task.RestDecoder(self)
		query = ""
		if "query" in rest:
			query = rest["query"]
		section = "SEARCH"
		if "section" in rest:
			section = rest["section"]
		qtypes = mamba.setup.config().sections[section.upper()]
		dictionary = database.Connect("dictionary")
		entities = database.find_entities(map(int, qtypes.keys()), query, dictionary)
		if len(entities):
			url = qtypes[str(entities[0][0])]+entities[0][1]
			mamba.http.HTTPRedirect(self, url).send()
		else:
			mamba.http.HTTPErrorResponse(self, 404, "Not Found").send()


class SearchPage(xpage.XPage):
	
	def __init__(self, page_class, page_name, action, limit, query):
		xpage.XPage.__init__(self, page_class, page_name)
		md5 = hashlib.md5()
		md5.update(action)
		container = md5.hexdigest()
		design = xpage.get_design()
		key = "EXAMPLES:"+page_class.upper()
		if key in design:
			examples = html.XSpan(self.content, {"class":"examples"})
			html.XText(examples, "(examples:")
			count = 0
			for example in design[key].split("\n"):
				count += 1
				html.XText(examples, " ")
				html.XText(html.XSpan(examples, {"class":"silent_link", "onclick":"document.blackmamba_search_form.query.value='"+example+"';"}), "#"+str(count))
			html.XText(examples, ")")
		form = html.XTag(self.content, "form", {"name":"blackmamba_search_form"})
		form["action"] = "javascript:blackmamba_search('/%s/', '%s', %d, 1, '%s');" % (action, page_class, limit, container)
		html.XTag(form, "input", {"type":"text", "name":"query", "value":query, "class":"query"})
		html.XDiv(form, "spacer")
		html.XTag(form, "input", {"type":"submit", "value":"search", "class":"search"})
		html.XDiv(self.content, "ajax_table", container)
		links_key = "QUICKLINKS"
		links_content_key = "CONTENT:"+links_key
		content = "Browse by:"
		if links_content_key in design:
			content = design[links_content_key]
		if links_key in mamba.setup.config().sections:
			links = mamba.setup.config().sections[links_key]
			if len(links):
				quicklinks = html.XSpan(self.content, {"class":"quicklinks"})
				html.XText(quicklinks, content)
				html.XDiv(quicklinks, "spacer")
				for key in sorted(links.keys()):
					html.XLink(quicklinks, links[key],key.split('_')[1].capitalize())
					html.XDiv(quicklinks, "spacer")
		if query != "":
			html.XScript(self.content, "document.blackmamba_search_form.submit();")


class SequenceSearchPage(xpage.XPage):
	
	def __init__(self, page_class, page_name, action, limit, query):
		xpage.XPage.__init__(self, page_class, page_name)
		md5 = hashlib.md5()
		md5.update(action)
		container = md5.hexdigest()
		design = xpage.get_design()
		key = "EXAMPLES:"+page_class.upper()
		if key in design:
			examples = html.XSpan(self.content, {"class":"examples"})
			html.XText(examples, "(examples:")
			count = 0
			for example in design[key].split("\n"):
				count += 1
				html.XText(examples, " ")
				html.XText(html.XSpan(examples, {"class":"silent_link", "onclick":"document.blackmamba_search_form.query.value='"+example+"';"}), "#"+str(count))
			html.XText(examples, ")")
		form = html.XTag(self.content, "form", {"name":"blackmamba_search_form"})
		form["action"] = "javascript:blackmamba_search('/%s/', '%s', %d, 1, '%s');" % (action, page_class, limit, container)
		html.XTextArea(form, {"rows":"20", "cols":"60","name":"query", "value":query, "class":"query"})
		html.XDiv(form, "break")
		html.XTag(form, "input", {"type":"submit", "value":"search", "class":"search"})
		html.XDiv(self.content, "ajax_table", container)
		if query != "":
			html.XScript(self.content, "document.blackmamba_search_form.submit();")


class SequenceQuery(mamba.task.Request):
	
	def blast(self):
		ncpattern = re.compile('[ACTG]+')
		
		rest = mamba.task.RestDecoder(self)
		query = ""
		if "query" in rest:
			query = rest["query"]
		section = ""
		if "section" in rest:
			section = rest["section"]
		limit = 20
		if "limit" in rest:
			limit = int(rest["limit"])
		page = 1
		if "page" in rest:
			page = int(rest["page"])
		container = rest["container"]
		
		if not query.startswith(">"):
			query = ">sequence\n"+query
		
		stype = ""
		if ncpattern.match(query.upper().split("\n")[1]):
			stype = "blastx"
		else:
			stype = "blastp"
		qtypes = mamba.setup.config().sections['SEARCH']
		blast = mamba.setup.config().globals[stype]
		blastdb = mamba.setup.config().globals['blastdb']
		
		blast_results = {}
		num_results = 0
		for qtype in qtypes:
			blast_request = "echo -e \""+query+"\"| "+blast+" -db "+blastdb+qtype+" -outfmt 6 -evalue 1 | cut -f2,11"
			blast_call = subprocess.Popen([blast_request], stdout=subprocess.PIPE, shell=True)
			blast_results[int(qtype)] = blast_call.stdout.readlines()
			num_results += len(blast_results[int(qtype)])
		
		self.build_response(blast_results, qtypes, num_results, section, limit, page, container)
	
	def build_response(self,blast_results, qtypes, num_results, section, limit, page, container):
		mamba.http.HTMLResponse(self, SequenceTable(None, database.Connect("dictionary"), blast_results, qtypes, num_results, section, limit, page, container).tohtml()).send()
	
	def main(self):
		rest = mamba.task.RestDecoder(self)
		query = ""
		if "query" in rest:
			query = rest["query"]
			if len(query) < 10:
				html.XP(self, "Query '%s' too short." % query)
				return
			self.queue("blast")


class Search(mamba.task.Request):
	
	def main(self):
		rest = mamba.task.RestDecoder(self)
		action = "EntityQuery"
		if "action" in rest:
			action = rest["action"]
		limit = 20
		if "limit" in rest:
			imit = int(rest["limit"])
		query = ""
		if "query" in rest:
			query = rest["query"]
		mamba.http.HTMLResponse(self, SearchPage("SEARCH", "Search", action, limit, query).tohtml()).send()


class SequenceSearch(mamba.task.Request):
	
	def main(self):
		rest = mamba.task.RestDecoder(self)
		action = "SequenceQuery"
		if "action" in rest:
			action = rest["action"]
		limit = 20
		if "limit" in rest:
			imit = int(rest["limit"])
		query = ""
		if "query" in rest:
			query = rest["query"]
		mamba.http.HTMLResponse(self, SequenceSearchPage("SEQUENCESEARCH", "SequenceSearch", action, limit, query).tohtml()).send()
