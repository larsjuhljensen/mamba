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
		for priority in self.sections['styles']:
			styles[int(priority)] = self.sections['styles'][priority]
		types = {}
		for priority in self.sections['types']:
			types[priority] = lambda x: evail(self.sections['types'][priority])
		print '[INIT]  Loading tagger ...'
		self.tagger = tagger.tagger.Tagger()
		self.tagger.SetStyles(styles, types)
		self.tagger.LoadHeaders(self.globals['java_scripts'])
		self.tagger.LoadNames(self.globals['entities_file'], self.globals['names_file'])
		self.tagger.LoadGlobal(self.globals['global_file'])
		self.tagger.LoadLocal(self.globals['local_file'])
		if 'changelog_file' in self.globals:
			self.tagger.LoadChangelog(self.globals['changelog_file'])


class AddName(mamba.task.Request):
	
	def main(self):
		rest = mamba.task.RestDecoder(self)
		for check in ('name', 'document_id', 'entity_type', 'entity_identifier'):
			if check not in rest:
				raise mamba.task.SyntaxError, 'Required parameter "%s" missing.' % check
		mamba.setup.config().tagger.AddName(rest['name'], int(rest['entity_type']), rest['entity_identifier'], rest['document_id'])
		mamba.http.HTTPResponse(self, "AddName succeeded.").send()


class AllowName(mamba.task.Request):
	
	def main(self):
		rest = mamba.task.RestDecoder(self)
		for check in ('name', 'document_id'):
			if check not in rest:
				raise mamba.task.SyntaxError, 'Required parameter "%s" missing.' % check
		mamba.setup.config().tagger.AllowName(rest['name'], rest['document_id'])
		mamba.http.HTTPResponse(self, 'AllowName succeeded.').send()


class BlockName(mamba.task.Request):
	
	def main(self):
		rest = mamba.task.RestDecoder(self)
		for check in ('name', 'document_id'):
			if check not in rest:
				raise mamba.task.SyntaxError, 'Required parameter "%s" missing.' % check
		mamba.setup.config().tagger.BlockName(rest['name'], rest['document_id'])
		mamba.http.HTTPResponse(self, 'BlockName succeeded.').send()


class GetHead(mamba.task.EmptyRequest):
	
	def main(self):
		mamba.http.HTTPResponse(self, mamba.setup.config().globals["java_scripts"]).send()


class GetHeader(GetHead):
	pass


class ResolveName(mamba.task.Request):
	
	def main(self):
		rest = mamba.task.RestDecoder(self)
		names = []
		if 'name' in rest:
			names += rest['name']
		elif 'names' in rest:
			names += rest['names'].split('\n')
		else:
			raise mamba.task.SyntaxError, 'Required parameter "name" or "names" is missing.'
		if self.format == "xml":
			doc = []
			doc.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
			doc.append("<ResolveNameResponse xmlns=\"Reflect\" xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">")
			doc.append(xdoc.getElementsByTagName("items")[0].toxml())
			doc.append("</ResolveNameResponse>")
			data = "".join(doc)
			content_type = "text/xml"
		else:
			data = self.get_entities()
			content_type = "text/plain"
		mamba.http.HTTPResponse(self, data, content_type).send()


class GetPopup(mamba.task.Request):
	 
	def main(self):
		try:
			doc = xml.dom.minidom.parseString(self.xml)
			found_proteins = []
			for entity in doc.getElementsByTagName('entity'):
				type = entity.getElementsByTagName('type')[0].childNodes[0].nodeValue.strip()
				id   = entity.getElementsByTagName('identifier')[0].childNodes[0].nodeValue.strip()
				found_proteins.append((type, id))
			if len(found_proteins):
				url_params = []
				show_first = ['9606', '10090']
				for pref_organism in show_first:
					for type, id in found_proteins:
						if type == pref_organism:
							url_params.append(type + '.' + id + '+')
				for type, id in found_proteins:
					if type not in show_first:
						url_params.append(type + '.' + id + '+')
				popup_url = 'http://reflect.ws/popup/fcgi-bin/createPopup.fcgi?' + ''.join(url_params)
				popup_url = popup_url[:-1]
        	        	reply = mamba.http.HTTPRedirect(self, popup_url)
				reply.send()
			else:
				html = "<html><head><title>No Reflect popup available</title></head><body>The name '%s' was not found in our dictionary.</body></html>" % self.names[0]
				mamba.http.HTTPResponse(self, html, content_type="text/html").send()
		finally:
			doc.unlink()
