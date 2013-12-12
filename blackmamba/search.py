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
			xtable.addhead("Matched name", "Primary name", "Type", "Identifier")
			seen = set()
			count = 0
			for qtype, qid, name in entities:
				if (qtype,qid) not in seen:
					seen.add((qtype,qid))
					if count >= limit*(page-1) and count < page*limit:
						preferred = database.preferred_name(qtype, qid, dictionary)
						type = database.preferred_type_name(qtype, dictionary)
						link = '<a class="silent_link" href="%s%s">%%s</a>' % (qtypes[str(qtype)], qid)
						xtable.addrow(link % html.xcase(name), link % html.xcase(preferred), type, link % qid)
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
		if query != "":
			html.XScript(self.content, "document.blackmamba_search_form.submit();")


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
