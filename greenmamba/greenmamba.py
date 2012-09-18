##############################################################################
# Copyright (c) 2011, Lars Juhl Jensen, Heiko Horn, and Sune Frankild
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#  - Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#  - Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#  - Neither the name of the Novo Nordisk Foundation Center for Protein
#    Research, University of Copenhagen nor the names of its contributors may
#    be used to endorse or promote products derived from this software without
#    specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
# THE POSSIBILITY OF SUCH DAMAGE.
##############################################################################

import base64
import os
import re
import tempfile
import mamba.setup
import mamba.task
import mamba.http

web_img_hide = '''data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAN1QAADdUBPdZY8QAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAMJSURBVDiNbZNNTFxVGIafc+6dc4dZ3DCSFDthamqmBMpUCC3GmBhcWSu0C9O6USIQNiTsam3ShBWJwUUNhm0X/iRG3RNY1ZguLLSyoJPgoiX8KLQDdLyQDveee+49bpDY1i95d9/35ls8j7DW8t8RQrQppQY9z+sNw7AM4HleJQzDX40x31hr/3hu/98CIYRUSl13HOdGf39f7uTJ12WxWMTEMY9WVlhZeZTevv1L3RjzhTHmS2ttelQghJANDQ13Wltby6Ojo34+n8daizExWmt0FBFFEbu7O/z40897q6trFa31O9baVB6+eLVUKpWvXfvMb2lpobu7m7a2NnZ2dtnZ2UU6DlJKfN/n04EB/7UTJ8qu614FkEKIkpRyfHh42MeCEAKlFNVqlYmJCSYnJ9muboMQgAABly72+a7jjAshSo7rup+fP//eu+WOshBSYoxhaWmJsbExarUaYRiyuLhIR0cHnlIYY5BCkBiT+WtzM5TZbLa32FKUxsTEsWZjY4Px8XFqtRojIyMMDw0RBAHT09Nsb1dJ05Q0tRwvFKRSmV7HWjvV98EF5bou29UqN29+RRAEDA0N0nPuLM3Nx3gln+f+/d958KDCqVKJTMYl63n8dnehUWItWmu2traYmvqaIAgY+ORjujo7CcMQHUW8ceYMly9/yP7+Pt9+9z1Pn9aOOJAZpSrr62sEfwdorfnoyhXK5Q7C8IAoComiiEhHnG5v59LFfnQcE4YHPH5SRalMxbHWnvJ9/+3T7W2i59xZCoUCiUkwicEYQ2xiTBwTxzFNTU10dXWSb2xkeXk5XV1b/0EaY27Nzy88C4IAgDA8OExIdBitNWmaApD1POr1OvML954ZY25Ja+1DkyQTM7NzewBpmpIkCYkxJEnCi64AzMzO7ZkkmbDWPjxCWSl1p1hsKfddeN/P5XIvHQHU63VmZuf2Njb+PEL5OZlc173uOM6Nt97syR0vFOSrzccAePykytbmZnp34V49SZKXZXpRZ9d1B5XK9GodlwGUylS0jv9X538Ab42nw0zf4FoAAAAASUVORK5CYII='''
web_img_show = '''data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAN1QAADdUBPdZY8QAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAL7SURBVDiNbVNNTFxVGD3fvXfeDLN4MiFTfjozpGYYyfBGEloaN1hXFhnARGNdNTZsGtYtNmnsSmNiXLFiQwrd+RNd+BNd1SALiSaMQ3BwAWSm0GnHOE5C4PHevfe960IkjPYk3+6c853FOWSMwVkQ0aBlWTei0egVz/McAIhGo5ue561orZeNMb+38f81ICJmWdYdzvndycli/MKF51k6nYZWCju7u9jd3QkfPvzB1Vp/qLX+yBgTnhoQEevo6FjN5XLO7OysnUgkYIyB1gpSSkjfh+/7aDb/xCeffnZQrdY2pZRjxpiQnUS8lc1mnbm523YqlcLIyAgGBwchRAScCzDOwRiDbdt45/p1uz+TcYQQtwCAEVGWMXZvZmbGhgGICJZlIRaLgYhABBAIIAJAAAHTU0VbcH6PiLJcCPHu1auvvuIMOfTT2hqSySSazSYajQaUUtBan5yC7/tYX19HX28vAq0jj+t1j8fj8fdfHhtL12o1LC4uolqtYnh4GEFwIlQKSiv4noflBw+w8uMqurq60JlI0PbOtmC+7zs9Pd0YGspjdPQSSqUS5ufncXh4COl7kNKHd3yMpaVlVCpbKBQcvJAbQE/3OUipHAZjIKWE1hpvX7uGSxcvolwuY2FhAUdHRzh2Xdy/v4TfKhW8WChgqjjR1hsei8Wmz5/vTXU+1wkDg3w+j9ZfLZTLG9jb30Op9CsqW1v/iCcnEIYhAGD/cR3bO9vrQkq5Uqs9utyfyTCuORjjeH16CkEQoLyxAQAoOA6KE+MIguD085N6PZRSrfAwDKuNp40ZZygfJSIEQYAwDDCQG0Cr1UIymURxYrwttuu6+Orrbw6lUjfJGINIJDLX3595760337DPEs/UvM3g8y++PKjVHn2glPr4tMqWZa2m0ymn+Nq4HY/H8Sy4rotvv/v+YG9v/7TKbWMSQtzhnN996fJovLevj/V0nwMAPG38gSf1erj28y9uEAT/H9N/5yyEuGFZkStSKgcALCuyKaV65pz/BrHqfIUFBe1lAAAAAElFTkSuQmCC'''

