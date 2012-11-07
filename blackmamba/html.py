import mamba.util
import json
import base64

def xcase(name):
	tokens = name.split(" ")
	if tokens[0].lower() == tokens[0]:
		tokens[0] = tokens[0].capitalize()
	return " ".join(tokens)


class XNode:
	
	def __init__(self, parent, attr={}):
		self.parent = None
		if parent != None:
			parent.add(self)
		self.attr = {}
		for name in attr:
			self.attr[name] = attr[name]
		self.nodes = []
		self.text = ""

	def remove(self):
		if self.parent != None and isinstance(self.parent, XNode):
			i = 0
			for node in self.parent.nodes:
				if node == self:
					del self.parent.nodes[i]
				else:
					i += 1
		self.nodes = []
		self.parent = None
		
	def add(self, node):
		if node == self:
			raise Exception, "HTML node %s is a child of itself" % str(node)
		self.nodes.append(node)
		if node.parent != None and node.parent != self:
			raise Exception, "Cannot add node due to parent mismatch: %s has parent %s which is not %s." % (node, node.parent, self)
		node.parent = self
	
	def begin_html(self):
		return ""
	
	def end_html(self):
		return ""
	
	def __contains__(self, name):
		return name in self.attr
	
	def __delitem__(self, name):
		del self.attr[name]
	
	def __getitem__(self, name):
		return self.attr[name]
	
	def __iter__(self):
		return self.attr.__iter__()
	
	def __setitem__(self, name, value):
		self.attr[name] = value
		
	def tohtml(self):
		html = []
		temp = []
		txt = self.begin_html()
		if txt != None and txt != "":
			temp.append(txt)
		for node in self.nodes:
			temp.append(node)
		if self.text != None and self.text != "":
			temp.append(mamba.util.string_to_bytes(self.text))
		txt = self.end_html()
		if txt != None and txt != "":
			temp.append(txt)
		for node in temp:
			txt = None
			if isinstance(node, XNode):
				txt = node.tohtml()
			elif isinstance(node, str):
				txt = node
			elif isinstance(node, unicode):
				txt = node.encode("utf8")
			else:
				raise Exception, "%s has child node which is of unsuported: %s" % (type(self), type(node))
			if txt != None and txt != "":
				html.append(mamba.util.string_to_bytes(txt))
		if len(html):
			return "".join(html)#.rstrip()
		return None


class XTag(XNode):
	
	def __init__(self, parent, tag, attr={}):
		XNode.__init__(self, parent, attr)
		self.tag = tag
		
	def begin_html(self):
		att = [""]
		for name in self.attr:			
			try:
				value = self.attr[name].replace('"', '\\"')
			except AttributeError:
				print self, name, self.attr[name]
			att.append("%s=\"%s\"" % (name, value))
		if len(att):
			att = " ".join(att)
		else:
			att = ""
		return "<%s%s>" % (self.tag, att)
		
	def end_html(self):
		return "</%s>" % self.tag


class XOuterTag(XTag):
	
	def begin_html(self):
		if len(self.nodes):
			return XTag.begin_html(self)
		return None
	
	def end_html(self):
		if len(self.nodes):
			return XTag.end_html(self)
		return None


class XText(XNode):
	
	def __init__(self, parent, text):
		XNode.__init__(self, parent)
		self.free = text
		
	def begin_html(self):
		return self.free


class XLink(XTag):
	
	def __init__(self, parent, href, text=None, target=None, attr={}):
		XTag.__init__(self, parent, "a", attr)
		self["href"] = href
		if target:
			self["target"] = target
		self.text = text


class XHr(XTag):
	
	def __init__(self, parent):
		XTag.__init__(self, parent, "hr")


class XP(XTag):
	
	def __init__(self, parent, text=None, attr={}):
		XTag.__init__(self, parent, "p", attr)
		if text != None:
			# issubclass changed to isinstance - Jan
			# if issubclass(type(text), basestring):
			if isinstance(text, basestring):
				self.text = text
			else:
				self.nodes.append(text)
				text.parent = self


class XDiv(XTag):
	
	def __init__(self, parent, div_class=None, div_id=None):
		XTag.__init__(self, parent, "div")
		if div_class:
			self["class"] = div_class
		if div_id:
			self["id"] = div_id


class XSpan(XTag):
	
	def __init__(self, parent, attr={}):
		XTag.__init__(self, parent, "span", attr)


class XScript(XTag):
	
	def __init__(self, parent, script):
		XTag.__init__(self, parent, "script")
		self.text = script


class XImg(XTag):
	def __init__(self, parent, source):
		XTag.__init__(self, parent, "img", {"src": source})


class XH1(XTag):
	
	def __init__(self, parent, heading=None):
		XTag.__init__(self, parent, "h1")
		if heading:
			self.text = heading


class XH2(XTag):
	
	def __init__(self,parent, heading=None):
		XTag.__init__(self, parent, "h2")
		if heading:
			self.text = heading


class XH3(XTag):
	
	def __init__(self, parent, heading=None):
		XTag.__init__(self, parent, "h3")
		if heading:
			self.text = heading


class XH4(XTag):
	
	def __init__(self, parent, heading=None):
		XTag.__init__(self, parent, "h4")
		if heading:
			self.text = heading


class XTd(XTag):
	
	def __init__(self, parent, attr={}):
		XTag.__init__(self, parent, "td", attr)


