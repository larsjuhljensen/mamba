import os
import re
import sys
import hashlib

import mamba.http
import mamba.setup
import mamba.task
import mamba.util


_taggable_types = ["text/html", "text/plain", "text/xml", "text/tab-separated-values", 'application/msword', 'application/pdf', 'application/vnd.ms-excel']


class TaggingRequest(mamba.task.Request):
	
	def __init__(self, http, action):
		mamba.task.Request.__init__(self, http, action, priority=1)	  
	
	def parse(self, rest):
		self.hash = None
		if "hash" in rest:
			self.hash = rest["hash"]
		self.document = None
		if "document" in rest:
			self.document = rest["document"]
			if "content_type" in rest and rest["content_type"].lower() == "text/html" or isinstance(self.document, str):
				self.document = unicode(self.document, self.http.charset, errors="replace")
		
		self.document_id = None
		self.document_url = None
		doi = None
		if "doi" in rest:
			doi  = rest["doi"]
		elif "document_identifier" in rest:
			doi = rest["document_identifier"]
		if doi:
			if self.doi.startswith('doi:'):
				doi = doi[4:]
			self.document_id = doi
			self.document_url = "http://dx.doi.org/"+doi
		elif "uri" in rest:
			if rest["uri"].startswith("http"):
				self.document_id = rest["uri"]
				self.document_url = rest["uri"]
			else:
				self.document_id = "http://"+rest["uri"]
				self.document_url = "http://"+rest["uri"]
		elif "pmid" in rest:
			self.document_id = rest["pmid"]
			self.document_url = "http://www.ncbi.nlm.nih.gov/pubmed/"+rest["pmid"]
		elif self.hash != None:
			self.document_id = self.hash
		
		self.auto_detect = 1
		if "auto_detect" in rest:
			self.auto_detect = int(rest["auto_detect"])
		self.auto_detect_doi = 1
		if "auto_detect_doi" in rest:
			self.auto_detect_doi = int(rest["auto_detect_doi"])
		self.ignore_blacklist = 0
		if "ignore_blacklist" in rest:
			self.ignore_blacklist = int(rest["ignore_blacklist"])
		
		if "entity_types" in rest:
			self.entity_types = set()
			for type in rest["entity_types"].split():
				self.entity_types.add(int(type))
		else:
			self.entity_types = set()
			if hasattr(self, "user_settings"):
				if "proteins" in self.user_settings and mamba.setup.config_is_true(self.user_settings["proteins"]):
					self.entity_types.add(9606)
				if "chemicals" in self.user_settings and mamba.setup.config_is_true(self.user_settings["chemicals"]):
					self.entity_types.add(-1)
				if "wikipedia" in self.user_settings and mamba.setup.config_is_true(self.user_settings["wikipedia"]):
					self.entity_types.add(-11)
	
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
		if self.document.startswith('%PDF'):
			os.system("%s/pdf2html %s >& /dev/null" % (bin_dir, infile))
		elif os.system("unset DISPLAY; abiword --to=html --exp-props='embed-css: yes; embed-images: yes;' %s" % infile):
			os.system("%s/xls2csv %s | %s/csv2html > %s" % (bin_dir, infile, bin_dir, outfile))
		f = open(outfile, "r")
		html = f.read();
		f.close()
		os.remove(infile)
		os.remove(outfile)
		if len(html):
			self.document = unicode(html, "utf-8", "replace")
			self.queue("main")
		else:
			mamba.http.HTTPErrorResponse(self, 400, "Request contains an unsupported document type").send()
	
	def download(self):
		self.info("Downloading: %s" % self.document_url)
		page, status, headers, page_url, charset = mamba.http.Internet().download(self.document_url)
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
			elif page:
				self.uri = page_url # URI could have been changed via multiple redirects.
				self.document = page
				self.queue("main")
			else:
				mamba.http.HTTPErrorResponse(self, 404, "Unable to download URI: '%s'" % str(fetch_url)).send()
	
	def main(self):
		if not hasattr(self, "document"):
			self.parse(mamba.task.RestDecoder(self))
		if self.http.method == "OPTIONS":
			mamba.http.HTTPResponse(self, "").send()
		elif isinstance(self.document, unicode):
			self.queue("tagging")
		elif self.document != None:
			self.queue("convert")
		elif self.document_url != None:
			self.queue("download")
		elif self.hash != None:
			self.load()
		else:
			mamba.http.HTTPErrorResponse(self, 400, "Request is missing a document and has no uri, doi or pmid either.").send()


