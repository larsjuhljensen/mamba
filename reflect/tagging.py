import os
import re
import sys
import hashlib

import mamba.util
import mamba.task
import mamba.http
import mamba.setup


_taggable_types = ["text/html", "text/plain", "text/xml", "text/tab-separated-values", 'application/msword', 'application/pdf', 'application/vnd.ms-excel']


class TaggingRequest(mamba.task.Request):
	
	def __init__(self, http, action):
		mamba.task.Request.__init__(self, http, action, priority=1)	  
		self.uri = None
		self.doi = None
		self.pmid = None
		self.document = None
		self.document_id = None
		self.entity_types = None
		self.auto_detect = None
		self.auto_detect_doi = None
		self.ignore_blacklist = None
		
	def parse(self):
		rest = mamba.task.RestDecoder(self)
		if "pmid" in rest:
			self.pmid = rest["pmid"]
		if "doi" in rest:
			self.doi  = rest["doi"]
		elif "document_identifier" in rest:
			self.doi = rest["document_identifier"]
		if self.doi and self.doi.startswith('doi:'):
			self.doi = self.doi[4:]
		if "uri" in rest:
			self.uri  = rest["uri"]
		if self.uri and not self.uri.startswith("http"):
			self.uri = "http://"+self.uri
		if "document" in rest:
			self.document = rest["document"]
			if "content_type" in rest and rest["content_type"].lower() == "text/html" or isinstance(self.document, str):
					self.document = unicode(self.document, self.http.charset, errors="replace")
		if "auto_detect" in rest:
			self.auto_detect = int(rest["auto_detect"])
		if "auto_detect_doi" in rest:
			self.auto_detect_doi = int(rest["auto_detect_doi"])
		if "entity_types" in rest:
			self.entity_types = set()
			for type in rest["entity_types"].split():
				self.entity_types.add(int(type))
		if "ignore_blacklist" in rest:
			self.ignore_blacklist = int(rest["ignore_blacklist"])
	
	def set_defaults(self):
		if not self.entity_types:
			self.entity_types = set()
			if mamba.setup.config_is_true(self.user_settings["proteins"]):
				self.entity_types.add(9606)
			if mamba.setup.config_is_true(self.user_settings["chemicals"]):
				self.entity_types.add(-1)
			if mamba.setup.config_is_true(self.user_settings["wikipedia"]):
				self.entity_types.add(-11)
		
		if self.auto_detect == None:
			self.auto_detect =  mamba.setup.config_is_true(self.user_settings["proteins"])
		if self.auto_detect_doi == None:
			self.auto_detect_doi = 1
		if self.ignore_blacklist == None:
			self.ignore_blacklist = 0
		if self.doi:
			self.document_id = self.doi
		elif self.uri:
			self.document_id = self.uri
		elif self.pmid:
			self.document_id = self.pmid
		elif self.document != None:
			hashfun  = hashlib.md5()
			hashfun.update(mamba.util.string_to_bytes(self.document, self.http.charset))
			self.document_id = hashfun.hexdigest()
		else:
			mamba.http.HTTPErrorResponse(self, 400, "Request is missing a document and has no uri, doi or pmid either.").send()

	def download(self):
		if not self.uri and not self.doi and not self.pmid:
			mamba.http.HTTPErrorResponse(self, 400, "Request is missing a document and has no uri, doi or pmid either.").send()
		else:
			fetch_url = None
			if self.doi:
				fetch_url = "http://dx.doi.org/"+self.doi
			elif self.pmid:
				fetch_url = "http://www.ncbi.nlm.nih.gov/sites/entrez/"+str(self.pmid)
			elif self.uri:
				fetch_url = self.uri
			if fetch_url:
				self.info("Downloading: %s" % fetch_url)
				page, status, headers, page_url, charset = mamba.http.Internet().download(fetch_url)
				if charset:
					page = unicode(page, charset, "replace")
					self.http.charset = charset
				if status != 200:
					mamba.http.HTTPErrorResponse(self, status, page).send()
				else:
					page_is_text = False
					if "Content-Type" in headers:
						for accepted in _taggable_types:
							if headers["Content-Type"].lower().startswith(accepted):
								page_is_text = True
								break
					if not page_is_text:
						mamba.http.Redirect(self, location=page_url).send()
					else:
						if page:
							self.uri = page_url # URI could have been changed via multiple redirects.
							self.document = page
							self.queue("tagging")
						else:
							mamba.http.HTTPErrorResponse(self, 404, "Unable to download URI: '%s'" % str(fetch_url)).send()
	
	def convert(self):
		md5 = hashlib.md5()
		md5.update(self.document)
		key = md5.hexdigest()
		if 'bin_dir' in mamba.setup.config().globals:
			bin_dir = mamba.setup.config().globals["bin_dir"]
		else:
			bin_dir = "./bin"
		infile  = "/dev/shm/"+key
		outfile = "/dev/shm/"+key+".html"
		f = open(infile, 'w')
		f.write(self.document)
		f.flush()
		f.close()
		error = 0
		if self.document.startswith('%PDF'):
			self.info("Converting PDF document...")
			error = os.system("%s/pdf2html %s >& /dev/null" % (bin_dir, infile))
		else:
			self.info("Converting document using AbiWord, format either text or binary...")
			error = os.system("unset DISPLAY; abiword --to=html --exp-props='embed-css: yes; embed-images: yes;' %s" % infile)
			if error:
				self.warn("Abiword returned %i. Continue conversion assuming Microsoft Excel format..." % error)
				os.system("%s/xls2csv %s | %s/csv2html > %s" % (bin_dir, infile, bin_dir, outfile))
		f = open(outfile, "r")
		html = f.read();
		f.close()
		try:
			if len(html):
				self.document = unicode(html, "utf-8", "replace")
				return True
			else:
				reply = mamba.http.HTTPErrorResponse(self, 400, "Request contains an unsupported document type")
				reply.send()
				return False
		finally:
				if os.path.exists(infile):
					try:
						os.remove(infile)
					except:
						self.err('Error while removing conversion input file "%s"' % infile)
				if os.path.exists(outfile):
					try:
						os.remove(outfile)
					except:
						self.err('Error while removing convertion output file "%s"' % outfile)
								
	def tagging(self):
		if not isinstance(self.document, unicode) and not self.convert():
			return
		footer = ['<div class="reflect_user_settings" style="display: none;">']
		for key in self.user_settings:
			footer.append('  <span name="%s">%s</span>' % (key, self.user_settings[key]))
		footer.append('</div>\n')
		html = mamba.setup.config().tagger.GetHTML(document=mamba.util.string_to_bytes(self.document, self.http.charset), document_id=self.document_id, entity_types=self.entity_types, auto_detect=self.auto_detect, ignore_blacklist=self.ignore_blacklist, html_footer="\n".join(footer))
		mamba.http.HTTPResponse(self, html, "text/html").send()
		
	def main(self):
		self.parse()
		self.set_defaults()
		if self.document:
			self.queue("tagging")
		else:
			self.queue("download")