class XTh(XTd):
	
	def __init__(self, parent, attr={}):
		XTag.__init__(self, parent, "th", attr)


class XTr(XTag):
	
	def __init__(self, parent, attr={}):
		if isinstance(parent, XTable):
			parent = parent.tbody
		XTag.__init__(self, parent, "tr", attr)
		
	def add_data(self, *args):
		for item in args:
			XTd(self).text = str(item)


class XTable(XTag):
	
	def __init__(self, parent, attr={}):
		XTag.__init__(self, parent, "table", attr)
		self.thead   = XOuterTag(self, "thead")
		self.tfoot   = XOuterTag(self, "tfoot")
		self.tbody   = XOuterTag(self, "tbody")
		
	# changed isinstance to is subclass - Jan
	def addhead(self, *args):
		row = XTr(self.thead)
		for arg in args:
			if isinstance(arg, XTd):
				row.add(arg)
			elif isinstance(arg, XNode):
				XTh(row).add(arg)
			else:
				XTh(row).text = str(arg)
		for th in row.nodes:
			th["class"] = th.text.lower()
		return row
	
	# changed isinstance to is subclass - Jan
	def addrow(self, *args):
		row = XTr(self.tbody)
		if len(self.tbody.nodes) % 2 == 0:
			row["class"] = "even"
		else:
			row["class"] = "odd"
		for arg in args:
			if isinstance(arg, XTd):
				row.add(arg)
			elif isinstance(arg, XNode):
				XTd(row).add(arg)
			else:
				XTd(row).text = str(arg)
		if len(row.nodes) == len(self.thead.nodes[0].nodes):
			for i in range(len(self.thead.nodes[0].nodes)):
				row.nodes[i]["class"] = self.thead.nodes[0].nodes[i].text.lower()
		return row


class XDataTable(XTable):
	
	def __init__(self, parent):
		XTable.__init__(self, parent)
		self["class"] = "data"
		self["cellpadding"] = "2"
		self["cellspacing"] = "0"


class XHead(XTag):
	
	def __init__(self, parent):
		XTag.__init__(self, parent, "head")
		self.title = ""
		self.css = []
		self.scripts = []
		self.scripts.append("https://ajax.googleapis.com/ajax/libs/jquery/1.7.1/jquery.min.js")
		self.scripts.append("/scripts/blackmamba.js")
		self.scripts.append("/scripts/base64.js")
		
	def begin_html(self):
		html = []
		html.append("<head>")
		if self.title:
			html.append("  <title>%s</title>" % self.title)
		html.append("""  <meta http-equiv="Content-Type" content="text/html; charset=utf-8"></meta>""")
		html.append("""  <meta http-equiv="X-UA-Compatible" content="IE=9"></meta>""")
		for style in self.css:
			html.append("""  <link rel="stylesheet" href="%s" type="text/css"></link>""" % style)
		for java in self.scripts:
			html.append("""  <script type="text/javascript" src="%s"></script>""" % java)
		return "\r\n".join(html)


class XBody(XTag):
	
	def __init__(self, page):
		XTag.__init__(self, page, "body")


class XGroup(XDiv):
	
	def __init__(self, parent, title):
		XDiv.__init__(self, parent, "group")
		self.header = XDiv(self, "group_header")
		XH3(self.header, title)
		self.body = XDiv(self, "group_body")


class XSection(XDiv):
	
	def __init__(self, parent, title, text=None):
		XDiv.__init__(self, parent, "section")
		self.header = XDiv(self, "section_header")
		XH4(self.header, title)
		self.body = XDiv(self, "section_body")
		if text != None:
			if type(text) is str:
				self.body.text = text
			else:
				self.body.add(text)


class XNakedPage(XTag):
	
	def __init__(self, title):
		XTag.__init__(self, None, "html")
		self.head = XHead(self)
		self.head.title = title
		self.body = XBody(self)
		self.header = XDiv(self.body, "header")
		self.content = XDiv(self.body, "content")
		self.footer = XDiv(self.body, "footer")
		
class XBr(XTag):

	def __init__(self, parent):
		XTag.__init__(self, parent, "br")
		
	def end_html(self):
		return ""

class XForm(XTag):
	
	def __init__(self, parent, attr = {}):
		self.data_store = {}
		XTag.__init__(self, parent, "form", attr)		
	
	def end_html(self):		
		html = ""
		if len(self.data_store):
			mamba_data_store = base64.urlsafe_b64encode(json.dumps(self.data_store))
			html = "<input type=\"hidden\" name=\"mamba_data_store\" id=\"mamba_data_store\" value=\"%s\" />" % mamba_data_store
			
		html = html + "</%s>" % self.tag
		return html
		
		
class XInput(XTag):

	def __init__(self, parent, attr = {}):
		XTag.__init__(self, parent, "input", attr)


class XTextArea(XTag):
	
	def __init__(self, parent, attr = {}):
		XTag.__init__(self, parent, "textarea", attr)


class XSelect(XTag):

	def __init__(self, parent, attr = {}):
		XTag.__init__(self, parent, "select", attr)
	
	def add_option(self, text, value = None):
		XOption(self, text, value)

	
class XOption(XTag):

	def __init__(self, parent, text, value = None, attr = {}):
		XTag.__init__(self, parent, "option", attr)
		self.text = text
		if value:
			self['value'] = value

	

