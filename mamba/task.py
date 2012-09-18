##############################################################################
# Copyright (c) 2010, 2011, Sune Frankild and Lars Juhl Jensen
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

import os
import re
import sys
import glob
import types
import urllib
import hashlib
import ConfigParser

try:
	import pg
except ImportError:
	import sys
	sys.stderr.write("[WARN]  User-settings disabled, pg module (Postgres) not installed.\n")

import mamba.util
import mamba.http
import mamba.setup


class RestDecoder:
	
	CONTENT_TYPE        = re.compile('''boundary=([^ \t\r\n]+)''', re.I)
	CONTENT_DISPOSITION = re.compile('''^Content-Disposition: .*? name="(.+?)".*?\r\n\r\n''', re.I | re.M | re.S)
	
	def __init__(self, request):
		self._table = {}
		mime_multipart = False
		if "Content-Type" in request.http.headers:
			match = RestDecoder.CONTENT_TYPE.search(request.http.headers["Content-Type"])
			if match:
				mime_multipart = True
				for mime_part in request.http.body.split("\r\n--"+match.group(1)):
					match = RestDecoder.CONTENT_DISPOSITION.search(mime_part)
					if match:
						self._table[match.group(1)] = mime_part[match.end(0):]
		if not mime_multipart:
			for item in request.http.get_parse_data().split("&"):
				if item and len(item):
					items = item.split("=")
					if len(items):
						key   = items[0]
						value = ""
					if len(items) >= 2:
						key   = items[0]
						value = '='.join(items[1:])
					key   = urllib.unquote_plus(key)
					value = urllib.unquote_plus(value)
					if request.http.charset != None:
						value = unicode(value, request.http.charset, errors="replace")
					self._table[key] = value

	def __contains__(self, key):
		return key in self._table
	
	def __delitem__(self, key):
		del self._table[key]
	
	def __getitem__(self, key):
		if key not in self._table:
			return None
		else:
			return self._table[key]
	
	def __iter__(self):
		return self._table.__iter__()
	
	def __setitem__(self, key, item):
		self._table[key] = item


class SyntaxError(Exception)         : pass
class PermissionError(Exception)     : pass
class NextMethodNotDefined(Exception): pass
class QueueNotDefined(Exception)     : pass


class Task:
	
	def __init__(self, priority):
		self.priority = priority
		self.worker   = None
		
	def __cmp__(self, other):
		return cmp(self.priority, other.priority)
		

class StopTask(Task):

	def __init__(self):
		Task.__init__(self, 99)
	

class Request(Task):
	
	def __init__(self, http, action=None, priority=0):
		Task.__init__(self, priority)
		self.http = http
		self.charset = self.http.charset        
		self.get_user_settings()
		if action == None:
			self.action = str(self.__class__).split(".")[-1]
		else:
			self.action = action
					
	def queue_exists(self, queue_name):
		try:
			self.worker.server.get_queue(queue_name)
			return True
		except Exception:
			return False
		
	def queue(self, queue_name, method = None):
		if method:
			self.next = method # Ok, use an alternative method instead of that matching the queue name.
		else:
			if hasattr(self, queue_name):
				method = getattr(self, queue_name)
				self.next = method
			else:
				raise NextMethodNotDefined, "Cannot put request '%s' on queue '%s' because the request has no method called '%s()'." % (self.__class__, queue_name, queue_name)
		if self.worker:
			self.worker.server.get_queue(queue_name).put(self)
			
	def _connect_to_user_database(self):
		connection_string = mamba.setup.config().server.user_database
		if connection_string != None:
			host, port, user, passwd, database = connection_string.split(':')
			try:
				conn = pg.connect(dbname=database, host=host, port=int(port), user=user, passwd=passwd)
				return conn
			except pg.InternalError, e:
				self.err(str(e).strip())
				return None
		return None
		
	def get_user_settings(self):
		self.user_settings = {}
		default_user_settings = mamba.setup.config().user_settings
		for key in default_user_settings:
			self.user_settings[key] = default_user_settings[key]
		if not self.http.uuid:
			return
		conn = self._connect_to_user_database()
		if not conn:
			return
		for row in conn.query("SELECT key, value FROM user_settings WHERE uuid='%s';" % self.http.uuid).getresult():
			key = row[0]
			value = row[1]
			if key in self.user_settings:
				self.user_settings[key] = value
		conn.close()
	
	def set_user_settings(self):
		if not self.http.uuid:
			return
		conn = self._connect_to_user_database()
		if not conn:
			return
		default_user_settings = mamba.setup.config().user_settings
		cmd = []
		cmd.append("DELETE FROM user_settings WHERE uuid='%s';" % self.http.uuid)
		for key in self.user_settings:
			value = self.user_settings[key]
			if key in default_user_settings and value != default_user_settings[key]:
				cmd.append("INSERT INTO user_settings (uuid, key, value) VALUES ('%s', '%s', '%s');" % (self.http.uuid, key, value))
		conn.query(' '.join(cmd).strip())
		conn.close()
		
	def info(self, *args):
		if self.worker:
			old = self.worker.get_frames_back()
			self.worker.set_frames_back(3)
			self.worker.info(*args)
			self.worker.set_frames_back(old)
		else:
			print "[INFO]:", " ".join([str(args[i]) for i in range(len(args))])

	def warn(self, *args):
		if self.worker:
			old = self.worker.get_frames_back()
			self.worker.set_frames_back(3)
			self.worker.warn(*args)
			self.worker.set_frames_back(old)
		else:
			print "[WARN]:", " ".join([str(args[i]) for i in range(len(args))])

	def err(self, *args):
		if self.worker:
			old = self.worker.get_frames_back()
			self.worker.set_frames_back(3)
			self.worker.err(*args)
			self.worker.set_frames_back(old)
		else:
			print "[ERR]:", " ".join([str(args[i]) for i in range(len(args))])

	def debug(self, *args):
		if self.worker:
			old = self.worker.get_frames_back()
			self.worker.set_frames_back(3)
			self.worker.debug(*args)
			self.worker.set_frames_back(old)
		else:
			print "[DEBUG]:", " ".join([str(args[i]) for i in range(len(args))])