class GetHTML(TaggingRequest):
	
	def __init__(self, http):
		TaggingRequest.__init__(self, http, "GetHTML")
		
		
class GetURI(GetHTML):
	
	def __init__(self, http):
		TaggingRequest.__init__(self, http, "GetURI")

	def tagging(self):
		html = mamba.setup.config().tagger.GetHTML(document=mamba.util.string_to_bytes(self.document, self.http.charset), document_id=self.document_id, entity_types=self.entity_types, auto_detect=self.auto_detect, ignore_blacklist=self.ignore_blacklist)
		document = mamba.util.string_to_bytes(html, self.http.charset)
		hashfun  = hashlib.md5()
		hashfun.update(document)
		filename = hashfun.hexdigest()+".html"
		f = open(self.worker.params["tmp_dir"]+"/"+filename, "w")
		f.write(document)
		f.flush()
		f.close()
		mamba.http.HTTPResponse(self, self.worker.params["tmp_uri"]+"/"+filename, "text/html").send()


class GetEntities(TaggingRequest):
	
	def __init__(self, http, action = "GetEntities"):
		TaggingRequest.__init__(self, http, action)
		
	def parse(self):
		TaggingRequest.parse(self)
		rest = mamba.task.RestDecoder(self)
		self.format = "xml"
		if "format" in rest:
			self.format = rest["format"].lower()
		if self.format not in ("xml", "tsv", "csv", "ssv"):
			raise mamba.task.SyntaxError, 'In action: %s unknown format: "%s". Supports only: %s' % (self.action, self.format, ', '.join(supported_formats))
		
	def tagging(self):
		data = mamba.setup.config().tagger.GetEntities(document=mamba.util.string_to_bytes(self.document, self.http.charset), document_id=self.document_id, entity_types=self.entity_types, auto_detect=self.auto_detect, ignore_blacklist=self.ignore_blacklist, format=self.format)
		content_type = "text/plain"
		if self.format == "xml":
			content_type = "text/xml"
		mamba.http.HTTPResponse(self, data, content_type).send()