class OpenAnnotation(TaggingRequest):
	
	def __init__(self, http, action = "OpenAnnotation"):
		TaggingRequest.__init__(self, http, action)
	
	def parse(self, rest):
		TaggingRequest.parse(self, rest)
		self.annotation_index = None
		if "annotation_index" in rest:
			self.annotation_index = int(rest["annotation_index"])
		if not "entity_types" in rest:
			self.entity_types = set([9606,-1,-2,-22,-25,-26,-27])

	def tagging(self):
		data = mamba.setup.config().tagger.get_jsonld(document=mamba.util.string_to_bytes(self.document, self.http.charset), document_charset=self.http.charset, document_id=self.document_id, annotation_index=self.annotation_index, entity_types=self.entity_types, auto_detect=self.auto_detect, ignore_blacklist=self.ignore_blacklist)
		mamba.http.HTTPResponse(self, data, "application/ld+json").send()


class GetEntities(TaggingRequest):
	
	def __init__(self, http, action = "GetEntities"):
		TaggingRequest.__init__(self, http, action)
	
	def parse(self, rest):
		TaggingRequest.parse(self, rest)
		self.format = "xml"
		if "format" in rest:
			self.format = rest["format"].lower()
		if self.format not in ("xml", "tsv", "csv", "ssv"):
			raise mamba.task.SyntaxError, 'In action: %s unknown format: "%s". Supports only: %s' % (self.action, format, ', '.join(supported_formats))		
	
	def tagging(self):
		data = mamba.setup.config().tagger.get_entities(document=mamba.util.string_to_bytes(self.document, self.http.charset), document_id=self.document_id, entity_types=self.entity_types, auto_detect=self.auto_detect, ignore_blacklist=self.ignore_blacklist, format=self.format)
		if format == "xml":
			mamba.http.HTTPResponse(self, data, "text/xml").send()
		else:
			mamba.http.HTTPResponse(self, data, "text/plain").send()


class GetHTML(TaggingRequest):
	
	def __init__(self, http):
		TaggingRequest.__init__(self, http, "GetHTML")
	
	def load(self):
		try:
			f = open(self.worker.params["tmp_dir"]+"/"+self.hash+".html", "r")
			self.document = f.read()
			f.close()
			mamba.http.HTMLResponse(self, self.document).send()
		except:
			mamba.http.HTTPErrorResponse(self, 404, "Pretagged document not available.").send()
	
	def respond(self):
		if self.hash != None:
			self.save()
		mamba.http.HTMLResponse(self, self.document).send()
		
	def save(self):
		if self.hash == None:
			hash  = hashlib.md5()
			hash.update(mamba.util.string_to_bytes(self.document, self.http.charset))
			self.hash = hash.hexdigest()
		f = open(self.worker.params["tmp_dir"]+"/"+self.hash+".html", "w")
		f.write(mamba.util.string_to_bytes(self.document, self.http.charset))
		f.close()
	
	def tagging(self):
		footer = ['<div class="reflect_user_settings" style="display: none;">']
		for key in self.user_settings:
			footer.append('  <span name="%s">%s</span>' % (key, self.user_settings[key]))
		footer.append('</div>\n')
		self.document = mamba.setup.config().tagger.get_html(document=mamba.util.string_to_bytes(self.document, self.http.charset), document_id=self.document_id, entity_types=self.entity_types, auto_detect=self.auto_detect, ignore_blacklist=self.ignore_blacklist, basename='reflect', add_events=True, extra_classes=False, force_important=True, html_footer="\n".join(footer))
		self.respond()


class GetURI(GetHTML):
	
	def __init__(self, http):
		TaggingRequest.__init__(self, http, "GetURI")
	
	def respond(self):
		self.save()
		mamba.http.HTTPResponse(self, self.worker.params["tmp_dir"]+"/"+self.hash+".html", "text/plain").send()
