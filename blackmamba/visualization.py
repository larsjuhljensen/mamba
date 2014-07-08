import pg
import re
import database
import html
import mamba.task

class SVG(html.XNode):
	__svg = ''
	
	def __init__(self, parent, qfigure, qtype, qid, qpaint = False, visualization = None):
		html.XNode.__init__(self, parent)
		svg = None
		if visualization == None:
			visualization = database.Connect("visualization")
		if qtype == None and qid == None:
			q = "SELECT svg FROM figures where figure = '%s';" % pg.escape_string(qfigure)
			svg = visualization.query(q).getresult()[0][0]
		else:
			q = "SELECT DISTINCT figure FROM colors WHERE type = %d AND id = '%s' AND figure LIKE '%s';" % (qtype, pg.escape_string(qid), pg.escape_string(qfigure))
			figures = visualization.query(q).getresult()
			if len(figures):
				figure = figures[0][0]
			else:
				figure = qfigure
			q = "SELECT svg, paint FROM figures WHERE figure = '%s';" % pg.escape_string(figure)
			figures = visualization.query(q).getresult()
			if len(figures) == 1:
				svg, paint = figures[0]
				if qpaint or paint == "t":
					q = "SELECT label, color FROM colors WHERE type = %d AND id = '%s' AND figure LIKE '%s';" % (qtype, pg.escape_string(qid), pg.escape_string(figure))
					label_color_map = {}
					for r in visualization.query(q).getresult():
						label_color_map[r[0]] = r[1]
					lines = []
					for line in svg.split("\n"):
						m = re.search('<.* title="([^"]+)".*>', line)
						if m:
							label = m.group(1)
							if label in label_color_map:
								line = re.sub('(?<=fill:|ill=")#.{6}', '%s' % label_color_map[label], line)
						lines.append(line)
					svg = "\n".join(lines)
			else:
				svg = '''<svg x="0px" y="0px" width="0px" height="0px" />'''
		# get rid of XML comments and XML header, and whitespace on the beginning of the document
		svg = re.sub("<\?xml.*?\?>\n?", '', svg)		
		svg = re.sub("<!--.*?-->\n?", '', svg)
		svg = re.sub("$\s*", '', svg)
		if not re.match("<svg", svg):
			raise Exception, "You tried to embed wrong type of SVG to the XSVG node"
		self.__svg = svg
		
	def begin_html(self):
		return self.__svg

class Visualization(mamba.task.Request):
	
	def main(self):
		rest = mamba.task.RestDecoder(self)
		
		qfigure = rest["figure"]
		qtype = None
		if "type" in rest:
			qtype = int(rest["type"])
		qid = None
		if "id" in rest:
			qid = rest["id"].encode("utf8")
		qpaint = False
		if "paint" in rest:
			qpaint = True
		
		xsvg = SVG(None, qfigure, qtype, qid, qpaint)
		mamba.http.HTTPResponse(self, xsvg.tohtml(), "image/svg+xml").send()

class VisualizationJSON(mamba.task.Request):

	def main(self):
		rest = mamba.task.RestDecoder(self)

		qfigure = rest["figure"]
		qtype = int(rest["type"])
		qid = rest["id"].encode("utf8")
		
		visualization = database.Connect("visualization")
		q = "SELECT label, score FROM colors WHERE type = %d AND id = '%s' AND figure LIKE '%s';" % (qtype, pg.escape_string(qid), pg.escape_string(qfigure))

		order = {
			"knowledge" : 1,
			"experiments" : 2,
			"HPM" : 2.1,
			"HPA-IHC" : 2.2,
			"HPA-RNA" : 2.3,
			"RNA-seq" : 2.4,
			"Exon array" : 2.5,
			"GNF" : 2.6,
			"UniGene" : 2.7,
			"textmining" : 3,
			"predictions" : 4,
			"PSORT" : 4.1,
			"YLoc" : 4.2
		}
		json = []
		for r in sorted(visualization.query(q).getresult(), key=lambda x: order.get(x[0].split(":")[0], 5)):
			json.append('''"%s":%d''' % (r[0], r[1]))
		mamba.http.HTTPResponse(self, "{"+",".join(json)+"}\n", "application/json").send()
