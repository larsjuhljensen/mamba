import pg
import urllib
import database
import mamba.setup
import mamba.task
import html
import xpage
import search
import hashlib
import json
from collections import defaultdict

globPhases = ["G1","S","G2","M"]

def get_phase(cycleinfo_dict,organism,peaktime):
	valid_transitions = ["G1/S","G2/M"]
	phase = []
	sorted_keys = sorted(cycleinfo_dict[organism].keys(), key=lambda x:x[0])
	for start,end in sorted_keys:
		transition = end + (end-start)/5
		if(peaktime is None):
			phase.append("non-periodic")
			break
		else:
			peaktime = float(peaktime)
			if (peaktime >= start and peaktime < transition):
				    phase.append(cycleinfo_dict[organism][start,end])
				    
	identified_phase = "/".join(phase)
	return identified_phase if identified_phase in valid_transitions else phase.pop()

def get_peak_range(cycleinfo_dict,organism,phase):
	peak_range = ()
	for start,end in cycleinfo_dict[organism]:
		if(cycleinfo_dict[organism][start,end] == phase):
			peak_range = (start,end)
			break
	return peak_range

def get_combined_results(id1,type1):
    return ("SELECT  id as id1,type as type1,rank,peak_time FROM combinedresults WHERE id='%s' and type=%d")% (id1,int(type1))

def get_icons(id1,type1):
    return ("SELECT label FROM colors WHERE id ='%s' AND figure LIKE 'cyclebase_%%' AND label LIKE '%%phenotype%%' AND type=%s AND score >= 2;"% (id1, type1))

def get_cycleinfo(organisms):
	formated_organisms = []
	for organism in organisms:
		formated_organisms.append("\'"+str(organism)+"\'")
	organisms_sql = "type IN (%s)" % (",".join(formated_organisms))
	
	return ("SELECT type, phase, start_phase,end_phase FROM organismcycles WHERE %s ORDER BY start_phase ASC")% (organisms_sql)

def get_cyclebase_gene_info(data):
	result = []
	if len(data):
		cyb_db = database.Connect("cyclebase")
		vis_db = database.Connect("visualization")
		evidences = []
		organisms = {}
		for row in data:
			id1 = row["id1"]
			type1 = row["type1"]
			url = build_url(id1,str(type1))
			evidence = cyb_db.query(get_combined_results(id1, type1)).dictresult()
			figures = vis_db.query(get_icons(id1,type1)).dictresult()
			organisms[type1] = 1
			if(len(evidence) > 0):
				evidence = evidence.pop(0)
				if "id2" in row and "type2" in row:
					id2 = row["id2"]
					type2 = row["type2"]
					evidence.update({"id2":id2, "type2": type2})
				if "homology" in row:
					evidence.update({"homology":row["homology"]})
				rank = evidence["rank"]
				evidence.update({"url":url})
				phenos = ""
				if len(figures):
					phenotypes = {}
					for figure in figures:
						label = figure["label"]
						phase = label.split('_')[0]
						phenotypes[phase] = 1
					phenos = ",".join(phenotypes.keys())
					phenos = phenos.replace("M","SM").replace("G2","SG2")
					phenos = sorted(phenos.split(","))
					phenos = ", ".join(phenos)
					phenos = phenos.replace("SM","M").replace("SG2","G2")
				evidence.update({'phenotypes':phenos})
				evidences.append((rank,evidence))
		if len(evidences):
			cycleinfo = cyb_db.query(get_cycleinfo(organisms.keys())).dictresult()
			cycleinfo_dict = simplify_dictionary(cycleinfo)
			
			sorted_evidences= sorted(evidences, key=lambda x:x[0])
			ranks, evidences = zip(*sorted_evidences)
			
			result = []
			for evidence in evidences:
			    organism = evidence["type1"]
			    evidence["peak_time"] = get_phase(cycleinfo_dict,organism,evidence["peak_time"])
			    result.append(evidence)
	return result

def simplify_dictionary(dictionary):
	simple_dict = {}
	for row in dictionary:
		if(not simple_dict.has_key(row["type"])):
			simple_dict[row["type"]] = {}
		simple_dict[row["type"]].update({(row["start_phase"],row["end_phase"]):row["phase"]})
	
	return(simple_dict)    

def build_url(id,type):
	fix_url = '/CyclebasePage?type=TYPE&id=ID'
	return fix_url.replace('ID',id).replace('TYPE',type)