web_script = '''
<script type='text/javascript'>
var hide = "%s";
var show = "%s";

function switchView(id, me)
{
  if (document.getElementById(id).className == "hide") {
    document.getElementById(id).className = "";
    me.src = hide;
  }
  else {
    document.getElementById(id).className = "hide";
    me.src = show;
  }
}

var active_index = 0;

function showForm(index)
{
  if (index != active_index) {
    document.getElementById(active_index+"_tab").className = "tab_inactive";
    document.getElementById(active_index+"_div").className = "div_inactive";
    document.getElementById(index+"_tab").className = "tab_active";
    document.getElementById(index+"_div").className = "div_active";
    active_index = index;
  }
}

</script>
''' % (web_img_hide, web_img_show)

web_style = '''
<style>

body{
  font-family: helvetica;
  margin: 0;
}

a{
  color: black;
  text-decoration: none;
}

input[type=text], textarea {
  font-family: monospace;
  font-size: 100%;
}

td{
  vertical-align: top;
}

.hide{
  display: none;
}

.pages{
  border-color: $color;
  border-style: solid;
  border-width: 0 0.2em 0.2em 0.2em;
  border-bottom-left-radius: 0.4em;
  border-bottom-right-radius: 0.4em;
  -khtml-border-bottom-left-radius: 0.4em;
  -khtml-border-bottom-right-radius: 0.4em;
  -moz-border-bottom-left-radius: 0.4em;
  -moz-border-bottom-right-radius: 0.4em;
  -webkit-border-bottom-left-radius: 0.4em;
  -webkit-border-bottom-right-radius: 0.4em;
  float: right;
}

.pages td{
  padding: 0em 0.5em;
}

.space{
  padding: 0.2em;
}

.tab_active{
  background-color: #EEEEEE;
  border-color: $color;
  border-style: solid;
  border-width: 0.2em 0 0.2em 0.2em;
  border-bottom-left-radius: 0.8em;
  border-top-left-radius: 0.8em;
  -khtml-border-bottom-left-radius: 0.8em;
  -khtml-border-top-left-radius: 0.8em;
  -moz-border-bottom-left-radius: 0.8em;
  -moz-border-top-left-radius: 0.8em;
  -webkit-border-bottom-left-radius: 0.8em;
  -webkit-border-top-left-radius: 0.8em;
  cursor: pointer;
  cursor: hand;
  padding: 0.4em;
}

.tab_inactive{
  border-color: $color;
  border-style: solid;
  border-width: 0.2em 0 0.2em 0.2em;
  border-bottom-left-radius: 0.8em;
  border-top-left-radius: 0.8em;
  -khtml-border-bottom-left-radius: 0.8em;
  -khtml-border-top-left-radius: 0.8em;
  -moz-border-bottom-left-radius: 0.8em;
  -moz-border-top-left-radius: 0.8em;
  -webkit-border-bottom-left-radius: 0.8em;
  -webkit-border-top-left-radius: 0.8em;
  color: #777777;
  cursor: pointer;
  cursor: hand;
  padding: 0.4em;
}

.div_inactive{
  display: none;
}

.wrapper{
  border-color: $color;
  border-style: solid;
  border-width: 0.2em;
  border-bottom-left-radius: 0.4em;
  border-bottom-right-radius: 0.4em;
  border-top-left-radius: 0.4em;
  border-top-right-radius: 0.4em;
  -khtml-border-bottom-left-radius: 0.4em;
  -khtml-border-bottom-right-radius: 0.4em;
  -khtml-border-top-left-radius: 0.4em;
  -khtml-border-top-right-radius: 0.4em;
  -moz-border-bottom-left-radius: 0.4em;
  -moz-border-bottom-right-radius: 0.4em;
  -moz-border-top-left-radius: 0.4em;
  -moz-border-top-right-radius: 0.4em;
  -webkit-border-bottom-left-radius: 0.4em;
  -webkit-border-bottom-right-radius: 0.4em;
  -webkit-border-top-left-radius: 0.4em;
  -webkit-border-top-right-radius: 0.4em;
  margin: 1em 0;
}

.wrapper th{
  border-style: double;
  border-width: 0 0 0.2em 0;
  margin: 0 0 1em 0;
  padding: 0.2em;
}

.wrapper th img{
  float: right;
  height: 1em;
  width: 1em;
  cursor: pointer;
  cursor: hand;
}

.wrapper table{
  font-family: monospace;
}

.wrapper td{
  min-width: 35em;
  padding: 0em 0.5em;
  width: $width;
}

.wrapper th{
  min-width: 0;
  text-align: left;
  width: auto;
}

.input td{
  font-family: helvetica;
  min-width: 0;
  text-align: left;
  width: auto;
}

.output td{
  min-width: 0;
  text-align: left;
  width: auto;
}

.output td.odd{
  background-color: #DDDDDD;
}

#title1{
  background-color: $color;
  background-image: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAABNCAYAAABuZK7kAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAN1wAADdcBQiibeAAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAA4SURBVDiNY/z//z8DOmDCEBkVHBUcgYIsDAwMjNgE2bAJshMtOPy0D0InjWqnsXbG/////0UXBAAjBgjTd7yRZAAAAABJRU5ErkJggg%3D%3D);
  background-position: bottom;
  background-repeat: repeat-x;
  background-size: 5px 77px;
  float: left;
  font-size: 2em;
  padding: 0.25em 0 1em 0.5em;
}

#title2{
  background-color: $color;
  background-image: url(data:image/png;base64,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%3D);
  background-position: right bottom;
  background-size: 99px 77px;
  float: left;
  font-size: 2em;
  padding: 0.25em 0 1em 0;
  width: 3em;
}

#title1 a{
  color: #EEEEEE;
  text-decoration: none;
}

#left{
  padding: 2em 0 0 1em;
}

#content{
  background-color: #EEEEEE;
  padding: 0.5em 0em;
}

#content a{
  color: $color;
  text-decoration: underline;
}

#footer a{
  color: $color;
  text-decoration: underline;
}

#footer{
  float: left;
  font-size: 0.8em;
  margin: 0;
  padding: 0 0.5em;
  width: $width;
}

</style>
'''


