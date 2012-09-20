from mamba.util import mamba.util.strin_to_bytes as utf8str
import mamba.task
import mamba.http
import mamba.setup

class EditRequest(mamba.task.Request):

    def __init__(self, http):
        mamba.task.Request.__init__(self, http)
        self.name = None
        self.document_id = None
                
    def main(self):
        self.parse()
        self.queue('edit')
    


class AddName(EditRequest):
    
    def parse(self):
        rest = mamba.task.RestDecoder(self)
        for check in ('name', 'document_id', 'entity_type', 'entity_identifier'):
            if rest[check] == None:
                raise mamba.task.SyntaxError, 'Required parameter "%s" missing.' % check
        self.name              = rest['name']
        self.document_id       = rest['document_id']
        self.entity_type       = int(rest['entity_type'])
        self.entity_identifier = rest['entity_identifier']
            
    def edit(self):
	mamba.setup.config().tagger.AddName(self.name, self.entity_type, self.entity_identifier, self.document_id)
        reply = mamba.http.HTTPResponse(self, "AddName succeeded. Name/type/ID: '%s'/%s/%s" % (utf8str(self.name), self.entity_type, utf8str(self.entity_identifier)))
        reply.send()
        
        
class AllowName(EditRequest):
    
    def parse(self):
        rest = mamba.task.RestDecoder(self)
        for check in ('name', 'document_id'):
            if rest[check] == None:
                raise mamba.task.SyntaxError, 'Required parameter "%s" missing.' % check
        self.name        = rest['name']
        self.document_id = rest['document_id']
    
    def edit(self):
	mamba.setup.config().tagger.AllowName(self.name, self.document_id)
        reply = mamba.http.HTTPResponse(self, 'AllowName succeeded. Name: "%s"' % utf8str(self.name))
        reply.send()
    

class BlockName(EditRequest):
    
    def parse(self):
        rest = mamba.task.RestDecoder(self)
        for check in ('name', 'document_id'):
            if rest[check] == None:
                raise mamba.task.SyntaxError, 'Required parameter "%s" missing.' % check
        self.name = rest['name']
        self.document_id = rest['document_id']

    def edit(self):
	mamba.setup.config().tagger.BlockName(self.name, self.document_id)
        reply = mamba.http.HTTPResponse(self, 'BlockName succeeded. Name: "%s"' % utf8str(self.name))
        reply.send()