def tuples_to_dict(tuples_list):
	dictionary = {}
	for a,b,c in tuples_list:
		if(not dictionary.has_key(a)):
			dictionary[a] = {}
		dictionary[a].update({b:c})
		
	return dictionary

class Cyclebase(mamba.task.Request):
	def main(self):
		rest = mamba.task.RestDecoder(self)
		identifier =  rest["id"]
		organism = rest["type"]
		org_sql = "type = %s" % (organism)
		id_sql = "id = '%s'" %(identifier)
		arrayjson = []
		
		#Get Cyclebase data - Cycle, Time-course data
		conn_cyclebase = database.Connect("cyclebase")
		#Individual results ids-y_values
		individual_results = conn_cyclebase.query("SELECT * FROM individualresults WHERE %s AND %s;"% (org_sql, id_sql)).dictresult()
		#Combined results source-x_values
		combined_results = conn_cyclebase.query("SELECT * FROM combinedresults WHERE %s AND %s;"% (org_sql,id_sql)).dictresult()
		#Cycle information percent each phase takes 
		cycle_info = conn_cyclebase.query("SELECT phase, start_phase, end_phase FROM organismcycles WHERE %s ORDER BY start_phase ASC;"% (org_sql)).dictresult()
		
		#Icons
		conn_visualization = database.Connect("visualization")
		#Icons to draw
		colors = conn_visualization.query("SELECT figure, label FROM colors WHERE figure LIKE 'cyclebase_%%' AND %s AND %s AND score >= 2;"% (org_sql, id_sql)).getresult()
		if(len(combined_results) > 0 and len(individual_results) > 0 and len(cycle_info) > 0):
			combined_results = combined_results.pop(0)
			average_expression = json.dumps(combined_results['average_expression'])#.replace("{","[").replace("}","]").replace('NaN','null')
			average_prot = ""
			if combined_results.has_key('average_protein') and combined_results['average_protein'] is not None:
				average = json.dumps(combined_results['average_protein'])
				average_prot = ",\"average_protein\":"+average
			arrayjson = ["{\"id\":\""+identifier+"\",\"results\":[{\"combined\":{\"rank\":"+str(combined_results["rank"])+",\"peak\":\""+str(combined_results["peak_time"])+"\",\"p_value\":"+str(combined_results["periodicity_pvalue"])+",\"average_expression\":"+average_expression+average_prot+"}},{\"individual\":["]
			
			string = "{\"id\":\"%s\",\"source\":\"%s\",\"visible\":\"%s\"}"
			
			for registry in individual_results:
				probeset = registry["probeset"]
				source = registry["source"]
				show = registry["visible"]
				arrayjson.append(string %(probeset,source,show))
				arrayjson.append(",")
			arrayjson = arrayjson[:-1]
			arrayjson.append("]}],\"cycleinfo\":[")
			
			
			phase_string = "{\"phase\": \"%s\",\"from\":%d,\"to\":%d}"
			for registry in cycle_info:
				phase = registry["phase"]
				start = float(registry["start_phase"])
				end = float(registry["end_phase"])
				arrayjson.append(phase_string%(phase,start,end))
				arrayjson.append(",")
			arrayjson = arrayjson[:-1]
			arrayjson.append("]")
			if len(colors):
				arrayjson.append(",\"icons\":[{")
				for figure,label in colors:
					figure_data = conn_visualization.query("SELECT svg,paint FROM figures WHERE figure = '%s'" % figure).getresult()
					for svg,paint in figure_data:
						if paint:
							arrayjson.append("\""+label+"\":\""+svg+"\"}")
							arrayjson.append(",{")
				arrayjson = arrayjson[:-1]
				arrayjson.append("]")
			arrayjson.append("}")
		else:
		    arrayjson = ["{","}"]
		mamba.http.HTTPResponse(self,"".join(arrayjson), "application/json").send()

