import httplib
import pg
import urllib
import xml.etree.ElementTree as etree
import database
import html
import xpage
import mamba.task
import mamba.util

class PopupHeader(mamba.task.Request):

	def main(self):
		rest = mamba.task.RestDecoder(self)
		qtype = int(rest["type"])
		qid = rest["id"]

		xroot = html.XNode(None)
		html.XLink(html.XDiv(xroot, "popup_close"), "javascript:close_popup()", "[close]")
		xpage.EntityHeader(xroot, qtype, qid)

		mamba.http.HTTPResponse(self, xroot.tohtml()).send()

class Documents(mamba.task.Request):
	
	def add_pages(self, parent, action, rest, documents):
		xpage.XPagesDiv(parent, action, rest, len(documents))
		
	def decorate_matches(self, title, abstract, matches):
		document = "\t".join([title, abstract])
		matches.sort()
		doc = []
		i = 0
		for start, stop, qtype, qid, css in matches:
			length = start - i
			if length > 0:
				doc.append(document[i:start])
			text = document[start:stop+1]
			doc.append('<span class="%s">%s</span>' % (css, text))
			i = stop + 1
		document = "".join(doc) + document[i:]
		parts = document.split("\t",1)
		title = parts[0]
		if len(parts) > 1:
			abstract = parts[1]
		return title, abstract
	
	def get_documents(self, rest, textmining):
		return rest["documents"].split(",")
	
	def get_highlight(self, rest):
		return []
	
	def rank_documents(self, documents):
		try:
			settings = mamba.setup.config().sections["RANKER"]
			host = settings["host"]
			port = int(settings["port"])
			params = urllib.urlencode({"documents":",".join(documents)})
			headers = {"Content-type":"application/x-www-form-urlencoded", "Accept":"text/plain"}
			conn = httplib.HTTPConnection(host, port)
			conn.request("POST", "/RankDocuments", params, headers)
			data = conn.getresponse().read()
			conn.close()
			return data.split(",")
		except:
			return sorted(documents, key=int, reverse=True)
	
	def main(self):
		rest = mamba.task.RestDecoder(self)
		textmining = database.Connect("textmining")

		documents = self.get_documents(rest, textmining)
		documents = self.rank_documents(documents)
		
		xroot = html.XNode(None)
		self.add_pages(xroot, self.action, rest, documents)
		
		limit = int(rest["limit"])
		page = int(rest["page"])
		
		count1 = 0
		count2 = 0
		for document in documents:
			data = textmining.query("SELECT * FROM documents WHERE document=%s;" % document).dictresult()
			if len(data):
				count1 += 1
				if count1 > limit*page:
					break
				if count1 <= limit*(page-1):
					continue
				data = data[0]
				text = mamba.util.string_to_bytes(data["text"]).split("\t", 1)
				title = text[0]
				abstract = ""
				if len(text) == 2:
					abstract = text[1].strip()
				journal = mamba.util.string_to_bytes(data["publication"]).split(".")[0]
				authors = mamba.util.string_to_bytes(data["authors"]).split(",")
				year    = mamba.util.string_to_bytes(data["year"])
				matches = dict()
				for qtype, qid, css in self.get_highlight(rest):
					sql = "SELECT start, stop FROM matches WHERE document=%s AND type=%d AND id='%s';" % (document, qtype, qid)
					for start, stop in textmining.query(sql).getresult():
						if start not in matches:
							matches[start] = (start, stop, qtype, qid, css)
				title, abstract = self.decorate_matches(title, abstract, matches.values())
				if count2 % 2 == 0:
					document_wrapper = html.XDiv(xroot, "document_wrapper document_even", document)
				else:
					document_wrapper = html.XDiv(xroot, "document_wrapper document_odd", document)
				if count2 == 0:
					document_wrapper["style"] = "border-top: solid 1px #B0B0B0;"
				count2 += 1
				title_wrapper = html.XDiv(document_wrapper, "document_title")
				title_wrapper["onclick"] = "javascript:toggle_document_content('%s', 'expand')" % document
				title_wrapper.text = title
				author_wrapper = html.XDiv(document_wrapper, "document_authors")
				tmp = []
				for idx, author in enumerate(authors):
					author = mamba.util.string_to_bytes(author)
					if idx < 3:
						tmp.append('<a href="http://www.ncbi.nlm.nih.gov/pubmed?term=%s[author]" target="authors_pubmed">%s</a>' % (author, author))
					else:
						tmp.append(" (and %d more)" % (len(authors) - 3))
						break
 				html.XText(author_wrapper, '%s ; &nbsp; <span style="text-decoration: underline">%s</span> (%s); &nbsp; PMID: <a href="http://www.ncbi.nlm.nih.gov/pubmed?term=%s[pmid]" target="pubmed">%s</a>' % (",".join(tmp), journal, year, document, document))
				document_abstract = html.XDiv(document_wrapper, "document_abstract")
				if len(abstract) == 0:
 					abstract_text = html.XDiv(document_abstract)
					abstract_text["style"] = "display:block; cursor: auto;"
					abstract_text.text = ""
				else:
					abstract_teaser = html.XDiv(document_abstract)
					abstract_teaser["onclick"] = "javascript:toggle_document_abstract('%s', 'expand')" % document
					abstract_teaser.text = '<span style="color: gray;">[View abstract]</span>'
					abstract_full = html.XDiv(document_abstract)
					abstract_full["onclick"] = "javascript:toggle_document_abstract('%s', 'collapse')" % document
					abstract_full["class"] = "hidden"
					abstract_full.text = mamba.util.string_to_bytes(abstract)

		mamba.http.HTTPResponse(self, xroot.tohtml()).send()

