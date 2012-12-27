import sys
import mamba.http
import mamba.task
import mamba.setup
import tagger.tagger


class Setup(mamba.setup.Configuration):

	def __init__(self, ini_file):
		mamba.setup.Configuration.__init__(self, ini_file)
		sys.setcheckinterval(10000)
		styles = {}
		if "STYLES" in self.sections:
			for priority in self.sections["STYLES"]:
				styles[int(priority)] = self.sections["STYLES"][priority]
		types = {}
		if "TYPES" in self.sections:
			for priority in self.sections["TYPES"]:
				types[int(priority)] = self.sections["TYPES"][priority]
		print '[INIT]  Loading tagger ...'
		self.tagger = tagger.tagger.Tagger()
		self.tagger.SetStyles(styles, types)
		if "java_scripts" in self.globals:
			self.tagger.LoadHeaders(self.globals["java_scripts"])
		self.tagger.LoadNames(self.globals["entities_file"], self.globals["names_file"])
		if "global_file" in self.globals:
			self.tagger.LoadGlobal(self.globals["global_file"])
		if "local_file" in self.globals:
			self.tagger.LoadLocal(self.globals["local_file"])
		if "changelog_file" in self.globals:
			self.tagger.LoadChangelog(self.globals["changelog_file"])


class AddName(mamba.task.Request):
	
	def main(self):
		rest = mamba.task.RestDecoder(self)
		for check in ("name", "document_id", "entity_type", "entity_identifier"):
			if check not in rest:
				raise mamba.task.SyntaxError, 'Required parameter "%s" missing.' % check
		mamba.setup.config().tagger.AddName(mamba.util.string_to_bytes(rest["name"], "utf-8"), int(rest["entity_type"]), mamba.util.string_to_bytes(rest["entity_identifier"], "utf-8"), mamba.util.string_to_bytes(rest["document_id"], "utf-8"))
		mamba.http.HTTPResponse(self, "AddName succeeded.").send()


class AllowName(mamba.task.Request):
	
	def main(self):
		rest = mamba.task.RestDecoder(self)
		for check in ("name", "document_id"):
			if check not in rest:
				raise mamba.task.SyntaxError, 'Required parameter "%s" missing.' % check
		mamba.setup.config().tagger.AllowName(mamba.util.string_to_bytes(rest["name"], "utf-8"), mamba.util.string_to_bytes(rest["document_id"], "utf-8"))
		mamba.http.HTTPResponse(self, 'AllowName succeeded.').send()


class BlockName(mamba.task.Request):
	
	def main(self):
		rest = mamba.task.RestDecoder(self)
		for check in ("name", "document_id"):
			if check not in rest:
				raise mamba.task.SyntaxError, 'Required parameter "%s" missing.' % check
		mamba.setup.config().tagger.BlockName(mamba.util.string_to_bytes(rest["name"], "utf-8"), mamba.util.string_to_bytes(rest["document_id"], "utf-8"))
		mamba.http.HTTPResponse(self, 'BlockName succeeded.').send()


class GetHead(mamba.task.EmptyRequest):
	
	def main(self):
		mamba.http.HTTPResponse(self, mamba.setup.config().globals["java_scripts"]).send()


class GetHeader(GetHead):
	pass


class GetPopup(mamba.task.Request):
	 
	def main(self):
		rest = mamba.task.RestDecoder(self)
		entities = mamba.setup.config().tagger.ResolveName(mamba.util.string_to_bytes(rest["name"], self.http.charset))
		if len(entities):
			url_params = []
			show_first = ["9606", "10090"]
			for pref_organism in show_first:
				for type, id in entities:
					if type == pref_organism:
						url_params.append(type + "." + id + "+")
			for type, id in entities:
				if type not in show_first:
					url_params.append(type + "." + id + "+")
			popup_url = 'http://reflect.ws/popup/fcgi-bin/createPopup.fcgi?' + ''.join(url_params)
			popup_url = popup_url[:-1]
			reply = mamba.http.HTTPRedirect(self, popup_url)
			reply.send()
		else:
			html = "<html><head><title>No Reflect popup available</title></head><body>The name '%s' was not found in our dictionary.</body></html>" % self.names[0]
			mamba.http.HTTPResponse(self, html, content_type="text/html").send()


class ResolveName(mamba.task.Request):
	
	def main(self):
		rest = mamba.task.RestDecoder(self)
		names = []
		if "name" in rest:
			names.append(mamba.util.string_to_bytes(rest["name"], self.http.charset))
		elif "names" in rest:
			names += mamba.util.string_to_bytes(rest["names"], self.http.charset).split("\n")
		else:
			raise mamba.task.SyntaxError, 'Required parameter "name" or "names" is missing.'
		format = "tsv"
		if "format" in rest:
			format = rest["format"]
		if format == "xml":
			xml = []
			xml.append("""<?xml version="1.0" encoding="UTF-8"?>\n""")
			xml.append("""<ResolveNameResponse xmlns="Reflect" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">""")
			xml.append("""<items>""")
			for name in names:
				xml.append("""<item><name xsi:type="xsd:string">%s</name><entities>""" % name)
				for entity in mamba.setup.config().tagger.ResolveName(name):
					xml.append("""<entity><type xsi:type="xsd:int">%d</type><identifier xsi:type="xsd:string">%s</identifier></entity>""" % (entity[0], entity[1]))
				xml.append("""</entities></item>""")
			xml.append("</items>")
			xml.append("</ResolveNameResponse>")
			result = "".join(xml)
			content_type = "text/xml"
		else:
			tsv = []
			for name in names:
				for entity in mamba.setup.config().tagger.ResolveName(name):
					tsv.append("%s\t%d\t%s\n" % (name, entity[0], entity[1]))
			result = "".join(tsv)
			content_type = "text/plain"
		mamba.http.HTTPResponse(self, result, content_type).send()