class CyclebaseGroups(xpage.Groups):
	def add_head(self):
		self.xtable.addhead("Name", "Organism", "Rank", "Peaktime","Phenotypes")
		
	def add_row(self, row, name, organism, format): 
		if format == "html":
			if row.has_key("url") and row["url"] !="":
				link = '<a class="silent_link" target = _blank href="%s">%%s</a>' % (row["url"])
				self.xtable.addrow(link % name, link % organism,link % row["rank"], link % row["peak_time"],link % row["phenotypes"])
			else:
				self.xtable.addrow(name,organism,row["rank"], row["peak_time"],row["phenotypes"])
		elif format == "json":
		    visible = "true"
		    self.json.append('''"%s":{"name":"%s","organism":"%s", "Rank":%d, "Peaktime":%s, "Phenotypes": %s,"visible":%s,"url":%s}'''% (row["id1"], name,organism,row["rank"],row["peak_time"], row["phenotypes"], visible,row["url"]))

	def get_rows(self, rest, species, filter):
		ortho_evidences = xpage.Groups.get_rows(self, rest, species, filter)
		return get_cyclebase_gene_info(ortho_evidences)

class CyclebaseOrthoGroups(xpage.OrthoGroups):
        def add_head(self):
                self.xtable.addhead("Name", "Organism", "Rank", "Peaktime","Phenotypes","Homology")

        def add_row(self, row, name, organism, homology, format):
                if format == "html":
                        if row.has_key("url") and row["url"] !="":
                                link = '<a class="silent_link" target = _blank href="%s">%%s</a>' % (row["url"])
                                self.xtable.addrow(link % name, link % organism,link % row["rank"], link % row["peak_time"],link % row["phenotypes"], link % homology)
                        else:
                                self.xtable.addrow(name,organism,row["rank"], row["peak_time"],row["phenotypes"], homology)
                elif format == "json":
                    	visible = "true"                    
			self.json.append('''"%s":{"name":"%s","organism":"%s", "Rank":%d, "Peaktime":%s, "Phenotypes": %s,"homology": %s, "visible":%s,"url":%s}'''% (row["id1"], name,organism,row["rank"],row["peak_time"], row["phenotypes"], homology, visible,row["url"]))

        def get_rows(self, rest, species, filter):
                ortho_evidences = xpage.OrthoGroups.get_rows(self, rest, species, filter)
                return get_cyclebase_gene_info(ortho_evidences)

class CyclebaseComplexes(xpage.KnowledgeIndirect):
	def create_table(self, rest, parent=None):
		dictionary = database.Connect("dictionary")
		format = "html"
		if "format" in rest:
			format = rest["format"]
		filter = False
		if format == "html":
			filter = True
			self.xtable = html.XDataTable(parent)
			self.xtable["width"] = "100%"
		elif format == "json":
			self.json = []
		limit = int(rest["limit"])
		page = int(rest["page"])
		count = 0
		rows = self.get_rows(rest, filter)
		table_rows = defaultdict(list)
		if len(rows):
			self.add_head()
			for r in rows:
				count += 1
				if count > page*limit:
					break
				if count > limit*(page-1):
					connection = html.xcase(database.preferred_name(int(rest["type2"]), r["id2"], dictionary))
					name = html.xcase(database.preferred_name(int(rest["type1"]), r["id1"], dictionary))
					table_rows[connection].append((r,name))
			for c in table_rows:
				span = len(table_rows[c])
				for r,name in table_rows[c]:
					self.add_row(r, c, name, format, span)
					span = 0
		else:
			html.XText(parent,"No evidences in this channel")
		return count
	
	def add_head(self):
		self.xtable.addhead("Complex", "Name", "Rank", "Peaktime","Phenotypes")
	
	def add_row(self, row, connection, name, format, span): 
		if format == "html":
			rank = row["rank"]
			peak = row["peak_time"]
			pheno = row["phenotypes"]
			if row.has_key("url") and row["url"] !="":
				link = '<a class="silent_link" target = _blank href="%s">%%s</a>' % (row["url"])
				name = link % name
				rank = link % rank
				peak = link % peak
				pheno = link % pheno
			if span > 0:
				c = (connection, {'rowspan': str(span)})
				self.xtable.addrow(c, name, rank, peak, pheno)
			else:
				self.xtable.addrow(name, rank, peak, pheno)
		elif format == "json":
		    visible = "true"
		    self.json.append('''"%s":{"connection":"%s", "name":"%s", "Rank":%d, "Peaktime":%s, "Phenotypes": %s,"visible":%s,"url":%s}'''% (row["id1"], name, row["rank"],row["peak_time"], row["phenotypes"], visible,row["url"]))
	
	def get_rows(self, rest, filter):
		complex_evidences = xpage.KnowledgeIndirect.get_rows(self,rest,filter)
		return get_cyclebase_gene_info(complex_evidences)

    
