import sys
import mamba.http
import mamba.setup
import mamba.task
import ranker


class Setup(mamba.setup.Configuration):

	def __init__(self, ini_file):
		mamba.setup.Configuration.__init__(self, ini_file)
		sys.stdout.write('[INIT]  Loading C/C++ module implementing ranked Pubmed search...')
		self.document_ranker = ranker.Ranker()
		for file in self.globals['mentions'].split(' '):
			self.document_ranker.read_mentions(file);
		sys.stdout.write('done\n')


class RankDocuments(mamba.task.Request):
	
	def main(self):
		rest = mamba.task.RestDecoder(self)
		
		alpha = 0.8
		if "alpha" in rest:
			alpha = float(rest["alpha"])
		
		documents = []
		if "documents" in rest:
			documents = map(int, rest["documents"].split(','))
		
		positives = []
		if "positives" in rest:
			positives = map(int, rest["positives"].split(','))
		
		negatives = []
		if "negatives" in rest:
			negatives = map(int, rest["negatives"].split(','))
		
		result = mamba.setup.config().document_ranker.rank_documents(documents, positives, negatives, alpha)
		mamba.http.HTTPResponse(self, ','.join(map(str,result)), 'text/plain').send()
