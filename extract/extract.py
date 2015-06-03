import os
import re
import sys
import hashlib

import mamba.http
import mamba.setup
import mamba.task
import mamba.util
import blackmamba.database
import blackmamba.html
import blackmamba.xpage
import reflect.tagging


_taggable_types = ["text/html", "text/plain", "text/xml", "text/tab-separated-values", 'application/msword', 'application/pdf', 'application/vnd.ms-excel']


class Extract(reflect.tagging.TaggingRequest):
	
	def __init__(self, http):
		reflect.tagging.TaggingRequest.__init__(self, http, "GetHTML")
	
	def tagging(self):
		dictionary = blackmamba.database.Connect("dictionary")
		document = mamba.util.string_to_bytes(self.document, self.http.charset)
		matches = mamba.setup.config().tagger.get_matches(document=document, document_id=self.document_id, entity_types=self.entity_types, auto_detect=self.auto_detect, ignore_blacklist=self.ignore_blacklist)
		rows = set()
		for match in reversed(matches):
			document = '''%s<span style="background-color: #ff6633;">%s</span>%s''' % (document[0:match[0]], document[match[0]:match[1]+1], document[match[1]+1:])
			for entity in match[2]:
				rows.add((blackmamba.database.preferred_type_name(entity[0], dictionary), blackmamba.html.xcase(blackmamba.database.preferred_name(entity[0], entity[1], dictionary)), entity[1]))
		page = blackmamba.xpage.XPage("Extract")
		selection = blackmamba.html.XDiv(page.content, "ajax_table")
		blackmamba.html.XH2(selection, "table_title").text = "Selected text"
		blackmamba.html.XP(selection).text = document
		tsv = []
		table = blackmamba.html.XDiv(page.content, "ajax_table")
		blackmamba.html.XH2(table, "table_title").text = "Identified terms"
		xtable = blackmamba.html.XDataTable(table)
		xtable["width"] = "100%"
		xtable.addhead("Type", "Name", "Identifier")
		for row in sorted(rows):
			tsv.append("%s\t%s\t%s\t%s\t%s\n" % (row[0], row[1], row[2], self.document_url or "", self.document))
			xtable.addrow(row[0], row[1], row[2])
		form = blackmamba.html.XForm(blackmamba.html.XP(table))
		blackmamba.html.XTextArea(form, attr = {"class" : "hidden", "id" : "clipboard"}).text = "".join(tsv)
		blackmamba.html.XLink(form, "", "Copy to clipboard", attr = {"class" : "button_link", "onClick" : "var clipboard = document.getElementById('clipboard'); clipboard.style.display = 'block'; clipboard.select(); document.execCommand('copy'); clipboard.style.display = 'none';"})
		blackmamba.html.XLink(form, "", "Save to file", attr = {"class" : "button_link", "download" : "entities.tsv", "onClick" : "var data = encodeURIComponent(document.getElementById('clipboard').innerHTML); this.setAttribute('href', 'data:text/plain;charset=ascii,'+data)"})
		mamba.http.HTMLResponse(self, page.tohtml()).send()