class CyclebasePage(mamba.task.Request):
    
    def get_section(self, section_type,qtype= None):
	maptype = {}
        maptype[-35]   = "PTMs"
        maptype[2759] = "Orthologs and Paralogs"
        maptype[4932] = {-28 : "Phenotypes"}
	maptype[4896] = {-29 : "Phenotypes"}
	maptype[9606] = {-30 : "Phenotypes"}
	maptype[3702] = {-28:"Phenotypes"} #temporarily until we have Arabidopsis Thaliana phenotypes
	
	if maptype.has_key(section_type):
		return maptype[section_type]
        elif maptype.has_key(qtype):
		if maptype[qtype].has_key(section_type):
			return maptype[qtype][section_type]
	else:
            return section_type
    
    def main(self):
	rest = mamba.task.RestDecoder(self)
	dictionary = database.Connect("dictionary")
	
	sections = mamba.setup.config().sections['COMBINED']
	groups = mamba.setup.config().sections['GROUPS']
	
	order = []
		
	qtype1 = int(rest["type"])
	qid1 = rest["id"]
	
	name1 = database.preferred_name(qtype1, qid1, dictionary)
	page = xpage.XPage("Cyclebase", name1)
	
	associations = None
	associations = html.XSection(page.content, html.xcase(""))
	
	if associations:
	    xpage.EntityHeader(associations.body, qtype1, qid1, dictionary)
	
	container_cycle = html.XDiv(associations.body,"ajax_cyclebase_cycle", "blackmamba_cyclebase_div")
	html.XScript(container_cycle, "blackmamba_cyclebase_cycle('id=%s&type=%s', '%s');" % (qid1, qtype1, "blackmamba_cyclebase_div"))
	container_timecourse = html.XDiv(associations.body,"ajax_cyclebase_timecourse", "blackmamba_cyclebase_timecourse_div")
	html.XScript(container_timecourse, "blackmamba_cyclebase_timecourse('id=%s&type=%s', '%s');" % (qid1, qtype1, "blackmamba_cyclebase_timecourse_div"))
	
	    
	for key in sections:
	    db_list = sections[key]
	    title = self.get_section(int(key),int(qtype1))
	    if title:
		xpage.XAjaxContainer(associations.body, "Combined", "title=%s&type1=%d&id1=%s&type2=%d&dbs=%s" % (title,qtype1, qid1, int(key),db_list), 10)
	
	#Complexes
	xpage.XAjaxContainer(associations.body, "CyclebaseComplexes", "title=Complexes&type1=%d&id1=%s&type2=-22&source=Cyclebase&db=knowledge" % (qtype1, qid1), 10)
	
	for key in groups:
	    db = groups[key]
	    title = self.get_section(int(key))
	    xpage.XAjaxContainer(associations.body, "CyclebaseOrthoGroups", "title=%s&type1=%d&id1=%s&key=%d&db=%s" % (title,qtype1, qid1, int(key),db), 10)
	
	
	
	mamba.http.HTMLResponse(self, page.tohtml()).send()

        
