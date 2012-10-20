import os
import re
import sys
import hashlib

import mamba.util
import mamba.task
import mamba.http
import mamba.setup


_taggable_types = ['text/html', 'text/plain', 'text/xml', 'text/tab-separated-values', 'application/msword', 'application/pdf', 'application/vnd.ms-excel']


def first_DOI_in_html_body(document):
    doi_match  = _re_doi.search(document)
    if doi_match:
        return doi_match.group(2)
    return None


class TaggingRequest(mamba.task.Request):
    
    def __init__(self, http, action):
        mamba.task.Request.__init__(self, http, action, priority=1)      
        self.uri              = None # Universal Resource Identifier.
        self.doi              = None # Digital Object Identifier (see dx.doi.org).
        self.pmid             = None # Pubmed ID.
        self.document         = None # The document as a string.
        self.document_id      = None # Either the DOI, URI, PMID or CHECKSUM.
        self.entity_types     = None # Entity types (chemicals, tax etc.)
        self.auto_detect      = None # Autodetection of entities.
        self.auto_detect_doi  = None # Autodetect DOI from attached document.
        self.ignore_blacklist = None # Completely ignore any blocking rules.
        
    def parse(self):
        #
        # Remember: This method returns True/False + rest object.
        # The reason is that derived classes may look for further
        # REST parameters that they need.
        #
        rest = mamba.task.RestDecoder(self)
        
        self.pmid = rest['pmid']
        self.doi  = rest['doi']
        self.uri  = rest['uri']
        
        if self.uri:
            if not self.uri.startswith('http'):
                self.uri = 'http://'+self.uri
        
        self.document = rest['document']
        
        if self.document != None:
            content_type = rest['content_type']
            if content_type == None:
                #
                # Assume the document is a HTML document with <html><head></head><body></body></html> structure.
                # Unicode the string to conserve all unicode characters.
                #
                if isinstance(self.document, str):
                    self.document = unicode(self.document, self.http.charset, errors='replace')
            else:
                #
                # In case 'content_type' is set and its 'text/html' then fine. We just unicode the document.
                # If the content_type is different from HTML then we force AbiWord conversion even on
                # plain text to get header and body structure so popups work.
                #
                if content_type.lower() == 'text/html':
                    self.document = unicode(self.document, self.http.charset, errors='replace')
                
        #
        # Try the alternative name for a DOI: document_identifier
        # This is used by Elsevier.
        #
        if not self.doi:
            self.doi = rest['document_identifier']
        else:
            if self.doi.startswith('doi:'):
                self.doi = self.doi[4:]  # Remove 'doi:' if its there.
            
        if rest['auto_detect']:
            try:
                self.auto_detect = int(rest['auto_detect'])
            except ValueError, e:
                raise mamba.task.SyntaxError, 'auto_detect must be either 0 or 1.'
            
        if rest['auto_detect_doi']:
            try:
                self.auto_detect_doi = int(rest['auto_detect_doi'])
            except ValueError, e:
                raise mamba.task.SyntaxError, 'auto_detect_doi must be either 0 or 1.'
            
        if rest['ignore_blacklist']:
            try:
                self.ignore_blacklist = int(rest['ignore_blacklist'])
            except ValueError, e:
                raise mamba.task.SyntaxError, 'ignore_blacklist must be either 0 or 1.'
            
        if rest['entity_types']:
            self.entity_types = set()
            types = rest['entity_types'].split()
            for type in types:
                try:
                    self.entity_types.add(int(type))
                except ValueError, e:
                    raise mamba.task.SyntaxError, 'All elements in entity_types must be integers.'

    def set_defaults(self):
        if not self.entity_types:
            self.entity_types = set()
            if mamba.setup.config_is_true(self.user_settings['proteins']):
                self.entity_types.add(9606)
            if mamba.setup.config_is_true(self.user_settings['chemicals']):
                self.entity_types.add(-1)
            if mamba.setup.config_is_true(self.user_settings['wikipedia']):
                self.entity_types.add(-11)
        
        #
        # Auto-detect and auto-detect-DOI.
        #
        if self.auto_detect == None:
            self.auto_detect =  mamba.setup.config_is_true(self.user_settings['proteins'])
            
        if self.auto_detect_doi == None:
            self.auto_detect_doi = 1
            
        if self.ignore_blacklist == None:
            self.ignore_blacklist = 0
            
        #
        # Fill in document_id based on DOI/URI/PMID information.
        #
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
            reply = mamba.http.HTTPErrorResponse(self, 400, 'Request is missing a document and has no uri, doi or pmid either.')
            reply.send()

    def download(self):
        if not self.uri and not self.doi and not self.pmid:
            reply = mamba.http.HTTPErrorResponse(self, 400, 'Request is missing a document and has no uri, doi or pmid either.')
            reply.send()
        else:
            fetch_url = None
            if self.doi:
                fetch_url = "http://dx.doi.org/" + self.doi
            elif self.pmid:
                fetch_url = "http://www.ncbi.nlm.nih.gov/sites/entrez/" + str(self.pmid)
            elif self.uri:
                fetch_url = self.uri
            if fetch_url:
                self.info("Downloading: %s" % fetch_url)    
                page, status, headers, page_url, charset = mamba.http.Internet().download(fetch_url)
                if charset:
                    page = unicode(page, charset, "replace")
                    self.http.charset = charset
                if status != 200:
                    reply = mamba.http.HTTPErrorResponse(self, status, page)
                    reply.send()
                else:
                    page_is_text = False
                    if "Content-Type" in headers:
                        for accepted in _taggable_types:
                            if headers["Content-Type"].lower().startswith(accepted):
                                page_is_text = True
                                break       
                    if not page_is_text:
                        reply = mamba.http.Redirect(self, location=page_url)
                        reply.send()
                    else:
                        if page:
                            self.uri = page_url # URI could have been changed via multiple redirects.
                            self.document = page
                            self.queue("tagging")
                        else:
                            reply = mamba.http.HTTPErrorResponse(self, 404, "Unable to download URI: '%s'" % str(fetch_url))
                            reply.send()
    
    def convert(self):
        md5 = hashlib.md5()
        md5.update(self.document)
        key = md5.hexdigest()
        if 'bin_dir' in mamba.setup.config().globals:
            bin_dir = mamba.setup.config().globals['bin_dir']
        else:
            bin_dir = './bin'
        infile  = '/dev/shm/' + key
        outfile = '/dev/shm/' + key + '.html'
        f = open(infile, 'w')
        f.write(self.document)
        f.flush()
        f.close()
        error = 0
        if self.document.startswith('%PDF'):
            self.info('Converting PDF document...')
            error = os.system('%s/pdf2html %s >& /dev/null' % (bin_dir, infile))
        else:
            self.info('Converting document using AbiWord, format either text or binary...')
            error = os.system('unset DISPLAY; abiword --to=html --exp-props="embed-css: yes; embed-images: yes;" %s' % infile)
            if error:
                self.warn('Abiword returned %i. Continue conversion assuming Microsoft Excel format...' % error)
                os.system('%s/xls2csv %s | %s/csv2html > %s' % (bin_dir, infile, bin_dir, outfile))
        f = open(outfile, 'r')
        html = f.read();
        f.close()
        try:
            if len(html):
                self.document = unicode(html, 'utf-8', 'replace')
                return True
            else:
                reply = mamba.http.HTTPErrorResponse(self, 400, 'Request contains an unsupported document type')
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
        if not isinstance(self.document, unicode):
            if not self.convert():
                return  # Return is important because if converts return False then
                        # a response has already been send back and we are done.
        byte_doc  = mamba.util.string_to_bytes(self.document, self.http.charset)
        doc_id    = self.document_id
        footer = ['<div class="reflect_user_settings" style="display: none;">']
        for key in self.user_settings:
            footer.append('  <span name="%s">%s</span>' % (key, self.user_settings[key]))
        footer.append('</div>\n')
        html = mamba.setup.config().tagger.GetHTML(document=byte_doc, document_id=doc_id, entity_types=self.entity_types, auto_detect=self.auto_detect, ignore_blacklist=self.ignore_blacklist, html_footer='\n'.join(footer))
        reply = mamba.http.HTTPResponse(self, html, "text/html")
        reply.send()
        
    def main(self):
        self.parse()
        self.set_defaults()
        if self.document:
            self.queue('tagging')
        else:
            self.queue('download')