def eq(a, b):
	try:
		return float(a) == float(b)
	except:
		return str(a) == str(b)

def ne(a, b):
	return not eq(a, b)

def lt(a, b):
	try:
		return float(a) < float(b)
	except:
		return str(a) < str(b)

def gt(a, b):
	try:
		return float(a) > float(b)
	except:
		return str(a) > str(b)

def le(a, b):
	return not gt(a, b)

def ge(a, b):
	return not lt(a, b)

def like(a, b):
	return re.match(b.replace("%", ".*"), a) != None

def ilike(a, b):
	return re.match(b.replace("%", ".*"), a, re.I) != None

def compare(a, b, operator):
	if operator == "eq":
		return eq(a, b)
	elif operator == "ne":
		return ne(a, b)
	elif operator == "lt":
		return lt(a, b)
	elif operator == "gt":
		return gt(a, b)
	elif operator == "le":
		return le(a, b)
	elif operator == "ge":
		return ge(a, b)
	elif operator == "like":
		return like(a, b)
	elif operator == "ilike":
		return ilike(a, b)

class Setup(mamba.setup.Configuration):
	
	def __init__(self, inifile):
		mamba.setup.Configuration.__init__(self, inifile)
		self.tools = {}
		for section in self.sections:
			self.tools[section.upper()] = section