class SearchTable(html.XNode):
	
	def __init__(self, parent, dictionary, query, section, limit, page, container):
		html.XNode.__init__(self, parent)
		if len(query) < 2:
		    html.XP(self, "Query '%s' too short." % query)
		    return
		qtypes = mamba.setup.config().sections[section.upper()]
		entities = database.find_entities(map(int, qtypes.keys()), query, dictionary)
		cyb_db = database.Connect("cyclebase")
		vis_db = database.Connect("visualization")
		cycleinfo = cyb_db.query(get_cycleinfo(qtypes.keys())).dictresult()
		cycleinfo = simplify_dictionary(cycleinfo)
		if len(entities):
			html.XDiv(self, "table_title").text = "Search results"
			xpages = html.XDiv(self, "table_pages")
			xtable = html.XDataTable(self)
			xtable["width"] = "100%"
			xtable.addhead("Matched name", "Primary name", "Type", "Identifier","Peaktime","Phenotypes")
			seen = set()
			count = 0
			for qtype, qid, name in entities:
				if (qtype,qid) not in seen:
					seen.add((qtype,qid))
					if count >= limit*(page-1) and count < page*limit:
						preferred = database.preferred_name(qtype, qid, dictionary)
						type_name = database.preferred_type_name(qtype, dictionary)
						link = '<a class="silent_link" href="%s%s">%%s</a>' % (qtypes[str(qtype)], qid)
						results = cyb_db.query(get_combined_results(qid,qtype)).dictresult()
						figures = vis_db.query(get_icons(qid,qtype)).dictresult()
						
						peaktime = ""
						phase = ""
						phenos = ""
						if(len(results)>0):
							peaktime = results.pop()["peak_time"]
							phase = get_phase(cycleinfo,qtype,peaktime)
							if len(figures):
								phenotypes = {}
								for figure in figures:
									label = figure["label"]
									phenotypes[label.split('_')[0]] = 1
								phenos = ",".join(phenotypes.keys())
								phenos = phenos.replace("M","SM").replace("G2","SG2")
								phenos = sorted(phenos.split(","))
								phenos = ", ".join(phenos)
								phenos = phenos.replace("SM","M").replace("SG2","G2")
						xtable.addrow(link % html.xcase(name), link % html.xcase(preferred), link % type_name, link % qid,link % phase, link % phenos)
					count += 1
					if count > page*limit:
						break
			if count > limit:
				if page > 1:
					html.XText(html.XSpan(xpages, {"class":"silent_link","onclick":"blackmamba_search('CyclebaseQuery', '%s', %d, %d, '%s')" % (section, limit, page-1, container)}), "&lt;&nbsp;Prev")
				if count > page*limit:
					if page > 1:
						html.XText(xpages, "&nbsp;|&nbsp;")
					html.XText(html.XSpan(xpages, {"class":"silent_link","onclick":"blackmamba_search('CyclebaseQuery', '%s', %d, %d, '%s')" % (section, limit, page+1, container)}), "Next&nbsp;&gt;")
		else:
			html.XP(self, "Nothing found for '%s'" % query)


class CyclebaseQuery(mamba.task.Request):
	
	def main(self):
		rest = mamba.task.RestDecoder(self)
		query = ""
		if "query" in rest:
			query = rest["query"]
		section = ""
		if "section" in rest:
			section = rest["section"]
		limit = 20
		if "limit" in rest:
			limit = int(rest["limit"])
		page = 1
		if "page" in rest:
			page = int(rest["page"])
		container = rest["container"]
		mamba.http.HTMLResponse(self, SearchTable(None, database.Connect("dictionary"), query, section, limit, page, container).tohtml()).send()

class CyclebaseSearch(mamba.task.Request):
	
	def main(self):
		rest = mamba.task.RestDecoder(self)
		action = "CyclebaseQuery"
		if "action" in rest:
			action = rest["action"]
		limit = 20
		if "limit" in rest:
			imit = int(rest["limit"])
		query = ""
		if "query" in rest:
			query = rest["query"]
		mamba.http.HTMLResponse(self, search.SearchPage("SEARCH", "Search", action, limit, query).tohtml()).send()
		
