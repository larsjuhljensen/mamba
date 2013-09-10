import pg
import re
import database
import html
import mamba.task

def svg(qfigure, qtype, qid, visualization = None):
	if visualization == None:
		visualization = database.Connect("visualization")
	if qtype == None and qid == None:
		q = "SELECT svg FROM figures where figure = '%s';" % pg.escape_string(qfigure)
		return visualization.query(q).getresult()[0][0]
	q = "SELECT DISTINCT figure FROM colors WHERE type = %d AND id = '%s' AND figure LIKE '%s';" % (qtype, pg.escape_string(qid), pg.escape_string(qfigure))
	figure = visualization.query(q).getresult()[0][0]
	q = "SELECT label, color FROM colors WHERE type = %d AND id = '%s' AND figure LIKE '%s';" % (qtype, pg.escape_string(qid), pg.escape_string(figure))
	label_color_map = {}
	for r in visualization.query(q).getresult():
		label_color_map[r[0]] = r[1]
	svg = []
	q = "SELECT svg FROM figures WHERE figure = '%s';" % pg.escape_string(figure)
	for line in visualization.query(q).getresult()[0][0].split("\n"):
		m = re.search('<.* title="([^"]+)".*>', line)
		if m:
			label = m.group(1)
			if label in label_color_map:
				line = re.sub('(?<=fill:|ill=")#.{6}', '%s' % label_color_map[label], line)
		svg.append(line)
	return "\n".join(svg)
	
class SVG(html.XNode):
	__svg = ''
	
	def __init__(self, parent, svg):
		html.XNode.__init__(self, parent)
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
		
		xsvg = SVG(None, svg(qfigure, qtype, qid))
		mamba.http.HTTPResponse(self, xsvg.tohtml()).send()

class VisualizationJSON(mamba.task.Request):

	def main(self):
		rest = mamba.task.RestDecoder(self)

		qfigure = rest["figure"]
		qtype = int(rest["type"])
		qid = rest["id"].encode("utf8")
		
		visualization = database.Connect("visualization")
		q = "SELECT label, color FROM colors WHERE type = %d AND id = '%s' AND figure LIKE '%s';" % (qtype, pg.escape_string(qid), pg.escape_string(qfigure))
		json = []
		for r in visualization.query(q).getresult():
			json.append('''"%s":"%s"''' % (r[0], r[1]))
		mamba.http.HTTPResponse(self, "{"+",".join(json)+"}\n", "application/json").send()

class AjaxSVG(html.XDiv):
	
	def __init__(self, parent, container, qfigure, qtype, qid):
		html.XDiv.__init__(self, parent, None, "blackmamba_%s_div" % container)
		html.XScript(self, 'blackmamba_visualization("/Visualization", "%s", "%s", %d, "%s");' % (container, qfigure, qtype, qid))