class REST(mamba.task.Request):
	
	def activate(self, tool = None):
		
		if tool == None:
			tool = self.tool
		
		# Check if command is defined in ini file.
		if "command" in mamba.setup.config().sections[tool]:
			return self.run(mamba.setup.config().sections[tool]["command"]+" ", tool)
		
		# Check if database is defined in ini file.
		if "database" in mamba.setup.config().sections[tool]:
			return self.query(mamba.setup.config().sections[tool]["database"], tool)
		
		# Check if (sub)tools are defined ini file.
		if "tools" in mamba.setup.config().sections[tool]:
			outputs = []
			for subtool in mamba.setup.config().sections[tool]["tools"].split(";"):
				subtool = subtool.strip()
				if subtool:
					outputs += self.activate(subtool)
			return outputs
		
		mamba.http.HTTPErrorResponse(self, 500, "Tool '%s' wrongly configured" % tool).send()
		
	def fix_fasta(self, data):
		data = data.replace("\r\n", "\n").replace("\r", "\n")
		if not data.startswith(">"):
			data = ">Sequence\n"+data
		if not data.endswith("\n"):
			data = data+"\n"
		return data
	
	def format(self, names, outputs, tool, format):
		return outputs
		
	def parse(self):
		self.tool = self.http.get_action()
		self.rest = mamba.task.RestDecoder(self)
		if not self.tool.upper() in mamba.setup.config().tools:
			mamba.http.HTTPErrorResponse(self, 400, "Unknown tool %s" % self.tool).send()
			return False
		self.tool = mamba.setup.config().tools[self.tool.upper()]
		return True
	
	def query(self, database, tool):
		
		outputs = []
		
		file = open(database, "r")
		line = file.readline()
		labels = []
		names = []
		for label in line.split("\t"):
			label = label.strip()
			labels.append(label)
			name = label.replace(" ", "_")
			names.append(name)
		outputs.append("\t".join(labels)+"\n")
		conditions = []
		for key in self.rest:
			if key.startswith("value_"):
				value = self.rest[key]
				if value != "":
					name = key[6:]
					operator = self.rest["operator_"+name]
					column = names.index(name)
					condition = (column, operator, value)
					conditions.append(condition)
		line = file.readline()
		while line:
			values = line.split("\t")
			good = True
			for condition in conditions:
				if not compare(values[condition[0]], condition[2], condition[1]):
					good = False
					break
			if good:
				outputs.append(line)
			line = file.readline()
		file.close()
		
		return self.format(["Database records matching query"], ["".join(outputs)], tool, "tsv")
	
	def run(self, command, tool):
		
		# Retrieve name(s) for FASTA input file(s), for which input should be checked and corrected.
		fasta = []
		if "fasta" in mamba.setup.config().sections[tool]:
			fasta = fasta + mamba.setup.config().sections[tool]["fasta"].split(" ")
		
		format = None
		if "format" in mamba.setup.config().sections[tool]:
			format = mamba.setup.config().sections[tool]["format"]
		
		# Retrieve name for output file (stdout will be used if none is specified).
		output = None
		if "output" in mamba.setup.config().sections[tool]:
			output = mamba.setup.config().sections[tool]["output"]
		
		# Retrieve name for input file to be split into records.
		split = None
		if "split" in mamba.setup.config().sections[self.tool]:
			split = mamba.setup.config().sections[self.tool]["split"]
		
		try:
			filenames = []
			output_filename = None
			split_filename = None
			for key in self.rest:
				if command.find("@"+key+" ") != -1:
					if "@"+key in fasta:
						self.rest[key] = self.fix_fasta(self.rest[key])
					if "@"+key == split:
						split_data = self.rest[key]
					else:
						filename = tempfile.mkstemp()[1]
						file = open(filename, "w")
						file.write(self.rest[key])
						file.close()
						command = command.replace("@"+key+" ", filename+" ")
						filenames.append(filename)
				elif command.find("$"+key+" ") != -1:
					command = command.replace("$"+key+" ", "'"+self.rest[key]+"' ")
			file_re = re.compile("@[^ ]+", re.I)
			match_used = set()
			for match in file_re.findall(command):
				if not match in match_used:
					match_used.add(match)
					filename = tempfile.mkstemp()[1]
					file = open(filename, "w")
					file.close()
					command = command.replace(match+" ", filename+" ")
					filenames.append(filename)
					if match == output:
						output_filename = filename
					if match == split:
						split_filename = filename
			
			# If no output name has been specified, capture stdout in a file.
			if not output:
				output_filename = tempfile.mkstemp()[1]
				command = command+" > "+output_filename
			
			outputs = []
			names = None
			if split:
				if (split in fasta):
					entries = split_data.replace("\n>", "\n\n-\n>").split("\n-\n")
					name_re = re.compile("^>([^ \t\r\n]*)")
					names = []
					for entry in entries:
						names.append(name_re.findall(entry)[0]) 
				else:
					entries = split_data.split("\n")
				for entry in entries:
					file = open(split_filename, "w")
					file.write(entry)
					file.close()
					os.system(command)
					file = open(output_filename, "r")
					outputs.append(file.read())
					file.close()
			else:
				os.system(command)
				file = open(output_filename, "r")
				outputs.append(file.read())
				file.close()
			
		except:
			
			# Return server error if tool failed to run properly.
			mamba.http.HTTPErrorResponse(self, 500, "Failed to run tool").send()
			
		finally:
			
			# Remove temporary files.
			for filename in filenames:
				try:
					os.remove(filename)
				except:
					pass
		
		return self.format(names, outputs, tool, format)
	
	def main(self):
		if not self.parse():
			return
		mamba.http.HTTPResponse(self, "\n\n".join(self.activate())).send()