class AdvancedTable(html.XNode):
	
	def __init__(self, parent, dictionary, search_id,organism, phase, phenotype,rank, section, limit, page, container):
		html.XNode.__init__(self, parent)
		
		if search_id == "" and organism == "" and phase == "" and rank == "" and phenotype == "":
			html.XP(self, "Query '%s' too short." % search_id)
			return
		
		qorganisms = {}
		qorganisms = mamba.setup.config().sections['SEARCH']
		if(organism != ""):
			qorganisms= {organism:qorganisms[organism]}
		
		cyb_database = database.Connect("cyclebase")
		cycle_info =  cyb_database.query(get_cycleinfo(qorganisms)).dictresult()
		cycle_info_dict = simplify_dictionary(cycle_info)
		vis_database = database.Connect("visualization")
		
		query = "SELECT rank,id, type,peak_time FROM combinedresults WHERE "
		phenotype_query = "SELECT id FROM colors WHERE type = TYPE AND label LIKE 'PHASE\\_phenotype%%' AND score >=2"
		qconditions = []
		results = []
		
		if(rank != ""):
			qrank = "rank <= %d" % (int(rank))
			qconditions.append(qrank)
		
		qids = ""
		if(search_id != ""):
			entities = database.find_entities(map(int, qorganisms.keys()), search_id, dictionary)
			if len(entities):
				types, ids,names = zip(*entities)
				qids = "id IN ('%s')" % "','".join(ids)
				qconditions.append(qids)
			else:
				qids = "id = '%s'" % search_id
				qconditions.append(qids)
		phenotype_results = []
		nothing_found = False
		if(phenotype !=""):
			for organism in qorganisms.keys():
				vis_query = phenotype_query.replace("TYPE",organism).replace("PHASE",phenotype)
				if qids != "":
					vis_query += " AND "+qids
				phenotype_results.extend(vis_database.query(vis_query).getresult())
			if qids !="":
				qconditions.pop()
			if len(phenotype_results):
				ids = zip(*phenotype_results)
				qids = "id IN %s" % ','.join(str(x) for x in ids)
				qids = qids.replace(",)",")")
				qconditions.append(qids)
			else:
				nothing_found = True		
		if not nothing_found:
			if(phase != ""):
				for organism in qorganisms.keys():
					start,end = get_peak_range(cycle_info_dict,int(organism),phase)
					transition = end + (end-start)/5
					qphase = " CAST(coalesce(peak_time, '-1') AS integer)>= %d AND CAST(coalesce(peak_time, '200') AS integer) <%d" %(start,transition)
					qconditions.append("type = %d  AND %s " % (int(organism),qphase))
					results.extend(cyb_database.query(query+" AND ".join(qconditions)).getresult())
					qconditions.pop()
			else:
				if len(qorganisms.keys()) > 1:
					qtypes = "type IN (%s)" % ",".join(qorganisms.keys())
				else:
					qtypes = "type = %d" % int(qorganisms.keys().pop())
				qconditions.append(qtypes)
				results.extend(cyb_database.query(query+" AND ".join(qconditions)).getresult())
		if len(results):
			html.XDiv(self, "table_title").text = "Search results"
			xpages = html.XDiv(self, "table_pages")
			xtable = html.XDataTable(self)
			xtable["width"] = "100%"
			xtable.addhead("Matched name", "Primary name", "Type", "Identifier","Peaktime","rank","Phenotypes")
			seen = set()
			count = 0
			
			sorted_results = sorted(results, key=lambda x:x[0])
			
			vis_db = database.Connect("visualization")
			
			for rank,qid, qtype,peak_time  in sorted_results:
				if (qtype,qid) not in seen:
					seen.add((qtype,qid))
					if count >= limit*(page-1) and count < page*limit:
							preferred = database.preferred_name(qtype, qid, dictionary)
							type_name = database.preferred_type_name(qtype, dictionary)
							link = '<a class="silent_link" href="%s%s">%%s</a>' % (qorganisms[str(qtype)], qid)
							phase = get_phase(cycle_info_dict,qtype,peak_time)
							figures = vis_db.query(get_icons(qid,qtype)).dictresult()
							
							if search_id != "":
								entities_dict = tuples_to_dict(entities)
								alias = entities_dict[qtype][qid]
							else:
								alias =preferred
							
							phenos = ""
							if len(figures):
								phenotypes = {}
								for figure in figures:
									label = figure["label"]
									phenotypes[label.split('_')[0]] = 1
								phenos = ",".join(phenotypes.keys())
								phenos = phenos.replace("M","SM").replace("G2","SG2")
								phenos = sorted(phenos.split(","))
								phenos = ", ".join(phenos)
								phenos = phenos.replace("SM","M").replace("SG2","G2")
								
							xtable.addrow(link % html.xcase(alias), link % html.xcase(preferred), link % type_name, link % qid,link % phase,link % rank, link % phenos)
					count += 1
					if count > page*limit:
						break
			if count > limit:
				if page > 1:
					html.XText(html.XSpan(xpages, {"class":"silent_link","onclick":"blackmamba_advanced_search('AdvancedCyclebaseQuery', '%s', %d, %d, '%s')" % (section, limit, page-1, container)}), "&lt;&nbsp;Prev")
				if count > page*limit:
					if page > 1:
						html.XText(xpages, "&nbsp;|&nbsp;")
					html.XText(html.XSpan(xpages, {"class":"silent_link","onclick":"blackmamba_advanced_search('AdvancedCyclebaseQuery', '%s', %d, %d, '%s')" % (section, limit, page+1, container)}), "Next&nbsp;&gt;")
		else:
			html.XP(self, "Nothing found for '%s'" % search_id)