class GetUserSettings(Request):
	
	def main(self):
		text = []
		for key in self.user_settings:
			text.append("%s\t%s\n" % (key, self.user_settings[key]))
		reply = mamba.http.HTTPResponse(self, "".join(text), content_type="text/plain")
		reply.send()
	

class SetUserSettings(Request):
	
	def main(self):
		rest = mamba.task.RestDecoder(self)
		for key in self.user_settings:
			value = rest[key]
			if value != None:
				self.user_settings[key] = value
		self.set_user_settings()
		reply = mamba.http.HTTPResponse(self, "OK", content_type="text/html")
		reply.send()
	


class ErrorRequest(Request):
	"""Class for wrapping HTTP objects that during receive of client data
	leads to an error (like unknown request etc.) such that an answer
	must be send back to the client even though we could not assign the
	request to any meaningful request type."""
	

class EmptyRequest(Request):
	
	def parse(self):
		pass


class SecureRequest(Request):
	
	def __init__(self, http, action=None, priority=0):
		Request.__init__(self, http, action, priority)
		
	def password_correct(self):
		rest = RestDecoder(self)
		if "passwd" not in rest:
			return False
		else:
			md5 = hashlib.md5()
			md5.update(rest["passwd"])
			return md5.hexdigest() == mamba.setup.config().security.password

	def trusted_client(self):
		return self.http.remote_ip == mamba.setup.config().security.trusted

	def request_is_allowed(self):
		return self.password_correct() or self.trusted_client()


class GetStatus(SecureRequest):

	def main(self):
		rest = RestDecoder(self)
		if "passwd" in rest:
			if self.password_correct():
				reply = mamba.http.HTTPResponse(self, body=mamba.util.get_complete_status_html(self.worker.server), content_type="text/html")
				reply.send()
			else:
				reply = mamba.http.HTTPErrorResponse(self, 401, "You do not have the rights to view the full status report.")
				reply.send()
		else:
			reply = mamba.http.HTMLResponse(self, mamba.util.get_simple_stauts_html(self.worker.server))
			reply.send()


class Download(SecureRequest):
		
	def download(self):
		rest = RestDecoder(self) 
		uri = rest["uri"]
		proxy_mode  = (rest["proxy_mode"]  == "1")
		insert_base = (rest["insert_base"] == "1")
		if self.request_is_allowed():
			if uri:
				if not uri.lower().startswith("http://"):
					uri = "http://" + uri
				page, status, headers, page_uri, charset = mamba.http.Internet().download(uri, self.http, proxy_mode=proxy_mode, insert_base=insert_base)
				reply = mamba.http.HTTPResponse(self, status=status, body=page, headers=headers)
				reply.charset = charset
				reply.send()
			else:
				reply = mamba.http.HTTPErrorResponse(self, 400, "No URI specified for download.")
				reply.send()
		else:
			reply = mamba.http.HTTPErrorResponse(self, 401, "You do not have the rights to download.")
			reply.send()
			
	def main(self):
		if self.queue_exists("download"):
			self.queue("download")
		else:
			self.download()


