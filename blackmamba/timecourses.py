import pg
import urllib
import re

import database

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
        
        json = ["{\"sources\":["]
        time_course = {}
        for dbregistry in measurements:
            source = dbregistry["source"]
            y_values_str = dbregistry["y_values"]
            y_values_str = y_values_str.replace("{","")
            y_values_str = y_values_str.replace("}","")
            y_values_str = y_values_str.replace("NA","null")
            y_values = y_values_str.split(",")
            time_course[source] = {"y_values": y_values}
            
        for dbregistry in metadata:
            source = dbregistry["source"]
            link = dbregistry["pmid"] if dbregistry["pmid"] is not None else ""
            if(time_course.has_key(source)):
                x_values_str = dbregistry["x_values"]
                x_values_str = x_values_str.replace("{","")
                x_values_str = x_values_str.replace("}","")
                x_values = x_values_str.split(",")
                time_course[source].update({"x_values": x_values, "link":link})
            
        for source in time_course:
            json.append("{\"name\":\""+source+"\",\"link\":\""+time_course[source]["link"]+"\",\"values\":[")
            for i in range(0,len(time_course[source]["x_values"])):
                json.append("["+time_course[source]["x_values"][i]+",")
                json.append(time_course[source]["y_values"][i]+"]")
                json.append(",")
            json = json[:-1]
            json.append("]}")
            json.append(",")
        json = json[:-1]
        json.append("]}")
        
        mamba.http.HTTPResponse(self,"".join(json), "application/json").send()