class HTML(REST):
	
	def header(self, entry, names, tool):
		if names:
			id = entry
			name = names[entry]
		else:
			id = tool
			name = tool
		html = []
		html.append('''<table cellpadding='0' cellspacing='0' class='wrapper'>''')
		html.append('''<tr><th>%s<img onclick='switchView("scroll_%s", this)' src='%s' id='%s_collapse'></th></tr>''' % (name, id, web_img_hide, id))
		html.append('''<tr><td><div id='scroll_%s'><div>''' % id)
		return html
	
	def footer(self, spacer = None):
		html = []
		html.append('''</div></div></td></tr>''')
		if spacer:
			html.append('''<tr><td>''')
			html.append(spacer)
			html.append('''</td></tr>''')
		html.append('''</table>''')
		return html
	
	def format(self, names, outputs, tool, format):
		if format == None:
			if len(outputs) and outputs[0].find("\t") != -1:
				format = "tsv"
			else:
				format = "text"
		html = []
		if format == "csv":
			html += self.format_table(names, outputs, tool, ",")
		elif format == "file":
			html = outputs
		elif format == "gif":
			html += self.format_image(names, outputs, tool, "gif")
		elif format == "html":
			html += self.format_html(names, outputs, tool)
		elif format == "jpeg":
			html += self.format_image(names, outputs, tool, "jpeg")
		elif format == "png":
			html += self.format_image(names, outputs, tool, "png")
		elif format == "text":
			html += self.format_text(names, outputs, tool)
		elif format == "tsv":
			html += self.format_table(names, outputs, tool, "\t")
		return html
	
	def format_html(self, names, outputs, tool):
		html = []
		entry = 0
		for output in outputs:
			html += self.header(entry, names, tool)
			html.append('''<pre class="output">%s</pre>''' % output.strip("\r\n"))
			html += self.footer()
			entry += 1
		return html
	
	def format_image(self, names, outputs, tool, type):
		html = []
		entry = 0
		for output in outputs:
			html += self.header(entry, names, tool)
			html.append('''<img src="data:image/%s;base64,%s">''' % (type, base64.standard_b64encode(output)))
			html += self.footer()
			entry += 1
		return html
	
	def format_table(self, names, outputs, tool, delim, quote = None):
		widths = []
		for output in outputs:
			row = 0
			for line in output.split("\n"):
				column = 0
				for field in line.split(delim):
					if quote:
						field = field.strip(quote)
					if column >= len(widths):
						widths.append(len(field))
					elif len(field) > widths[column]:
						widths[column] = len(field)
					column += 1
				row += 1
		spacer = []
		spacer.append('''<table class='output'><tr>''')
		for width in widths:
			spacer.append('''<td>%s</td>''' % ("&nbsp;" * width))
		spacer.append('''</tr></table>''')
		spacer = "".join(spacer)
		html = []
		entry = 0
		for output in outputs:
			html += self.header(entry, names, tool)
			html.append('''<table cellpadding="0" cellspacing="0" class="output">''')
			row = 0
			for line in output.split("\n"):
				html.append('''<tr>''')
				for field in line.split("\t"):
					if row == 0:
						html.append('''<th>%s</th>''' % field)
					elif row%2:
						html.append('''<td>%s</td>''' % field)
					else:
						html.append('''<td class="odd">%s</td>''' % field)
				html.append('''</tr>''')
				row += 1
			html.append('''</table>''')
			html += self.footer(spacer)
			entry += 1
		return html

	def format_text(self, names, outputs, tool):
		width = 0
		for output in outputs:
			for line in output.split("\n"):
				if len(line) > width:
					width = len(line)
		spacer = '''<tr><td><pre>%s</pre></td></tr>''' % (" " * width)
		html = []
		entry = 0
		for output in outputs:
			html += self.header(entry, names, tool)
			html.append('''<pre class="output">%s</pre>''' % output.strip("\r\n"))
			html += self.footer(spacer)
			entry += 1
		return html
	
	def show(self, page, tool, index = 0):
		
		html = []
		
		if index:
			html.append('''<div class='div_inactive' id='%s_div'>''' % index)
		else:
			html.append('''<div class='div_active' id='%s_div'>''' % index)
		html.append('''<table class='wrapper' id='content'><tr><td>''')
		
		if page == "home":
			html.append('''<form action='%s' enctype="multipart/form-data" method = "post">''' % self.tool)
			if (tool != self.tool):
				html.append('''<input name='__tool__' type='hidden' value='%s' />''' % tool)
		
		if "page_"+page in mamba.setup.config().sections[tool]:
			value = mamba.setup.config().sections[tool]["page_"+page]
			if os.path.isfile(value):
				file = open(value, "rb")
				html.append(file.read())
				file.close()
			else:
				html.append(value)
		elif page == "home":
			if "command" in mamba.setup.config().sections[tool]:
				html1 = []
				html2 = []
				file_re = re.compile("[@$][^ ]+", re.I)
				for match in file_re.findall(mamba.setup.config().sections[tool]["command"]):
					name = match[1:]
					label = name.replace("_", " ")
					if match[0] == "@":
						html1.append('''%s<br/><textarea name='%s' cols='80' rows='10'></textarea><br />''' % (label, name))
					elif match[0] == "$":
						html2.append('''%s <input name='%s' size='10' type='text' /><br />''' % (label, name))
				html.append("<br />".join(html1+html2))
			elif "database" in mamba.setup.config().sections[tool]:
				file = open(mamba.setup.config().sections[tool]["database"], "r")
				html.append('''<table class='input'>''')
				for label in file.readline().split("\t"):
					label = label.strip()
					name = label.replace(" ", "_")
					html.append('''<tr><td>%s</td><td><select name='operator_%s'>''' % (label, name))
					for compare_value, compare_html in [("eq", "="), ("ne", "&ne;"), ("lt", "&lt;"), ("gt", "&gt;"), ("le", "&le;"), ("ge", "&ge;"), ("like", "like"), ("ilike", "ilike")]:
						html.append('''<option value='%s'>%s</option>''' % (compare_value, compare_html))
					html.append('''</select></td><td><input name='value_%s' size='20' type='text' /></td></tr>''' % name)
				html.append('''</table>''')
				file.close()
			else:
				mamba.http.HTTPErrorResponse(self, 404, "Page '%s' for tool '%s' does not exist" % (page, tool)).send()
				return
		else:
			mamba.http.HTTPErrorResponse(self, 404, "Page '%s' for tool '%s' does not exist" % (page, tool)).send()
			return
		
		if page == "home":
			html.append('''</td></tr><tr><td><input name='submit' style='float: right;' type='submit' value='SUBMIT' />''')
			html.append('''</form>''')
		
		html.append('''</td></tr></table>''')
		html.append('''</div>''')
		return html		
	
	def main(self):
		
		if not self.parse():
			return
		
		if "submit" in self.rest and "format" in mamba.setup.config().sections[self.tool] and mamba.setup.config().sections[self.tool]["format"] == "file":
			if "__tool__" in self.rest:
				outputs = self.activate(self.rest["__tool__"])
			else:
				outputs = self.activate()
			mamba.http.HTTPResponse(self, "\n".join(outputs), content_type="application/octet-stream").send()
			return
		
		self.color = "#018001"
		if "color" in mamba.setup.config().sections[self.tool]:
			self.color = mamba.setup.config().sections[self.tool]["color"]
		
		self.width = "35em"
		if "width" in mamba.setup.config().sections[self.tool]:
			self.width = mamba.setup.config().sections[self.tool]["width"]
		
		# Create page header.
		html = []
		html.append('''<html><head>''')
		html.append(web_script)
		html.append(web_style.replace('$color', self.color).replace('$width', self.width))
		html.append('''</head>''')
		html.append('''<body><table cellpadding='0' cellspacing='0'><tr><td colspan='2' style='text-align: right;'>''')
		html.append('''<div id='title1'><a href='%s'>%s</a></div>''' % (self.tool, self.tool))
		html.append('''<div id='title2'>&nbsp;</div>''')
		pages = []
		for key in mamba.setup.config().sections[self.tool]:
			if key.startswith("page_") and not key == "page_home":
				pages.append(key.lower()[5:])
		if pages != []:
			pages.sort()
			pages.insert(0, "home")
			html.append('''<table class='pages'><tr>''')
			for page in pages:
				html.append('''<td><a href='%s?page=%s'>%s</a></td>''' % (self.tool, page, page.upper()))
			html.append('''</tr></table>''')
		html.append('''</td>''')
		html.append('''</tr>''')
		
		# Create page content.
		if "submit" in self.rest:
			html.append('''<tr><td id='left'></td><td>''')
			if "__tool__" in self.rest:
				html += self.activate(self.rest["__tool__"])
			else:
				html += self.activate()
			html.append('''</td></tr>''')
		else:
			page = "home"
			if "page" in self.rest:
				page = self.rest["page"].lower()
			if page == "home" and "tools" in mamba.setup.config().sections[self.tool] and not "page_home" in mamba.setup.config().sections[self.tool]:
				tools = []
				for tool in mamba.setup.config().sections[self.tool]["tools"].split(";"):
					tool = tool.strip(" ")
					if tool:
						tools.append(tool)
				html.append('''<tr><td id='left'><table cellpadding='0' cellspacing='0'>''')
				index = 0
				for tool in tools:
					if index:
						html.append('''<tr><td class='tab_inactive' id='%s_tab' onclick='showForm("%s")'>%s</td></tr><tr><td class="space"></td></tr>''' % (index, index, tool))
					else:
						html.append('''<tr><td class='tab_active' id='%s_tab' onclick='showForm("%s")'>%s</td></tr><tr><td class="space"></td></tr>''' % (index, index, tool))
					index += 1
				html.append('''</table></td><td>''')
				index = 0
				for tool in tools:
					html += self.show(page, tool, index)
					index += 1
				html.append('''</td></tr>''')
			else:
				html.append('''<tr><td id='left'></td><td>''')
				html += self.show(page, self.tool)
				html.append('''</td></tr>''')
		
		# Create page footer.
		if "footer" in mamba.setup.config().sections[self.tool]:
			html.append('''<tr><td id='left'></td><td><span id='footer'>%s</span></td></tr>''' % mamba.setup.config().sections[self.tool]["footer"])
		html.append('''</table></body></html>''')
		
		mamba.http.HTTPResponse(self, "\n".join(html), content_type="text/html").send()
