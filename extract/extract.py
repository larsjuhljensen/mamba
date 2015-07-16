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
	
	def __init__(self, http, action = "Extract"):
		reflect.tagging.TaggingRequest.__init__(self, http, action)
	
	def tagging(self):
		dictionary = blackmamba.database.Connect("dictionary")
		document = mamba.util.string_to_bytes(self.document, self.http.charset)
		matches = mamba.setup.config().tagger.get_matches(document=document, document_id=self.document_id, entity_types=self.entity_types, auto_detect=self.auto_detect, ignore_blacklist=self.ignore_blacklist)
		rows = set()
		for match in reversed(matches):
			classes = ["extract_match"]
			for entity in match[2]:
				classes.append(entity[1])
				rows.add((blackmamba.database.preferred_type_name(entity[0], dictionary), blackmamba.html.xcase(blackmamba.database.preferred_name(entity[0], entity[1], dictionary)), entity[0], entity[1]))
			document = '''%s<span class="%s"">%s</span>%s''' % (document[0:match[0]], " ".join(classes), document[match[0]:match[1]+1], document[match[1]+1:])
		page = blackmamba.xpage.XPage(self.action)
		selection = blackmamba.html.XDiv(page.content, "ajax_table")
		blackmamba.html.XH2(selection, "table_title").text = "Selected text"
		blackmamba.html.XP(selection).text = document
		tsv = []
		table = blackmamba.html.XDiv(page.content, "ajax_table")
		blackmamba.html.XH2(table, "table_title").text = "Identified terms"
		if len(rows):
			xtable = blackmamba.html.XDataTable(table)
			xtable["width"] = "100%"
			xtable.addhead("Type", "Name", "Identifier")
			for row in sorted(rows):
				tsv.append("%s\t%s\t%s\t%s\t%s\n" % (row[0], row[1], row[3], self.document_url or "", self.document))
				url = blackmamba.database.url(row[2], row[3])
				if url:
					xtable.addrow(row[0], row[1], blackmamba.html.XLink(None, url, row[3], '_blank'))
				else:
					xtable.addrow(row[0], row[1], row[3])
			form = blackmamba.html.XForm(blackmamba.html.XP(table))
			blackmamba.html.XTextArea(form, attr = {"class" : "hidden", "id" : "clipboard"}).text = "".join(tsv)
			blackmamba.html.XLink(form, "", "Copy to clipboard", attr = {"class" : "button_link", "id" : "extract_copy_to_clipboard", "onClick" : "extract_copy_to_clipboard('clipboard'); return false;"})
			blackmamba.html.XLink(form, "", "Save to file", attr = {"class" : "button_link", "download" : "entities.tsv", "id" : "extract_save_to_file", "onClick" : "extract_save_to_file(this);"})
		else:
			blackmamba.html.XP(table).text = "No terms were identified in the selected text."
		mamba.http.HTMLResponse(self, page.tohtml()).send()


class ExtractPopup(Extract):

	def __init__(self, http, action = "ExtractPopup"):
		Extract.__init__(self, http, action)