class GetHTML(TaggingRequest):
    
    def __init__(self, http):
        TaggingRequest.__init__(self, http, 'GetHTML')
        
        
class GetURI(GetHTML):
    
    def __init__(self, http):
        TaggingRequest.__init__(self, http, 'GetURI')

    def tagging(self):
        byte_doc  = mamba.util.string_to_bytes(self.document, self.http.charset)
        doc_id    = self.document_id
        html = mamba.setup.config().tagger.GetHTML(byte_doc, doc_id, self.entity_types, self.auto_detect, self.ignore_blacklist)
        document = mamba.util.string_to_bytes(html, self.http.charset)
        hashfun  = hashlib.md5()
        hashfun.update(document)
        filename = hashfun.hexdigest() + '.html'                
        f = open(self.worker.params['tmp_dir']+'/'+filename, 'w')
        f.write(document)
        f.flush()
        f.close()               
        reply = mamba.http.HTTPResponse(self, self.worker.params['tmp_uri']+'/'+filename, 'text/html')
        reply.send()


class GetEntities(TaggingRequest):
    
    def __init__(self, http, action = 'GetEntities'):
        TaggingRequest.__init__(self, http, action)
        self.format = 'xml'
        
    def parse(self):
        TaggingRequest.parse(self)
        rest = mamba.task.RestDecoder(self)
        self.format = rest['format']
        if self.format == None:
            self.format = 'xml'
        self.format = self.format.lower()
        supported_formats = ('xml', 'tsv', 'csv', 'ssv')
        if self.format not in supported_formats:
            raise mamba.task.SyntaxError, 'In action: %s unknown format: "%s". Supports only: %s' % (self.action, self.format, ', '.join(supported_formats))
        
    def get_entities(self):
        return mamba.setup.config().tagger.GetEntities(mamba.util.string_to_bytes(self.document, self.http.charset), self.document_id, self.entity_types, self.auto_detect, self.ignore_blacklist, format=self.format)
        
    def tagging(self):
        data = self.get_entities()
        if self.format == 'xml':
            content_type = 'text/xml'
        else:
            content_type = 'text/plain'
        reply = mamba.http.HTTPResponse(self, data, content_type)
        reply.send()
