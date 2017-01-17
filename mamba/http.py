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
import sys
import re
import glob
import socket
import urllib
import urlparse
import time
import datetime
import StringIO
import gzip
import traceback
import codecs
import uuid
import select
import threading

import mamba.util
import mamba.setup
import mamba.task
import mamba.http


http_status_codes = {}
http_status_codes[100] = "Continue"
http_status_codes[101] = "Switching Protocols"
http_status_codes[102] = "Processing"

http_status_codes[200] = "OK"
http_status_codes[201] = "Created"
http_status_codes[202] = "Accepted"
http_status_codes[203] = "Non-Authoritative Information"
http_status_codes[204] = "No Content"
http_status_codes[205] = "Reset Content"
http_status_codes[206] = "Partial Content"
http_status_codes[207] = "Multi-Status"

http_status_codes[300] = "Multiple Choices"
http_status_codes[301] = "Moved Permanently"
http_status_codes[302] = "Found"
http_status_codes[303] = "See Other"
http_status_codes[304] = "Not Modified"
http_status_codes[305] = "Use Proxy"
http_status_codes[306] = "Switch Proxy"
http_status_codes[307] = "Temporary Redirect"

http_status_codes[400] = "Bad Request"
http_status_codes[401] = "Unauthorized"
http_status_codes[402] = "Payment Required"
http_status_codes[403] = "Forbidden"
http_status_codes[404] = "Not Found"
http_status_codes[405] = "Method Not Allowed"
http_status_codes[406] = "Not Acceptable"
http_status_codes[407] = "Proxy Authentication Required"
http_status_codes[408] = "Request Timeout"
http_status_codes[409] = "Conflict"
http_status_codes[410] = "Gone"
http_status_codes[411] = "Length Required"
http_status_codes[412] = "Precondition Failed"
http_status_codes[413] = "Request Entity Too Large"
http_status_codes[414] = "Request-URI Too Long"
http_status_codes[415] = "Unsupported Media Type"
http_status_codes[416] = "Requested Range Not Satisfiable"
http_status_codes[417] = "Expectation Failed"
http_status_codes[422] = "Unprocessable Entity"
http_status_codes[423] = "Locked"
http_status_codes[424] = "Failed Dependency"
http_status_codes[425] = "Unordered Collection"
http_status_codes[426] = "Upgrade Required"
http_status_codes[449] = "Retry With"
http_status_codes[450] = "Blocked by Windows Parental Controls"

http_status_codes[500] = "Internal Server Error"
http_status_codes[501] = "Not Implemented"
http_status_codes[502] = "Bad Gateway"
http_status_codes[503] = "Service Unavailable"
http_status_codes[504] = "Gateway Timeout"
http_status_codes[505] = "HTTP Version Not Supported"
http_status_codes[506] = "Variant Also Negotiates"
http_status_codes[507] = "Insufficient Storage"
http_status_codes[509] = "Bandwidth Limit Exceeded"
http_status_codes[510] = "Not Extended"


def easy_zip(document):
	zbuff = StringIO.StringIO()
	zfile = gzip.GzipFile(mode="wb", fileobj=zbuff, compresslevel=9)
	zfile.write(document)
	zfile.close()
	return zbuff.getvalue()
	
def easy_unzip(gzipped):
	zbuff = StringIO.StringIO(gzipped)
	zfile = gzip.GzipFile(fileobj=zbuff)
	return zfile.read()


class HTTPHeader:
	
	RE_HEADERS = re.compile("([a-z0-9_-]+) *: * ([^\r\n]+)\r?\n?", re.I)
	
	def __init__(self, headers=None):
		self._dict = {}
		if headers:
			if isinstance(headers, str):
				self.parse(headers)
			elif isinstance(headers, list):
				self.set_headers(headers)
			elif isinstance(headers, HTTPHeader):
				self.duplicate(headers)
			else:
				raise ValueError, "argument 'headers' in constructor is neither a str, list or HTTPHeader object."
			
	def normalize_name(self, name):
		return "-".join(map(str.capitalize, name.strip().split("-")))
		
	def parse(self, headers):
		for match in HTTPHeader.RE_HEADERS.findall(headers):
			self._dict[self.normalize_name(match[0])] = match[1]
			
	def set_headers(self, headers_list):
		for key, value in headers_list:
			self._dict[self.normalize_name(key)] = value
			
	def __iter__(self):
		return self._dict.__iter__()
			
	def __contains__(self, key):
		return self.normalize_name(key) in self._dict
		
	def __getitem__(self, key):
		return self._dict[self.normalize_name(key)]
		
	def __setitem__(self, key, value):
		self._dict[self.normalize_name(key)] = value.strip()
		
	def __delitem__(self, key):
		del self._dict[self.normalize_name(key)]
		
	def __len__(self):
		return len(self._dict)
		
	def __str__(self):
		http = []
		for norm_name in sorted(self._dict):
			http.append("%s: %s" % (norm_name, self._dict[norm_name]))
		return "\r\n".join(http)
	
	def add(self, key, value):
		self.__setitem__(key, value)
		
	def remove(self, key):
		self.__delitem__(key)
		
	def find(self, key, part_of_value):
		if key not in self:
			return False
		return part_of_value in self[key].lower()
		
	def copy(self):
		headers = HTTPHeader()
		for norm_name in self._dict:
			headers._dict[norm_name] = self._dict[norm_name]
		return headers
	
	def duplicate(self, other_headers):
		self._dict.clear()
		for norm_name in other_headers._dict:
			self._dict[norm_name] = other_headers._dict[norm_name]
			
	def clear(self):
		self._dict.clear()


