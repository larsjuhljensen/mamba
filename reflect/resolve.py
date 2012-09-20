import xml.dom.minidom

import mamba.task
import mamba.http
import mamba.setup

import tagging


class GetHead(mamba.task.EmptyRequest):
    
    def main(self):
        reply = mamba.http.HTTPResponse(self, mamba.setup.config().globals["java_scripts"])
        reply.send()


class GetHeader(GetHead):
    pass


class ResolveRequest(tagging.GetEntities):
    
    def __init__(self, http, action):
        tagging.GetEntities.__init__(self, http, action)
        self.names = None
        self.xml   = None
        
    def parse(self):
        rest = mamba.task.RestDecoder(self)
        names = None
        if rest['name']:
            names = rest['name']
        elif rest['names']:
            names = rest['names']
        else:
            raise mamba.task.SyntaxError, 'Required parameter "name" or "names" is missing.'
        self.names = map(lambda s: s.strip(), filter(lambda s: len(s) > 0, names.split('\\n')))     
        
    def prepare_document(self):
        temp = ''
        for name in self.names:
            temp += '<P>' + name + '</P>'
        self.document          = temp
        self.doc_type          = 'text/html'
        self.auto_detect       = 0
        self.auto_detect_doi   = 0
        self.entity_types      = [(0,0), (-1,0)]
        self.entity_styles     = {}
        self.entity_styles[0]  = mamba.setup.config().tagger.class_styles[0][1]
        self.entity_styles[-1] = mamba.setup.config().tagger.class_styles[-1][1]
            
    def tagging(self):
        self.prepare_document()
        self.xml = self.get_entities()
        self.post_process()
        
    def main(self):
        self.parse()
        self.queue('tagging')
    
        
class ResolveName(ResolveRequest):
    
    def __init__(self, http):
        ResolveRequest.__init__(self, http, 'ResolveName')
        
    def parse(self):
        ResolveRequest.parse(self)
        tagging.GetEntities.parse(self)
        
    def post_process(self):
        if self.format == "xml":
            doc = []
            xdoc = xml.dom.minidom.parseString(self.xml)
            doc.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
            doc.append("<ResolveNameResponse xmlns=\"Reflect\" xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">")
            doc.append(xdoc.getElementsByTagName("items")[0].toxml())
            doc.append("</ResolveNameResponse>")
            data = "".join(doc)
            content_type = "text/xml"
        else:
            data = self.get_entities()
            content_type = "text/plain"
        reply = mamba.http.HTTPResponse(self, data, content_type)
        reply.send()


class GetPopup(ResolveRequest):
    
    def __init__(self, http):
        ResolveRequest.__init__(self, http, "GetPopup")
            
    def post_process(self):
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
                reply = mamba.http.HTTPResponse(self, html, content_type="text/html")
                reply.send()
        finally:
            doc.unlink()