class Proxy(Request):
	
	def __init__(self, http, fetch_url):
		Request.__init__(self, http)
		self.fetch_url = fetch_url
		
	def main(self):
		if self.queue_exists("proxy"):
			self.queue("proxy")
		else:
			self.proxy()
	
	def proxy(self):
		page, status, headers, page_uri = mamba.http.Internet().download_raw(self.fetch_url, self.http, proxy_mode=True)
		reply = mamba.http.HTTPProxyResponse(self, status=status, headers=headers, body=page)
		reply.send()


class GetFile(Request):
	
	def __init__(self, http, filename):
		Request.__init__(self, http)
		self.filename = filename
		
	def main(self):
		mime_type, mime_encoding = mamba.util.MimeTypes.guess_type(self.filename)
		if mime_type:
			reply = mamba.http.HTTPResponse(self, open(self.filename, "rb").read(), content_type=mime_type, encoding=mime_encoding)
			reply.message = os.path.relpath(self.filename)
			reply.send()
		else:
			reply = mamba.http.HTTPErrorResponse(self, 415, "Unable to guess MIME type for file: %s" % self.filename)
			reply.send()
			

def get_plugin_folders(ini_filename):
	ini = ConfigParser.ConfigParser()
	ini.read(ini_filename)
	srv = mamba.setup.Configuration.Server()
	srv.from_config(ini)
	return srv.plugins

def import_plugin_modules(ini_filename=None, logger=None, folders=[]):
	"""Returns a string with all import statements necessary to import all
	.py modules under the plugins stated in the .ini file. This functions
	prepare a statement which the caller must execute using the exec key word.
	The sys.path list is appropriately updated to include the path to the
	modules such that the executed import will not fail.
	Example:

	exec mamba.task.import_plugin_modules("./mysetup.ini")
	"""
	import_statements = []
	if folders == None or len(folders) == 0:
		if ini_filename:
			folders = get_plugin_folders(ini_filename)
		elif mamba.setup.config() != None:
			folders = get_plugin_folders(mamba.setup.config().ini_file)
		elif logger:
			logger.warn("No plugins loaded. No folders and .ini file provided.")
		
	for dirname in folders:
		if dirname == os.path.abspath("./"):
			return
		if os.path.exists(dirname) and os.path.isdir(dirname):
			if dirname not in sys.path:
				sys.path.append(os.path.abspath(dirname))
			for filename in glob.glob("%s/*.py" % dirname):
				import_statements.append("import %s" % os.path.basename(filename.split(".py")[0]))
	return "\n".join(import_statements)
	

def import_plugins(ini_filename=None, logger=None, folders=[]):
	config  = None
	plugins = {}
	if folders == None or len(folders) == 0:
		if ini_filename:
			folders = get_plugin_folders(ini_filename)
		elif mamba.setup.config() != None:
			folders = get_plugin_folders(mamba.setup.config().ini_file)
		elif logger:
			logger.warn("No plugins loaded. No folders and .ini file provided.")
		
	for dirname in folders:
		if dirname == os.path.abspath("./"):
			return
		if os.path.exists(dirname) and os.path.isdir(dirname):
			sys.path.append(os.path.abspath(dirname))
			for filename in glob.glob(os.path.join(dirname, "*.py")):
				name = os.path.basename(filename)
				if not name.startswith('__'):
					name = name.replace(".py", "")
					#if name not in sys.modules and name != "mambasrv":
					if name != "mambasrv":
						if logger:
							logger.info("Importing plugin '%s':" % name)
						try:
							__import__(name, globals(), locals(), [], -1)
						except ImportError, e:
							if logger:
								logger.err("Import failed for module %s from file %s. Message: %s" % (name, filename, str(e)))
							raise e
					else:
						if logger:
							logger.info("Plugin '%s' was already imported - fine." % name)
					if name in sys.modules:
						module = sys.modules[name]
						for symbol in dir(module):
							if symbol.startswith('_') or symbol.endswith("Request"):
								continue
							type = getattr(module, symbol)
							try:
								if type in plugins and logger:
									logger.err("Plugin '%s' redefines class '%s'." % (str(module), str(type)))
								else:
									if isinstance(type, types.ClassType):
										if issubclass(type, Request):
											plugins[symbol.lower()] = type
											if logger:
												logger.info(" - Loaded request handler: %s" % symbol)
										elif ini_filename and issubclass(type, mamba.setup.Configuration):
											config = type
							except TypeError, e:
								if logger:
									logger.warn("Error analyzing type '%s'. Message: '%s'" % (str(type), str(e)))
	return config, plugins