class HTTPResponse:
	
	def __init__(self, request, body=None, content_type=None, encoding=None, status=200, headers=None):
		self.request = request
		self.body = body
		self.status = status
		self.content_type = content_type
		self.encoding = encoding if encoding else request.http.charset
		self.headers = HTTPHeader(headers)
		if content_type:
			if not self.encoding:
				self.headers.add("Content-Type", content_type)
			else:
				self.headers.add("Content-Type", content_type + "; charset=" + self.encoding)
		
	def __str__(self):
		headers = self.headers.copy()
		headers.add("Access-Control-Allow-Headers", "'Accept,Cache-Control,Content-Type,Depth,If-Modified-Since,NCBI-PHID,Origin,User-Agent,X-File-Name,X-File-Size,X-Prototype-Version,X-Requested-With")
		headers.add("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
		headers.add("Access-Control-Allow-Origin", "*")
		headers.add("Connection", "close")
		headers.add("Date", datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S UTC"))
		if self.request.http.uuid:
			expires = (datetime.datetime.now()+datetime.timedelta(weeks=52*10)).strftime("%a, %d-%b-%Y %H:%M:%S UTC")
			headers.add("Set-Cookie", "%s=%s; expires=%s" % (mamba.setup.config().server.user_cookie, self.request.http.uuid, expires))
		if mamba.setup.config().other_servers.servers:
			headers.add("Servers", ", ".join([mamba.setup.config().server.host] + mamba.setup.config().other_servers.servers))
		if mamba.setup.config().server.version:
			headers.add("Version", "Mamba server (%s)" % mamba.setup.config().server.version)
		content = self.body
		if content and isinstance(content, unicode):
			content = mamba.util.string_to_bytes(content, self.encoding)
		if self.content_type:
			content_class = self.content_type.split("/")[0].strip().lower()
			if content_class == "text":
				if self.body and self.request.http.accept_encoding_gzip():
					headers.add("Content-Encoding", "gzip")
					content = easy_zip(content)
			elif content_class == "image" or self.encoding == "binary":
				headers.add("Accept-Ranges", "bytes")
		if content:
			headers.add("Content-Length", str(len(content)))
		http = []
		http.append("HTTP/1.1 %i %s\r\n" % (self.status, http_status_codes[self.status]))
		http.append(str(headers))
		http.append("\r\n\r\n")
		if content:
			http.append(content)
		http = "".join(http)
		return http
		
	def get_reason(self):
		return http_status_codes[self.status]
	
	def send(self):
		self.request.worker.server.add_response(self)
		
		
class HTMLResponse(HTTPResponse):
	
	def __init__(self, request, html, status=200, headers=None, encoding=None):
		HTTPResponse.__init__(self, request, html, "text/html", encoding, status, headers)
		


class HTTPRedirect(HTTPResponse):
	
	def __init__(self, request, location, status=303):
		HTTPResponse.__init__(self, request, status=status)
		self.headers.add("Location", location)


class HTTPErrorResponse(HTTPResponse):
	
	def __init__(self, request, status, message, exception=None):
		HTTPResponse.__init__(self, request, content_type="text/html", status=status)
		self.message = message
		reason = http_status_codes[status]
		body = []
		body.append("<!DOCTYPE HTML PUBLIC \"-//IETF//DTD HTML 2.0//EN\">")
		body.append("<html>")
		body.append("  <head>")
		body.append("    <title> %s (%i)</title>" % (reason, status))
		body.append("  </head>")
		body.append("<body>")
		body.append("<h1> %s (%i)</h1>" % (reason, status))
		body.append("<p>%s<BR>" % message)
		body.append("<p>%s<BR>" % datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S UTC"))
		if status in (500, 501):
			body.append("<hr>")
			body.append("Please make sure your request adheres to the rules defined by the API.<br>")
		if mamba.setup.config() and mamba.setup.config().http.error_details and exception:
			body.append("<strong>Error type :</strong> % <br>" % str(type(exception)))
			body.append("<strong>Error message :</strong> %s <br>" % str(exception))
			body.append("<P><B>Stack trace:</B><BR>")
			n = 1
			for line in traceback.format_exc().split("\n"):
				body.append(str("<strong>Line %3i :</strong> %s <br>" % (n, line)))
				n += 1
			body.append("<p>")
		body.append("</body>")
		body.append("</html>")
		self.body = "\r\n".join(body)


class HTTPProxyResponse(HTTPResponse):
	
	def __init__(self, request, status, headers, body):
		HTTPResponse.__init__(self, request, status=status, headers=headers, body=body)
		if "Connection" in self.headers:
			del self.headers["Connection"]
			self.headers.add("Connection", "close")
		
	def __str__(self):
		http = []
		http.append("HTTP/1.1 %i %s\r\n" % (self.status, http_status_codes[self.status]))
		http.append(str(self.headers))
		http.append("\r\n\r\n")
		if self.body:
			http.append(self.body)
		http = "".join(http)
		return http


_sock_buf_size = 64*(2**10) # 32 Kilo bytes.

class HTTPRequest:
	
	_re_double_newline = re.compile("\r?\n\r?\n", re.I)
	_re_http = re.compile("^(?P<method>GET|POST|PUT|DELETE|HEAD|OPTIONS|TRACE|CONNECT) (?P<url>([^ ]*)) HTTP/(?P<version>1.[0-1])\r?\n(?P<headers>.*?)\r?\n\r?\n", re.I | re.DOTALL)
	_re_header = re.compile("(?P<key>[a-z0-9_-]+): (?P<value>.+?)\r?\n", re.I)
	_re_content_charset = re.compile("charset=(?P<encoding>[-\w]+)$", re.I)
	
	def __init__(self, client_conn, remote_ip, serial):
		self.conn           = client_conn
		self.remote_ip      = remote_ip
		self.serial         = serial
		self.duration       = datetime.datetime.now()
		self.uuid           = None
		self.data           = []      # The data from the client socket.
		self.bytes_received =  0
		self.header_size    = -1
		self.got_null_byte  = False   # Indicator if we got a null byte.
		self.last_read_time = None    # Time of last read byte.
		self.method         = ""    # GET/POST etc.
		self.url            = ""
		self.path           = ""
		self.query          = ""    # ?document=IL5
		self.version        = None    # E.g. "1.1" for "HTTP/1.1".
		self.headers        = HTTPHeader()    # Collection of HTTP headers.
		self.charset        = "utf-8" # Default value used in replies. See: get_preferred_charset().
		self.content_length = 0
		self.body           = None    # The body text.
		
	def parse(self, http_data):
		match = HTTPRequest._re_http.match(http_data)
		if match:
			self.method  = match.group("method")
			self.version = match.group("version")
			self.url     = match.group("url")
			urlinfo = urlparse.urlsplit(self.url)
			self.path    = urlinfo.path
			self.query   = urlinfo.query
			if self.headers:
				self.headers.clear()
			self.headers.parse(match.group("headers"))
			self.body = http_data[match.end(0):]
			return True
		else:
			return False
		
	def get_action(self):
		if self.path != None:
			return os.path.basename(self.path)
		return None
		
	def _assign_uuid(self):
		cookie = None
		if "Cookie" in self.headers:
			cookie = self.headers["Cookie"]
		if cookie:
			for f in cookie.split():
				if f.startswith(mamba.setup.config().server.user_cookie):
					key, value = map(lambda s: s.strip(), f.split("="))
					self.uuid = value.replace(";", "")
					break
		if self.uuid == None:
			self.uuid = str(uuid.uuid1()).upper()

	def get_parse_data(self):
		return "&".join((self.query, self.body))
	
	def accept_encoding_gzip(self):
		if "Accept-Encoding" in self.headers:
			return "gzip" in self.headers["Accept-Encoding"].lower()
		return False
	
	def get_preferred_charset(self):
		content_type = None
		charset_content = None
		if "Content-Type" in self.headers:
			content_type = self.headers["Content-Type"]
			match = HTTPRequest._re_content_charset.search(content_type)
			if match:
				charset = match.group("encoding")
				try:
					encoding = codecs.lookup(charset)
					charset_content = encoding.name
				except Exception:
					charset_content = None
		if not charset_content:
			charset_content = "utf-8"
		return charset_content
	
	def finallize(self):
		self.duration = datetime.datetime.now() - self.duration
		if not self.parse("".join(self.data)):
			raise RuntimeError, "Client data is not a HTTP request."
		self.data = None  # Reset data array. No use for it anymore.
		self.charset = self.get_preferred_charset()
		if self.method == "POST":
			if self.body == None or len(self.body)==0:
				raise mamba.http.HTTPErrorResponse(mamba.task.ErrorRequest(self), 400, "POST request was malformed. Contained no body.")
		elif self.method == "GET":
			if len(self.body):
				raise mamba.http.HTTPErrorResponse(mamba.task.ErrorRequest(self), 400, "GET request was malformed. Contained an unexpected body.")
		elif self.method == "OPTIONS":
			if len(self.body):
				raise mamba.http.HTTPErrorResponse(mamba.task.ErrorRequest(self), 400, "OPTIONS request was malformed. Contained an unexpected body.")
		
	def size(self):
		return self.header_size + self.content_length   
				
	def is_complete(self):
		if self.bytes_received >= self.size():
			return True
		if self.bytes_received >= mamba.setup.config().http.max_data_client:
			return True
		if self.got_null_byte:
			return True
		if self.method:
			if self.method == "GET" or self.method == "OPTIONS":
				return True
			elif self.method == "POST":
				current_body_size = self.bytes_received - self.header_size
				if current_body_size >= self.content_length:
					return True
				else:
					return False
		if self.last_read_time != None:
			dT = datetime.datetime.now() - self.last_read_time
			if dT.seconds > mamba.setup.config().http.max_wait:
				return True
		
	def recv(self):
		data = self.conn.recv(_sock_buf_size)
		self.last_read_time = datetime.datetime.now()
		if data == None:
			self.got_null_byte = True
		elif len(data) == 0:
			return 0
		else:
			self.bytes_received += len(data)
			self.data.append(data)
		if not self.headers:
			if len(self.data) > 1:
				chunk = "".join((self.data[-2], self.data[-1]))
			else:
				chunk = data
			double_newline = HTTPRequest._re_double_newline.search(chunk)
			if double_newline:
				http_header = "".join(self.data)
				self.header_size = len(http_header) - len(chunk) + double_newline.end(0)
				if not self.parse(http_header):
					raise RuntimeError, "Client data is not a HTTP request."
				self._assign_uuid()
				if self.method == "GET" or self.method == "OPTIONS":
					self.content_length = 0  # Ensures header is analyzed just once.
				elif self.method != "POST":
					return -1
				if "x-forwarded-For" in self.headers:
					self.remote_ip = self.headers["x-forwarded-For"].split()[-1]
				if "Content-Length" in self.headers:
					self.content_length = int(self.headers["Content-Length"])
				if self.content_length > mamba.setup.config().http.max_msg_content:
					return -2
				Tracking().append_task(self)
			elif self.bytes_received > mamba.setup.config().http.max_msg_header:
				return -3
		return 1


class HTTPOperator(mamba.util.Logger):
	
	def __init__(self, deadman_filename):
		mamba.util.Logger.__init__(self, 'network')
		self._mutex                 = threading.Lock()
		self._server_socket         = None
		self._shutdown              = False
		self._readable_sockets      = {}
		self._writeable_sockets     = {}
		self._on_reply_socket_read  = None
		self._on_reply_socket_write = None
		self._client_count          = 0
		self._deadman_filename      = deadman_filename
		
	def initialize(self):
		if self._deadman_filename:
			os.system("touch %s" % self._deadman_filename)
		if self._shutdown:
			self.info("Network is re-initializing.")
			self._shutdown = False
		self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		try:
			host = mamba.setup.config().server.host
			port = mamba.setup.config().server.port
			self._server_socket.bind((host, port))
			self.info("Starting server on '%s' port %i." % (host, port))
			self._server_socket.listen(5)
			self._on_reply_socket_write = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self._on_reply_socket_write.connect((host, port))
			self._on_reply_socket_write.setblocking(False)
			self._on_reply_socket_read = None
			return True
		except socket.error, e:
			if not mamba.setup.config().server.wait_on_port:
				self.err("Server could not bind to port:", mamba.setup.config().server.port)
				self.err(e)
			return False
	
	def shutdown(self):
		try:
			self._mutex.acquire()
			self.debug("Network is shutting down.")
			self.debug("Pending tasks (before setting _shutdown to True):", Tracking().pending_tasks())
			self._shutdown = True
		finally:
			self._mutex.release()
			self.notify_select()
			
	def tear_down(self):
		self.debug("Network is tearing down.")
		for conn in self._get_all_read_sockets() + self._get_all_write_sockets():
			if conn:
				try:
					conn.shutdown(socket.SHUT_RDWR)
				except socket.error, e:
					errcode, msg = e.args
					if errcode not in (57, 107):
						self.warn("Failed to shutdown socket: '%s'" % (str(e)))
				except Exception, e:
					self.warn("Unhandled exception caught while shutdown of socket: '%s'." % str(e))
				finally:
					conn.close()
		self._on_reply_socket_read  = None
		self._on_reply_socket_write = None
		self._server_socket     = None
		self._readable_sockets  = {}
		self._writeable_sockets = {}
		
	def notify_select(self):
		self._on_reply_socket_write.sendall("x")
	
	def _get_all_read_sockets(self):
		return [self._server_socket] + self._readable_sockets.keys()
		
	def _get_all_write_sockets(self):
		return self._writeable_sockets.keys()
		
	def add_response(self, reply):
		self.debug("Response (%i, '%s') added to client %s" % (reply.status, reply.get_reason(), reply.request.http.remote_ip))
		reply_string = str(reply)
		self._mutex.acquire()
		self._writeable_sockets[reply.request.http.conn] = [reply, reply_string, 0]
		self._mutex.release()
		self.notify_select()
		Tracking().save_track_file("reply", reply_string, reply.request.http.remote_ip)
		
	def task_done(self, reply):
		now = self.now()
		serial = reply.request.http.serial
		if isinstance(reply.request, mamba.task.GetFile):
			action = "GET"
		else:
			action = reply.request.http.get_action()
		uuid = reply.request.http.uuid
		ip = reply.request.http.remote_ip
		reason = reply.get_reason()
		message = None
		if isinstance(reply, mamba.http.HTTPErrorResponse) or hasattr(reply, "message"):
			message = reply.message
		elif isinstance(reply, mamba.http.HTTPResponse):
			message = mamba.http.http_status_codes[reply.status]
		if message == None:
			message = ''
		out = str("%s\t%i\t%s\t%s\t%s\t%s:%s\n" % (now, serial, ip, uuid, action, reply.status, message.encode(reply.request.http.charset)))
		try:
			sys.stdout.write(out)
			sys.stdout.flush()
		except IOError:
			pass
		if self.file != sys.stdout and mamba.setup.config().log.active:
			self.file.write(out)
			self.file.flush()
		
	def on_error_receive(self, conn):
		if conn:
			conn
			http = None
			if conn in self._readable_sockets:
				http = self._readable_sockets[conn]
				self.warn("Socket receive error. Clearing up after client '%s'" % http.remote_ip)
				for key in http.headers:
					self.warn("  Client header: '%s: %s'" % (key, http.headers[key]))
				del self._readable_sockets[conn]
				conn.shutdown(socket.SHUT_RD)
				if http and Tracking().task_exists(http):
					Tracking().remove_task(http)
					self.info("Dropped client %s (serial %i) due to an error raised during socket.recv." % (http.remote_ip, http.serial))
			elif conn in self._writeable_sockets:
				self.warn("Socket receive error. Writable socket was in error.")
			elif conn == self._server_socket:
				self.err("Socket receive error. Server socket was in error.")
			elif conn == self._on_reply_socket_read:
				self.err("Socket receive error. on-reply-socket-read socket was in error.")
			elif conn == self._on_reply_socket_write:
				self.err("Socket receive error. on-reply-socket-write socket was in error.")
			else:
				self.info("Connection seemed to be closed and cleaned up already.")
		
	def on_finished_reply(self, conn, reply):
		if conn in self._writeable_sockets:
			del self._writeable_sockets[conn]
			conn.close()
			self.debug('Closed client socket from %s (serial %i).' % (reply.request.http.remote_ip, reply.request.http.serial))
			if Tracking().task_exists(reply.request.http):
				Tracking().remove_task(reply.request.http)
			self.task_done(reply)
		
	def on_socket_error(self, error):
		self.err('Exception: "%s".' % str(error))
		self.err(traceback.format_exc())
		
	def get_http_requests(self):
		completed_list = []
		while len(completed_list) == 0:
			select_error = False
			try:
				self._mutex.acquire()
				rsock = self._get_all_read_sockets()
				wsock = self._get_all_write_sockets()
				self._mutex.release()               
				#
				# If in shutdown-mode AND all tasks have finished - then break loop.
				# Server (that has initiated the shutdown) will catch the return
				# of an empty client HTTP request list and stop the whole process.
				#
				if self._shutdown and Tracking().pending_tasks() == 0 and len(wsock) == 0:
					self.debug('Network is stopping receiveing and sending.')
					break
				#
				# The main select statement.
				#
				self.debug('Select: %4i readers,  %4i writers.' % (len(rsock), len(wsock)))
				rlist, wlist, elist = select.select(rsock, wsock, rsock+wsock, 10)
				
				if self._deadman_filename:
					os.system('touch %s' % self._deadman_filename)
				
				if len(elist):
					self.warn('Select returned non-empty error list and no action is taken!')
			except select.error, e:
				errcode, message = e.args
				if errcode == 4:
					self.warn('Select call interrupt error probably due to SIGTERM')
					break
				else:
					raise e
			except socket.error, e:
				select_error = True
				self.on_socket_error(e)
				for conn in rsock+wsock:
					try:
						select.select([conn], [], [], 0)
					except:
						self.warn('The following socket was in error:', conn)
						if conn in rsock:
							self.warn('Socket was from readable list.')
							for rconn in rsock:
								if rconn == conn:
									self._mutex.acquire()
									http = self._readable_sockets[conn]
									self.warn('Client IP is:', http.remote_ip)
									if Tracking().task_exists(http):
										Tracking().remove_task(http)
									if conn in self._readable_sockets:
										del self._readable_sockets[conn]
									self._mutex.release()
									conn.close()
									self.warn('Found and deleted error socket in read-sockets')
						elif conn in wsock:
							self.warn('socket was from writable list.')
							for wconn in wsock:
								if wconn == conn:
									self._mutex.acquire()
									reply = self._writeable_sockets[conn][0]
									self.warn('Client IP is:', reply.request.http.remote_ip)
									if Tracking().task_exists(reply.request.http):
										Tracking().remove_task(reply.request.http)
									if conn in self._writeable_sockets:
										del self._writeable_sockets[conn]
									self._mutex.release()
									conn.close()
									self.warn('Found and deleted error socket in write-sockets')
						else:
							print 'socket not found in either read or write list!!'
				continue
			# 
			# Read-ready sockets.
			#
			for conn in rlist:
				# 
				# Handle new socket connections.
				# 
				if conn == self._server_socket:
					new_conn, new_addr = self._server_socket.accept()
					if self._client_count == 0:
						self._on_reply_socket_read = new_conn
					if not self._shutdown:
						new_conn.setblocking(0)
						http = HTTPRequest(new_conn, new_addr[0], self._client_count)
						self._client_count += 1
						self._readable_sockets[new_conn] = http
						self.debug('Server got new request from %s (serial = %i).' % (new_addr, http.serial))
					else:
						self.debug('Server is shutting down, ignoring new connection from %s.')
				elif conn == self._on_reply_socket_read:
					self.debug('Reply wake-up notification.')
					self._on_reply_socket_read.recv(_sock_buf_size)
				else:
					#
					# Handle reading from client sockets.
					#
					http = self._readable_sockets[conn]
					try:
						round = http.recv()
						if round == 0:
							if conn.getpeername()[0] == self._server_socket.getsockname()[0]:
								self.debug('Client gone error (serial %i). Probably just an expeceted hang up from a wake-up connection.' % http.serial)
							else:
								self.debug('Client gone error (serial %s). Peer (%s) probably hung up unexpectedly!' % (http.serial, http.remote_ip))
							self.on_error_receive(conn)
						elif round < 0:
							self.debug('(%i) "%s".' % (reply.status, reply.message))
							self.on_error_receive(conn)
							self.add_response(reply)
						if http.is_complete():
							conn.shutdown(socket.SHUT_RD) # Ok, we are done reading request.
							if http.conn in self._readable_sockets:
								del self._readable_sockets[http.conn]
							Tracking().save_http_request(http)
							http.finallize()
							completed_list.append(http)
							self.debug('Request completed, header: %i and body: %i bytes.' % (http.header_size, http.content_length))                           
							if http.body:
								cl = http.content_length
								bl = len(http.body)
								if bl != cl:
									self.warn('HTTP request Content-Length (%i) was not equal to size of body (%i).' % (cl, bl))
					except mamba.http.HTTPErrorResponse, reply:
						self.on_error_receive(conn)
						self.add_response(reply)
						
					except (Exception, RuntimeError), e:
						self.on_error_receive(conn)
						reply = mamba.http.HTTPErrorResponse(mamba.task.ErrorRequest(http), 500, str(e))
						self.add_response(reply)
			#
			# Write-ready sockets.
			# Handle sending server replies to clients.
			#
			for conn in wlist:
				reply, reply_string, reply_sent = self._writeable_sockets[conn]
				try:
					chunk_sent = conn.send(reply_string[reply_sent:])
					reply_sent += chunk_sent
					if chunk_sent > 0 and reply_sent < len(reply_string):
						self._writeable_sockets[conn][2] = reply_sent
					else:
						self.debug('Reply for %i was completely sent to %s.' % (reply.request.http.serial, reply.request.http.remote_ip))
						self.on_finished_reply(conn, reply)
				except socket.error, e:
					errcode, msg = e.args
					if errcode == 104:
						self.warn('Connection to %s was reset by peer.' % reply.request.http.remote_ip)
						self.on_finished_reply(conn, reply)
					else:
						self.err('Socket error while replying: "%s". Sent %i of %i bytes.' % (str(e), reply_sent, len(reply_string)))
						self.on_finished_reply(conn, reply)
				except Exception, e:
					self.err('Exception ignored while sending reply:', str(e))
					self.err(traceback.format_exc())
					self.on_finished_reply(conn, reply)
		return completed_list


_single_internet = None

def Internet():
	global _single_internet
	if not _single_internet:
		_single_internet = CurlInternet()
	return _single_internet


class BaseInternet(mamba.util.Logger):
	
	site_register = {}
	site_log_file = None    
	thread_lock   = threading.Lock()
	
	re_charset      = re.compile("charset=([^ ]+)", re.I)
	re_charset_meta = re.compile("<head[^>]*>.*?<meta http-equiv=\"Content-Type\" content=\"(.+?)\" ?/>.*?</head>", re.I | re.DOTALL)
	re_head_begin   = re.compile("<head[^>]*>", re.I)
	re_base_href    = re.compile("<base href=.+?>", re.I)
		
	
	def __init__(self):
		mamba.util.Logger.__init__(self, "internet", show_debug = True)
		if not _single_internet:
			self.info("Initializing internet download object.")
			if mamba.setup.config() and mamba.setup.config().log.download:
				BaseInternet.site_log_file = open(mamba.setup.config().log.download, "a")
			else:
				BaseInternet.site_log_file = sys.stdout 
		
	def _log_activity(self, url):
		url_info = urlparse.urlsplit(url)
		prot = url_info.scheme
		site = url_info.netloc
		if mamba.setup.config():
			if not mamba.setup.config().log.active:
				return
		try:
			BaseInternet.site_log_file.write("%s  PROTOCOL:  %s  SITE:  %s  PAGE:  %s\n" % (self.now(), prot, site, url))
			BaseInternet.site_log_file.flush()
		except IOError:
			pass
				
	def _fetch(self, url, client=None, proxy_mode=False):
		raise Exception, "_fetch() not implemented in internet download class."
		#return document, status, headers, page_url
	
	def download_raw(self, url, client=None, proxy_mode=False):
		status   = 400
		document = None
		headers  = None
		page_url = None
		BaseInternet.thread_lock.acquire()
		try:
			site = urlparse.urlsplit(url).netloc
			if site:
				self._log_activity(url)
				if site not in BaseInternet.site_register:
					wait = 0
				else:
					if mamba.setup.config():
						min_wait = mamba.setup.config().delays.get_min_wait(site)
					else:
						min_wait = 0
					last_time  = BaseInternet.site_register[site]
					since_last = datetime.datetime.now() - last_time
					if since_last.seconds < min_wait:
						wait = min_wait - since_last.seconds
					else:
						wait = 0
				self.debug('Waiting %f seconds for "%s".' % (wait, site))
				if wait > 0:
					time.sleep(wait)                
				BaseInternet.site_register[site] = datetime.datetime.now()
				#url = url.replace(" ", "%20")
				self.info("Attempting to download URL '%s'" % url)
				document, status, headers, page_url = self._fetch(url, client, proxy_mode)
				self.info("Downloaded page '%s' (status code: %i)" % (page_url, status))
		finally:
			BaseInternet.thread_lock.release()
		return document, status, headers, page_url
				
	def download(self, url, client=None, proxy_mode=False, insert_base=False):
		charset = None
		content_type = None
		content_encoding = None
		document, status, headers, page_url = self.download_raw(url, client, proxy_mode)

		# ======================================================================
		# Determine the character-set-code-page either from the HTTP-headers or
		# if that fails, from the document itself via meta-tags in the HTML
		# header.
		# ======================================================================
		if "Content-Type" in headers:
			content_type = headers["Content-Type"]
			charset_match = BaseInternet.re_charset.search(content_type)
			if charset_match:
				charset = charset_match.group(1).strip().lower()
		if not charset:
			content_type_match = BaseInternet.re_charset_meta.search(document)
			if content_type_match:
				content_type = content_type_match.group(1)
				charset_match = BaseInternet.re_charset.search(content_type)
				if charset_match:
					charset = charset_match.group(1).strip().lower()
		if not charset and content_type and not content_type.lower().startswith("application/"):
			charset = "iso-8859-1"

		# ======================================================================
		# Determine if the content was gzip compressed or not.
		# ======================================================================
		if "Content-Encoding" in headers:
			content_encoding = headers["Content-Encoding"]

		# ======================================================================
		# Unzip the document and remove the 'Content-Encoding: gzip' from the
		# response headers. We compress again if we have to send the document
		# back to the client if that client is accepting gzip compression.
		# We are acting between the client and the server here so we uncompress
		# here to provide the document in text as the return value.
		# ======================================================================
		if not proxy_mode and content_encoding and content_encoding.lower() == "gzip":
			try:
				document = easy_unzip(document)
				del headers["Content-Encoding"]
			except Exception, e:
				self.err("Error while unzipping:", e)
		
		# ======================================================================
		# Insert <base href="..." /> in the <head>...</head>.
		# ======================================================================
		if insert_base:
			match_head_begin = BaseInternet.re_head_begin.search(document)
			if match_head_begin:
				match_base_ref = BaseInternet.re_base_href.search(document, match_head_begin.end(0))
				if not match_base_ref:
					insert = match_head_begin.end(0)
					pre = document[:insert]
					info = urlparse.urlsplit(url)
					href = info.scheme + "://" + info.netloc
					if href[-1] != "\t":
						href += "/"
					base = "<base href=\"%s\" />" % href
					post = document[insert:]
					document = "".join((pre, base.encode("utf8"), post))
		
		# ======================================================================
		# Finally, if some implementation of the BaseInternet class fetches
		# pages as unicode strings we encode the unicode string object into a
		# normal string object (Python versions 2.x).
		# ======================================================================
		if document and not isinstance(document, unicode):
			document = mamba.util.string_to_bytes(document, charset)
		return document, status, headers, page_url, charset


class CurlInternet(BaseInternet):
	
	re_response_line  = re.compile("^HTTP/([0-9]\.[0-9]+) ([0-9]{3}) (.+?)\r?\n", re.I)
	re_double_newline = re.compile("\r?\n\r?\n")
	
	class Curl(mamba.util.Command):
		def __init__(self, url, headers=None):
			cmd = []
			cmd.append("curl --silent --include")
			if not headers:
				 cmd.append("--user-agent 'Mozilla/4.0'")
			if headers:
				for key in headers:
					cmd.append("-H '%s: %s'" % (key, headers[key]))
			cmd.append("'%s'" % url)
			cmd = mamba.util.string_to_bytes(" ".join(cmd), "utf8")
			mamba.util.Command.__init__(self, cmd)

	
	def _fetch(self, url, client=None, proxy_mode=False):
		document = None
		status = 400
		request_headers = HTTPHeader()
		page_url = None
		if client:
			request_headers = HTTPHeader(client.headers)
		server_ip = socket.gethostbyname(socket.gethostname())
		if client:
			if not proxy_mode:
				if "Host" in request_headers and request_headers["Host"].lower().startswith("localhost"):
					del request_headers["Host"]
				if "Accept-Charset" in request_headers:
					del request_headers["Accept-Charset"]
				if "Accept-Encoding" in request_headers:
					del request_headers["Accept-Encoding"]
				request_headers.add("Host", urlparse.urlsplit(url).netloc)
				request_headers.add("Accept-Charset" , "iso-8859-1,utf-8;q=0.7,*;q=0.3")
				request_headers.add("Accept-Encoding", "gzip")
			chain = []
			if "X-Forwarded-For" in request_headers:
				for ip_addr in map(str.strip, request_headers["X-Forwarded-For"].split(",")):
					if ip_addr != client.remote_ip and ip_addr != server_ip:
						chain.append(ip_addr)
				del request_headers["X-Forwarded-For"]
			chain = [server_ip] + chain + [client.remote_ip]
			if chain:
				request_headers["X-Forwarded-For"] = ", ".join(chain)
		exit_code, stdout, stderr = CurlInternet.Curl(url, request_headers).run()
		response_headers = HTTPHeader()
		if exit_code == 0:
			page_url = url
			double_newline = CurlInternet.re_double_newline.search(stdout)
			if double_newline:
				head = stdout[:double_newline.end(0)]
				document = stdout[double_newline.end(0):]
				first = CurlInternet.re_response_line.match(head)
				if first:
					version = first.group(1)
					status  = int(first.group(2))
					reason  = first.group(3)
					header  = head[first.end(0):].strip()
					response_headers.parse(header)
		if "Transfer-Encoding" in response_headers: # Even in case of "proxy_mode"!
			del response_headers["Transfer-Encoding"]
		return document, status, response_headers, page_url
		
class UrlopenInternet(BaseInternet):
	
	class MozillaOpener(urllib.FancyURLopener):
		version = "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_3; en-us) AppleWebKit/531.22.7 (KHTML, like Gecko) Version/4.0.5 Safari/531.22.7"
		def http_error_401(self, url, fp, errcode, errmsg, headers, data=None): return None
		def http_error_402(self, url, fp, errcode, errmsg, headers, data=None): return None
		def http_error_403(self, url, fp, errcode, errmsg, headers, data=None): return None
	
	def __init__(self):
		BaseInternet.__init__(self)
		urllib._urlopener = UrlopenInternet.MozillaOpener()
		
	def _fetch(self, url, client=None):
		url = url.replace(" ", "%20")
		self.info("Attempting to download URL '%s'" % url)
		response = urllib.urlopen(url)
		status   = response.getcode()
		page_url = response.geturl()
		headers  = response.headers.items()
		document = response.read()
		return document, status, headers, page_url


_single_track = None

def Tracking():
	global _single_track
	if not _single_track:
		_single_track = __Track()
	return _single_track


class __Track(mamba.util.Logger):
	
	def __init__(self):
		mamba.util.Logger.__init__(self, "track")
		
		global _single_track
		if _single_track:
			self._thread_lock = _single_track._thread_lock
			self._client_load = _single_track._client_load
			self._total_data  = _single_track._total_data
			self._total_http  = _single_track._total_http
		else:
			self.debug("Instanciating the track module for extended client logging.")
			self._thread_lock  = threading.Lock()
			self._client_load  = {}
			self._total_data   = 0
			self._total_http   = 0
			self._setup_dirs()
			
	def _lock(self):
		self._thread_lock.acquire()
		
	def _release(self):
		self._thread_lock.release()
		
	def _setup_dirs(self):
		if mamba.setup.config().track.active:
			if not os.path.exists(mamba.setup.config().track.logdir):
				os.mkdir(mamba.setup.config().track.logdir)
			if not os.path.exists(mamba.setup.config().track.faildir):
				os.mkdir(mamba.setup.config().track.faildir)
			
	def _get_track_dir(self, ip):
		trackdir = mamba.setup.config().track.logdir + '/' + ip + '/'
		if os.path.exists(trackdir):
			return trackdir
		else:
			if not os.path.exists(trackdir):
				os.mkdir(trackdir)
				self.info('Creating track dir:', trackdir)
			return trackdir
		
	def _get_next_fail_filename(self):
		N = len(glob.glob(mamba.setup.config().track.faildir + '/critical_error_*'))
		if N > 1000:
			raise RuntimeError, 'Too many failure files stored already under: ' + mamba.setup.config().track.faildir
		while True:
			N += 1
			filename = mamba.setup.config().track.faildir + '/critical_error_' + str(N)
			if not os.path.exists(filename):
				break
		return filename
	
	def _delete_oldest_file(self, filename):
		folder = os.path.dirname(filename)
		base   = os.path.basename(filename)
		timestamp, type = base.split('-')
		pattern = folder + '/*-' + type
		#print pattern
		similar_files = glob.glob(pattern)
		similar_files.sort()
		#print similar_files
		while len(similar_files) > max(0, mamba.setup.config().track.max_go_back - 1):
			old_file = similar_files[0]
			del similar_files[0]
			os.remove(old_file)
			self.debug('Deleted old track file "%s"' % old_file)
			
	def _save_track_file(self, ip, filename, data):
		folder = os.path.dirname(filename)
		base   = os.path.basename(filename)
		filename = folder + '/' + datetime.datetime.now().strftime('%d_%m_%Y_%H_%M_%S') + '-' + base
		self._delete_oldest_file(filename)
		f = None
		try:
			f = open(filename, 'w')
			f.write(data)
			f.flush()
		finally:
			if f:
				f.close()
			
	def save_http_request(self, http):
		if mamba.setup.config().track.active:
			try:
				self._lock()
				trackdir = self._get_track_dir(http.remote_ip)
				filename = trackdir + 'client'
				self._save_track_file(http.remote_ip, filename, str(''.join(http.data)))
				self.debug('Saved client HTTP request from', http.remote_ip, 'of', http.bytes_received, 'bytes in', filename)
			finally:
				self._release()
				
	def save_track_file(self, basefilename, data, client_ip):
		if mamba.setup.config().track.active:
			try:
				self._lock()
				trackdir = self._get_track_dir(client_ip)
				filename = trackdir + basefilename
				self._save_track_file(client_ip, filename, data)
				self.debug('Saved %i bytes from %s in track file %s' % (len(data), client_ip, filename))
			finally:
				self._release()
								
	def save_critical_error(self, error_file, exception, http=None):
		if mamba.setup.config().track.active:
			try:
				self._lock()
				filename = self._get_next_fail_filename()
				f = None
				try:
					f = open(filename, 'w')
					if http:
						ip_addr = http.remote_ip
						header  = http.data[:http.header_size]
						f.write('Exception: "%s"\n' % str(exception))
						f.write('-------------------------------------\n')
						f.write('Client IP-addr.: %s\n' % ip_addr)
						f.write('-------------------------------------\n')
						f.write('Client HTTP header\n:')
						f.write('-------------------------------------\n')
						f.write(header)
						f.write('-------------------------------------\n')
					if error_file:
						f.write('Error file content:\n')
						f.write('-------------------------------------\n')
						f.write(error_file)
				finally:
					if f:
						f.close()
			finally:
				self._release()
				
	def get_client_quota_usage(self):
		clients = {}
		try:
			self._lock()
			for ip in self._client_load:
				jobs = []
				used, tasks = self._client_load[ip]
				for serial in tasks:
					size = tasks[serial]
					jobs.append((serial, size))
				clients[ip] = jobs
		finally:
			self._release()
		return clients
			
	def free_total_data(self):
		if mamba.setup.config():
			return mamba.setup.config().http.max_data_total - self._total_data
		else:
			return 0
	
	def free_total_slots(self):
		if mamba.setup.config():
			return mamba.setup.config().http.max_http_total - self._total_http
		else:
			return 0
	
	def used_total_data(self):
		return self._total_data
				
	def used_client_data(self, ip):
		cd = 0
		if ip in self._client_load:
			cd = self._client_load[ip][0]
		return cd
	
	def free_client_data(self, ip):
		if mamba.setup.config():
			cd = self.used_client_data(ip)
			fc = mamba.setup.config().http.max_data_client - cd
			return fc
		else:
			return 0
		
	def free_client_slots(self, ip):
		if mamba.setup.config():
			fs = 0
			max_http = mamba.setup.config().http.max_http_client
			if ip not in self._client_load:
				fs = max_http
			else:
				fs = max_http - len(self._client_load[ip][1])
			return fs
		else:
			return 0
	
	def is_task_appended(self, http):
		r = False
		try:
			self._lock()
			ip     = http.remote_ip
			serial = http.serial
			if ip in self._client_load and serial in self._client_load[ip][1]:
				r = True
		finally:
			self._release()
		return r
		
	def pending_tasks(self):
		return self._total_http
		
	def append_task(self, http):
		try:
			self._lock()
			ip     = http.remote_ip
			serial = http.serial
			size   = http.size()
		
			if ip not in self._client_load:
				self._client_load[ip] = [0, {}]
		
			if serial in self._client_load[ip][1]:
				self.err('HTTP request cannot be added more than once. IP: %s serial: %i' % (ip, serial))
			else:
				if self.free_client_data(ip) < size:
					raise mamba.http.HTTPErrorResponse(mamba.task.ErrorRequest(http), 509, "You have reached your per-client request data limit.")
					
				elif self.free_client_slots(ip) == 0:
					raise mamba.http.HTTPErrorResponse(mamba.task.ErrorRequest(http), 509, "You have submitted too many requests to the server.")
					
				elif self.free_total_data() < size:
					raise mamba.http.HTTPErrorResponse(mamba.task.ErrorRequest(http), 509, "Server too busy. Too much pending data.")
					
				elif self.free_total_slots() == 0:
					raise mamba.http.HTTPErrorResponse(mamba.task.ErrorRequest(http), 509, "Server too busy. Too many pending requests.")
					
				else:
					self._client_load[ip][0]        += size
					self._client_load[ip][1][serial] = size # Task is added to dict.
					self._total_data                += size
					self._total_http                += 1
					self.debug('Appended request %i from %s of %i bytes.' % (serial, ip, size))
		finally:
			self._release()
			
	def task_exists(self, http):
		try:
			self._lock()
			ip     = http.remote_ip
			serial = http.serial
			size   = http.size()
			return ip in self._client_load and serial in self._client_load[ip][1]
		finally:
			self._release()
	
	def remove_task(self, http):
		try:
			self._lock()
			ip     = http.remote_ip
			serial = http.serial
			size   = http.size()
			if ip in self._client_load and serial in self._client_load[ip][1]:
				del self._client_load[ip][1][serial]
				self._client_load[ip][0] -= size
				if self._client_load[ip][0] == 0 and len(self._client_load[ip][1]) == 0:
					del self._client_load[ip]
				self._total_data         -= size
				self._total_http         -= 1
				self.debug('Freed %i bytes for %s.' % (size, ip))
			else:
				self.warn('Cannot remove task from %s (serial %i).' % (ip, serial))
				self.warn('Call came from file "%s" line: %i.' % self.called_from(frames_back=3))
		finally:
			self._release()

	
