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
	
	def main(self):
		rest = mamba.task.RestDecoder(self)
		input = json.loads(self.http.body)
		apikey = input["custom_parameters"]["apikey"]
		apiurl = input["custom_parameters"]["apiurl"]
		method = input["method"]
		if method == "getState":
			output = '''{"status":200,"success":true,"key":"%s","data":{"state":"Running","version":"0.4","version_changes":"Use POST for saveAnnotations","max_analizable_documents":100000}}''' % apikey
			mamba.http.HTTPResponse(self, output).send()
		elif method == "getAnnotations":
			commid = input["parameters"]["communication_id"]
			output = '''{"status": 200,"success": true,"key":"%s"}''' % apikey
			mamba.http.HTTPResponse(self, output).send()
			communication_id = input["parameters"]["communication_id"]
			types = input["parameters"]["types"]
			entity_types = []
			auto_detect = False
			if "GENE" in types:
				entity_types.append(9606)
				auto_detect = True
			if "CHEMICAL" in types:
				entity_types.append(-1)
			if "ORGANISM" in types:
				entity_types.append(-2)
			if "SUBCELLULAR_STRUCTURE" in types:
				entity_types.append(-22)
			if "TISSUE_AND_ORGAN" in types:
				entity_types.append(-25)
			if "DISEASE" in types:
				entity_types.append(-26)
			type_map = {
				-1 : "CHEMICAL",
				-2 : "ORGANISM",
				-22 : "SUBCELLULAR_STRUCTURE",
				-25 : "TISSUE_AND_ORGAN",
				-26 : "DISEASE"
			}
			documents = input["parameters"]["documents"]
			abstracts = []
			articles = []
			patents = []
			for document in documents:
				source = document["source"]
				sections = []
				if source == "PATENT SERVER":
					patents.append(document["document_id"])
				elif source == "PMC":
					articles.append(document["document_id"])
				elif source == "PUBMED":
					abstracts.append(document["document_id"])
			for i in xrange(0, len(abstracts), 1000):
				cmd = '''curl --silent --data 'db=pubmed&id=%s&rettype=medline&retmode=text' https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi''' % ",".join(abstracts[i:i+1000])
				rc, so, se = mamba.util.Command(cmd).run()
				pmid = None
				for line in so.replace("\n     ","").splitlines():
					linetype = line[0:5]
					if linetype == "PMID-":
						pmid = line[5:]
					elif linetype == "TI  -":
						if pmid is not None:
							sections.append([pmid, "T", line[5:]])
					elif linetype == "AB  -":
						if pmid is not None:
							sections.append([pmid, "A", line[5:]])
			for i in xrange(0, len(patents), 1000):
				cmd = '''curl --silent -H "Content-Type: application/json" --data '{"patents": %s}' http://193.147.85.10:8087/patentserver/tsv''' % json.dumps(patents[i:i+1000])
				rc, so, se = mamba.util.Command(cmd).run()
				for line in so.splitlines():
					columns = line.split("\t", 2)
					sections.append([columns[0], "T", columns[1]])
					if len(columns) == 3:
						 sections.append([columns[0], "A", columns[2]])
			results = []
			for section in sections:
				matches = mamba.setup.config().tagger.get_matches(document=section[2], document_id=0, entity_types=entity_types, auto_detect=auto_detect)
				for match in matches:
					init, end, entities = match
					if len(entities) > 1:
						continue
					for entity in entities:
						result = {}
						result["document_id"] = section[0]
						result["section"] = section[1]
						result["init"] = init
						result["end"] = end
						result["annotated_text"] = section[2][init:end]
						if entity[0] > 0:
							result["type"] = "GENE"
							result["database_id"] = "%d.%s" % (entity[0], entity[1])
						elif entity[0] in type_map:
							result["type"] = type_map[entity[0]]
							result["database_id"] = entity[1]
						else:
							result["type"] = "unknown"
							result["database_id"] = entity[1]
						results.append(result)
			cmd = "curl --silent --data @- '%s/saveAnnotations/JSON?apikey=%s&communicationId=%s'" % (apiurl, apikey, communication_id)
			pipe = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE)
			pipe.stdin.write(json.dumps(results))
			pipe.stdin.close()
		else:
			mamba.http.HTTPErrorResponse(self, 400, "Request contains an unsupported BeCalm method").send()
