import pg
import database
import hashlib
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
			xtable.addhead("Matched name", "Primary name", "Identifier")
			seen = set()
			count = 0
			for qtype, qid, name in entities:
				if (qtype,qid) not in seen:
					seen.add((qtype,qid))
					if count >= limit*(page-1) and count < page*limit:
						preferred = database.preferred_name(qtype, qid, dictionary)
						link = '<a class="silent_link" href="%s%s">%%s</a>' % (qtypes[str(qtype)], qid)
						xtable.addrow(link % html.xcase(name), link % html.xcase(preferred), link % qid)
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


class EntityQuery(mamba.task.Request):
	
	def main(self):
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
		mamba.http.HTMLResponse(self, Table(None, database.Connect("dictionary"), query, section, limit, page, container).tohtml()).send()


class Search(mamba.task.Request):
	
	def main(self):
		rest = mamba.task.RestDecoder(self)
		action = "EntityQuery"
		if "action" in rest:
			action = rest["action"]
		section = "SEARCH"
		if "section" in rest:
			section = rest["section"].upper()
		limit = 20
		if "limit" in rest:
			limit = int(rest["limit"])
		query = ""
		if "query" in rest:
			query = rest["query"]
		md5 = hashlib.md5()
		md5.update(action)
		container = md5.hexdigest()
		
		design = xpage.get_design()
		page = xpage.XPage(section, "Search")
		key = "EXAMPLES:"+section.upper()
		if key in design:
			examples = html.XSpan(page.content, {"class":"examples"})
			html.XText(examples, "(examples:")
			count = 0
			for example in design[key].split("\n"):
				count += 1
				html.XText(examples, " ")
				html.XText(html.XSpan(examples, {"class":"silent_link", "onclick":"document.blackmamba_search_form.query.value='"+example+"';"}), "#"+str(count))
			html.XText(examples, ")")
		form = html.XTag(page.content, "form", {"name":"blackmamba_search_form"})
		form["action"] = "javascript:blackmamba_search('/%s/', '%s', %d, 1, '%s');" % (action, section, limit, container)
		for name in rest:
			if name not in ["action", "query", "submit"]:
				html.XTag(form, "input", {"type":"hidden", "name":name, "value":rest[name]})
		html.XTag(form, "input", {"type":"text", "name":"query", "value":query, "class":"query"})
		html.XDiv(form, "spacer")
		html.XTag(form, "input", {"type":"submit", "value":"search", "class":"search"})
		html.XDiv(page.content, "ajax_table", container)
		if query != "":
			html.XScript(page.content, "document.blackmamba_search_form.submit();")
		
		mamba.http.HTMLResponse(self, page.tohtml()).send()
