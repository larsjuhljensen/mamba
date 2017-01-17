import os
import re
import json
import subprocess
import sys

import mamba.http
import mamba.setup
import mamba.task
import mamba.util


class BeCalm(mamba.task.Request):

	def download(self):
		abstracts = []
		articles = []
		patents = []
		for document in self.documents:
			source = document["source"]
			if source == "PATENT SERVER":
				patents.append(document["document_id"])
			elif source == "PMC":
				articles.append(document["document_id"])
			elif source == "PUBMED":
				abstracts.append(document["document_id"])
		self.sections = []
		for i in xrange(0, len(abstracts), 1000):
			cmd = '''curl --silent --data 'db=pubmed&id=%s&rettype=medline&retmode=text' https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi''' % ",".join(abstracts[i:i+1000])
			rc, so, se = mamba.util.Command(cmd).run()
			pmid = None
			for line in so.replace("\n     ","").splitlines():
				linetype = line[0:5]
				if linetype == "PMID-":
					pmid = line[6:]
				elif linetype == "TI  -":
					if pmid is not None:
						self.sections.append([pmid, "T", line[6:]])
				elif linetype == "AB  -":
					if pmid is not None:
						self.sections.append([pmid, "A", line[6:]])
		for i in xrange(0, len(patents), 1000):
			cmd = '''curl --silent -H "Content-Type: application/json" --data '{"patents": %s}' http://193.147.85.10:8087/patentserver/tsv''' % json.dumps(patents[i:i+1000])
			rc, so, se = mamba.util.Command(cmd).run()
			for line in so.splitlines():
				columns = line.split("\t", 2)
				self.sections.append([columns[0], "T", columns[1]])
				if len(columns) == 3:
					 self.sections.append([columns[0], "A", columns[2]])
		self.queue("tagging")
	
	def tagging(self):
		type_map = {
			-1 : "CHEMICAL",
			-2 : "ORGANISM",
			-22 : "SUBCELLULAR_STRUCTURE",
			-25 : "TISSUE_AND_ORGAN",
			-26 : "DISEASE"
		}
		results = []
		for section in self.sections:
			matches = mamba.setup.config().tagger.get_matches(document=section[2], document_id=0, entity_types=self.entity_types, auto_detect=self.auto_detect)
			for match in matches:
				init, end, entities = match
				if self.disambiguate and len(entities) > 1:
					continue
				result = {}
				result["document_id"] = section[0]
				result["section"] = section[1]
				result["init"] = init
				result["end"] = end+1
				result["annotated_text"] = section[2][init:end+1]
				types = set()
				database_ids = []
				for entity in entities:
					if entity[0] > 0:
						types.add("GENE")
						database_ids.append("%d.%s" % (entity[0], entity[1]))
					elif entity[0] in type_map:
						types.add(type_map[entity[0]])
						database_ids.append(entity[1])
					else:
						types.add("unknown")
						database_ids.append(entity[1])
				if len(types) == 1:
					result["type"] = "".join(types)
				else:
					result["type"] = "unknown"
				result["database_id"] = ",".join(database_ids)
				results.append(result)
		if self.debug:
			print "[DEBUG] %s" % results
		cmd = "curl --silent --data @- '%s/saveAnnotations/JSON?apikey=%s&communicationId=%s'" % (self.apiurl, self.apikey, self.communication_id)
		devnull = open(os.devnull, "w")
		pipe = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=devnull, stderr=subprocess.STDOUT)
		pipe.stdin.write(json.dumps(results))
		pipe.stdin.close()

	def main(self):
		rest = mamba.task.RestDecoder(self)
		input = json.loads(self.http.body)
		self.apikey = input["custom_parameters"]["apikey"]
		self.apiurl = input["custom_parameters"]["apiurl"]
		self.cache = True
		if "cache" in input["custom_parameters"]:
			self.cache = input["custom_parameters"]["cache"]
		self.debug = False
		if "debug" in input["custom_parameters"]:
			self.debug = input["custom_parameters"]["debug"]
		self.disambiguate = True
		if "disambiguate" in input["custom_parameters"]:
			self.disambiguate = input["custom_parameters"]["disambiguate"]
		method = input["method"]
		if method == "getState":
			mamba.http.HTTPResponse(self, '''{"status":200,"success":true,"key":"%s","data":{"state":"Running","version":"0.5","version_changes":"Better use of queue.","max_analyzable_documents":100000}}''' % self.apikey).send()
		elif method == "getAnnotations":
			mamba.http.HTTPResponse(self, '''{"status": 200,"success": true,"key":"%s"}''' % self.apikey).send()
			self.communication_id = input["parameters"]["communication_id"]
			self.entity_types = []
			self.auto_detect = False
			types = input["parameters"]["types"]
			if "GENE" in types:
				self.entity_types.append(9606)
				self.auto_detect = True
			if "CHEMICAL" in types:
				self.entity_types.append(-1)
			if "ORGANISM" in types:
				self.entity_types.append(-2)
			if "SUBCELLULAR_STRUCTURE" in types:
				self.entity_types.append(-22)
			if "TISSUE_AND_ORGAN" in types:
				self.entity_types.append(-25)
			if "DISEASE" in types:
				self.entity_types.append(-26)
			self.documents = input["parameters"]["documents"]
			self.queue("download")
		else:
			mamba.http.HTTPErrorResponse(self, 400, "Request contains an unsupported BeCalm method").send()