class Mentions(Documents):

	def get_documents(self, rest, textmining = None):
		qtype = int(rest["type"])
		qid = rest["id"].encode("utf8")
		return textmining.query("SELECT documents FROM mentions WHERE type=%d AND id='%s';" % (qtype, qid)).getresult()[0][0].split()

	def get_highlight(self, rest):
		qtype = int(rest["type"])
		qid = rest["id"].encode("utf8")
		return [(qtype, qid, "document_match_type1")]

class Comentions(Documents):

	def get_documents(self, rest, textmining):
		qtype1 = int(rest["type1"])
		qtype2 = int(rest["type2"])
		qid1 = rest["id1"].encode("utf8")
		qid2 = rest["id2"].encode("utf8")

		documents1 = textmining.query("SELECT documents FROM mentions WHERE type=%d AND id='%s';" % (qtype1, qid1)).getresult()[0][0].split()
		documents2 = textmining.query("SELECT documents FROM mentions WHERE type=%d AND id='%s';" % (qtype2, qid2)).getresult()[0][0].split()
		if len(documents1) < len(documents2):
			small = documents1
			large = documents2
		else:
			small = documents2
			large = documents1
		lookup = set()
		for document in small:
			lookup.add(document)
		selected = []
		for document in large:
			if document in lookup:
				selected.append(document)
		return selected

	def get_highlight(self, rest):
		qtype1 = int(rest["type1"])
		qtype2 = int(rest["type2"])
		qid1 = rest["id1"].encode("utf8")
		qid2 = rest["id2"].encode("utf8")
		return [(qtype1, qid1, "document_match_type1"), (qtype2, qid2, "document_match_type2")]


class PubmedQuery(Documents):
	
	def add_pages(self, parent, action, rest, documents):
		xpage.XPagesDiv(parent, "/Documents", {"container":rest["container"], "documents":",".join(documents), "limit":rest["limit"], "page":rest["page"]}, len(documents))
	
	def get_documents(self, rest, textmining):
		documents = []
		if "query" in rest:
			url = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + urllib.urlencode({"db":"pubmed", "term":rest["query"], "retmax":100000, "rettype":"uilist"})
			data, status, headers, page_url, charset = mamba.http.Internet().download(url)
			for document in etree.fromstring(data).getiterator("Id"):
				documents.append(document.text)
		return documents
