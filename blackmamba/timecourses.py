import pg
import urllib
import re

import database
import json
import mamba.setup
import mamba.task

class TimeCourses(mamba.task.Request):
    
    def main(self):
        rest = mamba.task.RestDecoder(self)
        id = None
        if "id" in rest:
            id = rest["id"]
            id_sql = "id = '%s'" %(id)
        ids = None
        if "ids" in rest:
            ids = rest["ids"]
            id_sql = "id IN ('%s)'" %(ids)
            
        sources = rest["sources"].split(",")
        
        formated_sources = []
        for source in sources:
            formated_sources.append("\'"+source+"\'")
        
	sources_sql = "source IN (%s)" % (",".join(formated_sources))
        
        timecourses = database.Connect("timecourses")
        measurements = timecourses.query("SELECT source,y_values FROM measurements WHERE %s AND %s;"%(id_sql,sources_sql)).dictresult()
        metadata = timecourses.query("SELECT source,pmid,x_values FROM metadata WHERE %s;"%(sources_sql)).dictresult()
        
        jsondict = {'sources' : []}
        time_course = {}
        for dbregistry in measurements:
            source = dbregistry["source"]
            y_values = dbregistry["y_values"]
            if isinstance(y_values, basestring):
                y_values = y_values.replace("{","").replace("}","").split(",")
            time_course[source] = {"y_values": map(float, y_values)}
            
        for dbregistry in metadata:
            source = dbregistry["source"]
            link = dbregistry["pmid"] if dbregistry["pmid"] is not None else ""
            if(time_course.has_key(source)):
                x_values = dbregistry["x_values"]
                if isinstance(x_values, basestring):
                    x_values = x_values.replace("{","").replace("}","").split(",")
                time_course[source].update({"x_values": map(float, x_values), "link":link})
        
        for source in time_course:
	    sourceRegistry = {'name': source, 'link' : time_course[source]["link"], 'values' : []}
            for i in range(0,len(time_course[source]["x_values"])):
		sourceRegistry['values'].append([time_course[source]["x_values"][i], time_course[source]["y_values"][i]])
	    jsondict['sources'].append(sourceRegistry)

        mamba.http.HTTPResponse(self,json.dumps(jsondict), "application/json").send()