class AdvancedCyclebaseQuery(mamba.task.Request):
	
	def main(self):
		rest = mamba.task.RestDecoder(self)
		qid = organism = phase = rank = phenotype = ""
		if("id" in rest):
			qid = rest["id"]
		if "type" in rest and "phase" in rest and "rank" and "phenotype" in rest :
			if(rest["type"] != "" or rest["phase"] != "" or rest["rank"] != "" or rest["phenotype"] !=""):
				organism = rest["type"]
				phase = rest["phase"]
				rank = rest["rank"]
				phenotype = rest["phenotype"]
		elif("type" in rest and rest["type"] != ""):
			organism = rest["type"]
		section = ""
		if "section" in rest:
			section = rest["section"]
		limit = 20
		if "limit" in rest:
			limit = int(rest["limit"])
		page = 1
		if "page" in rest:
			page = int(rest["page"])
		container = rest["container"]
		mamba.http.HTMLResponse(self, AdvancedTable(None, database.Connect("dictionary"), qid,organism, phase,phenotype,rank, section, limit, page, container).tohtml()).send()
		
class AdvancedSearchPage(xpage.XPage):
	
	def __init__(self, page_class, page_name, action, limit, qid,qtype, phase,phenotype, rank):
		xpage.XPage.__init__(self, page_class, page_name)
		md5 = hashlib.md5()
		md5.update(action)
		container = md5.hexdigest()
		design = xpage.get_design()
		dictionary = database.Connect("dictionary")
		searchfor = mamba.setup.config().sections['SEARCH']
		form = html.XTag(self.content, "form", {"name":"blackmamba_advanced_search_form"})
		form["action"] = "javascript:blackmamba_advanced_search('/%s/', '%s', %d, 1, '%s');" % (action, page_class, limit, container)
		html.XText(form,"Search for a gene using any of these parameters:")
		html.XDiv(form, "break")
		html.XText(form,"Gene name/symbol matching ")
		html.XTag(form, "input", {"type":"text", "name":"id", "value":qid, "class":"advanced_search.query"})
		html.XDiv(form, "spacer")
		html.XText(form,"from ")
		select_type = html.XSelect(form, {"type":"select", "name":"organisms", "value":qtype, "class":"advanced_search.organism"})
		html.XOption(select_type, text="any organism", value = "", attr = {})
		for s in searchfor:
			organism = html.xcase(database.preferred_type_name(int(s), dictionary).replace("protein",""))
			if qtype !="" and qtype == s:
				option = html.XOption(select_type, organism, value = s, attr = {"selected":"selected"})
			else:
				option = html.XOption(select_type, organism, value = s, attr = {})
		html.XDiv(form, "break")
		
		html.XText(form,"with maximum rank of ")
		html.XTag(form, "input", {"type":"text", "name":"rank", "value":rank, "class":"advanced_search.rank"})
		html.XText(form,",")
		html.XDiv(form, "spacer")
		
		html.XText(form,"peak expression in ")
		select_phase = html.XSelect(form, {"type":"select", "name":"phase", "value": phase, "class":"advanced_search.phase"})
		html.XOption(select_phase, text="any phase", value = "", attr = {})
				
		html.XText(form," and phenotype related to ")
		phenotype_phase = html.XSelect(form, {"type":"select", "name":"phenotype", "value": phenotype, "class":"advanced_search.phenotype"})
		html.XOption(phenotype_phase, text="any phase", value = "", attr = {})
		for phase in globPhases:
			select_phase.add_option(phase , phase)
			phenotype_phase.add_option(phase , phase)
		html.XDiv(form, "break")

		html.XTag(form, "input", {"type":"submit", "value":"search", "class":"search"})
		html.XDiv(self.content, "ajax_table", container)
		if (qid != "" and qtype != "" and phase != "" and rank != "" and phenotype !="") or qtype != "":
			html.XScript(self.content, "document.blackmamba_advanced_search_form.submit();")

class AdvancedSearch(mamba.task.Request):
	
	def main(self):
		rest = mamba.task.RestDecoder(self)
		action = "AdvancedCyclebaseQuery"
		if "action" in rest:
			action = rest["action"]
		limit = 20
		if "limit" in rest:
			limit = int(rest["limit"])
		qid = qtype = phase = rank = phenotype= ""
		if "id" in rest:
			qid = rest["id"]
		if "type" in rest:
			qtype = rest["type"]
		if "phase" in rest:
			phase = rest["phase"]
		if "rank" in rest:
			rank = rest["rank"]
		if "phenotype" in rest:
			phenotype = rest["phenotype"]
		mamba.http.HTMLResponse(self, AdvancedSearchPage("ADVANCEDSEARCH", "AdvancedSearch", action, limit, qid,qtype, phase, phenotype,rank).tohtml()).send()
