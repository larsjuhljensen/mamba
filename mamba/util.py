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
import time
import datetime
import threading
import inspect
from subprocess import Popen, PIPE

import mamba.setup

def string_to_bytes(text, charset="utf8"):
	if isinstance(text, unicode):
		byte_array = None
		for tolerance in ("strict", "replace", "ignore"):
			try:
				return text.encode(charset, tolerance)
			except UnicodeEncodeError:
				pass
		raise Exception, "Unable to convert unicode string to a byte-array!"
	else:
		return text

def init_log(server_log_filename):
	Logger.LOG_FILE = open(server_log_filename, "a")


class Logger:

	SEEN = {}
	LOG_FILE = sys.stdout
	RE_SHORT_NAME = re.compile("^(?P<queue>.+?)(_(?P<pool>.+?)_(?P<number>\d+))?$", re.IGNORECASE)
	
	def __init__(self, name, show_debug = True, log_stream = None):
		if not log_stream:
			self.file = Logger.LOG_FILE
		else:
			self.file = log_stream
		self.name  = name
		short_name = Logger.RE_SHORT_NAME.search(self.name).group('queue')
		configured_names = {}
		if mamba.setup.config():
			configured_names = mamba.setup.config().debug.names
		if short_name in configured_names:
			show = configured_names[short_name]
			self.show_debug = show
			if show:
				if short_name not in Logger.SEEN:
					Logger.SEEN[short_name] = 1
					self.info('Show debug information for:', short_name)
		else:
			self.show_debug = 0
		self._timers = []
		self._frames_back = 2
		
	def set_frames_back(self, frames_back):
		self._frames_back = frames_back
	
	def get_frames_back(self):
		return self._frames_back
		
	def now(self):
		return datetime.datetime.now().strftime('%d%m%Y %H:%M:%S.%f')
		
	def _format(self, kind, call_file, call_line, text):
		name = None
		if len(self.name) > 8:
			name = self.name[:4] + ".." + self.name[-1]
		else:
			name = self.name
		filename = None
		if len(call_file) > 8:
			filename = call_file[:4] + ".." + call_file[-1]
		else:
			filename = call_file
		place = "%s{%s,%i}" % (name, filename, call_line)
		return str('%s\t%s\t%s\t%s\n' % (self.now(), place, kind, text))
		
		
	def called_from(self, frames_back=2):
		if frames_back < 1:
			raise RuntimeError, 'Irrelevant to go less than 2 frames back on stack.'
		caller_frame = inspect.currentframe().f_back
		for i in range(frames_back-1):
			caller_frame = caller_frame.f_back
		line = caller_frame.f_lineno
		file = os.path.basename(inspect.getfile(caller_frame))
		return file, line
		
	def info(self, *args):
		text = ' '.join([str(args[i]) for i in range(len(args))])
		call_file, call_line = self.called_from(self._frames_back)
		out = self._format("Info", call_file, call_line, text)
		try:
			sys.stdout.write(out)
			sys.stdout.flush()
		except IOError:
			pass
		if self.file != sys.stdout and mamba.setup.config().log.active:
			self.file.write(out)
			self.file.flush()
		
	def err(self, *args):
		text = ' '.join([str(args[i]) for i in range(len(args))])
		call_file, call_line = self.called_from(self._frames_back)
		out = self._format("Err", call_file, call_line, text)
		try:
			sys.stdout.write(out)
			sys.stdout.flush()
		except IOError:
			pass
		if self.file != sys.stdout and mamba.setup.config().log.active:
			self.file.write(out)
			self.file.flush()
		
	def warn(self, *args):
		text = ' '.join([str(args[i]) for i in range(len(args))])
		call_file, call_line = self.called_from(self._frames_back)
		out = self._format("Warn", call_file, call_line, text)
		try:
			sys.stdout.write(out)
			sys.stdout.flush()
		except IOError:
			pass
		if self.file != sys.stdout and mamba.setup.config().log.active:
			self.file.write(out)
			self.file.flush()
		
	def debug(self, *args):
		if not self.show_debug:
			return
		text = ' '.join([str(args[i]) for i in range(len(args))])
		call_file, call_line = self.called_from(self._frames_back)
		out = self._format("Debug", call_file, call_line, text)
		try:
			sys.stdout.write(out)
			sys.stdout.flush()
		except IOError:
			pass
		if self.file != sys.stdout and mamba.setup.config().log.active:
			self.file.write(out)
			self.file.flush()
				
	def timer_start(self, watched_operation, show = False):
		if not mamba.setup.config() or not mamba.setup.config().debug.timing:
			return
		now = datetime.datetime.now()
		self._timers.append((watched_operation, now))
		if show:
			call_file, call_line = self.called_from(self._frames_back)
			out = str('%s [Timer]  %-16s %10s %3i [Started] [Operation]  %s\n' % (self.now(), self.name, call_file, call_line, watched_operation))
			try:
				sys.stdout.write(out)
				sys.stdout.flush()
			except IOError:
				pass
			if self.file != sys.stdout and mamba.setup.config().log.active:
				self.file.write(out)
				self.file.flush()
		
	def timer_stop(self):
		if not mamba.setup.config() or not mamba.setup.config().debug.timing:
			return
		#
		# Pop the last timer inserted and return the difference
		# between that earlier timer and now.
		# Also, we delete the last timer popped from the 'stack'.
		#
		watched_operation, latest = self._timers[-1]
		dT = datetime.datetime.now() - latest
		#
		# Remove timer.
		#
		self._timers[-1] = None
		del self._timers[-1]
		#
		# Print message
		#
		call_file, call_line = self.called_from(self._frames_back)
		out = str('%s [Timer]  %-16s %10s %3i [Elapsed: %s] [Operation]  %s\n' % (self.now(), self.name, call_file, call_line, str(dT), watched_operation))
		try:
			sys.stdout.write(out)
			sys.stdout.flush()
		except IOError:
			pass
		if self.file != sys.stdout and mamba.setup.config().log.active:
			self.file.write(out)
			self.file.flush()
		return dT
	
	def flush_timers(self):
		if len(self._timers) > 0:
			self.war('Uuuuups! There were unexpected non-closed timers left!')
		self._timers = []


def _get_process_memory_usage(size="rss"):
	now = datetime.datetime.now().strftime("%a-%d-%b-%Y %H:%M:%S")
	return now, int(os.popen("ps -p %d -o %s | tail -1" % (os.getpid(), size)).read())


class ProcessWatcher(threading.Thread, Logger):
	
	def __init__(self, server):
		threading.Thread.__init__(self)
		Logger.__init__(self, "stat", show_debug = False)
		self.setName("Stat")
		self.daemon = True
		self._server = server
		activated = mamba.setup.config().watchdog.active
		scan_interval = mamba.setup.config().watchdog.periodicity
		self._quit = (not activated) or (scan_interval < 0)
		self._wait_con = threading.Condition()
		self._log_file = None
		if not self._quit:
			filename = mamba.setup.config().watchdog.memory_log
			if filename and len(filename):
				self._log_file = open(filename, "w")
				self.info("Watchdog created memory log file %s scanning every %i." % (filename, scan_interval))
		else:
			self.info("Memory logging disabled.")
		
	def stop(self):
		self._quit = True
		self._wait_con.acquire()
		self._wait_con.notify()
		self._wait_con.release()
		
	def run(self):
		if self._quit:
			return
		while not self._quit:
			try:
				self._wait_con.acquire()
				self._wait_con.wait(mamba.setup.config().watchdog.periodicity)
				self._wait_con.release()
				if self._quit:
					break
				if self._log_file:
					now, rss = _get_process_memory_usage()
					print >> self._log_file, now,
					print >> self._log_file, "rss/memory: %i" % (rss),
					print >> self._log_file, "threads: %i queues:" % (threading.active_count()),
					for queue_name in self._server.get_queue_names():
						queue = self._server.get_queue(queue_name)
						print >> self._log_file, "%s : %i " % (queue_name, queue.qsize()),
					print >> self._log_file
					self._log_file.flush()
				for pool in self._server.get_thread_pools():
					pool.renew_dead_threads()
			except RuntimeError, e:
				self.err(e)
				self.err("Failed to get data from ps. Stopping the watchdog thread.")
				break
		if self._log_file:
			self._log_file.flush()
			self._log_file.close()
		self.info("Watchdog thread is Stopping.")


class LogData:
	
	def __init__(self):
		self.log_lines = []
		self.response_ok = []
		self.response_errors = []
		self.warnings_and_errors = []
		self.ip_count = {}
		self.ip_action = {}
		self.ip_error = {}
		
	def _read_server_log(self):
		if mamba.setup.config().log.server != None:
			if os.path.exists(mamba.setup.config().log.server):
				tmpf = "/dev/shm/server.log.tail"
				os.system("tail -100 %s > %s" % (mamba.setup.config().log.server, tmpf))
				self.log_lines = map(lambda s: s.strip(), open(tmpf).readlines())
				os.remove(tmpf)
		
	def load(self):
		self._read_server_log()
		for logline in self.log_lines:
			f = logline.split()
			if len(f) > 3:
				timestamp = f[0] + " " + f[1]
				timestamp = timestamp.strip()
				try:
					timestamp = datetime.datetime.strptime(timestamp, "%a-%d-%b-%Y %H:%M:%S")
					ip = f[3]
					ip = ".".join(ip.split(".")[:2])
					if f[2] == "[Client]":
						action = f[8]
						status = f[10]
						reason = " ".join(f[11:])
						if ip not in self.ip_count:
							self.ip_count[ip] = 1
						else:
							self.ip_count[ip] += 1
						if (ip, action) not in self.ip_action:
							self.ip_action[(ip, action)] = 1
						else:
							self.ip_action[(ip, action)] += 1
						if ip not in self.ip_error:
							self.ip_error[ip] = 0
						if status not in ("200", "303"):
							self.ip_error[ip] += 1
							self.response_errors.append((timestamp, ip, status, reason))
						else:
							self.response_ok.append((timestamp, ip, status, reason))
					elif f[2] in "[Err] [War]":
						error = ' '.join(f[2:])
						self.warnings_and_errors.append((timestamp, error))
				except ValueError:
					pass
				except TypeError:
					pass
		self.response_errors.sort()
		self.response_errors.reverse()
		self.warnings_and_errors.sort()
		self.warnings_and_errors.reverse()


def begin_status_html(service):
	doc = []
	doc.append('<HTML>')
	doc.append('  <HEAD>')
	doc.append('    <TITLE>Process and queue status of the Reflect service</TITLE>')
	doc.append('    <META http-equiv="Content-Type" content="text/html; charset=ISO-8859-1" />')
	doc.append('    <style type="text/css">')
	doc.append('	  body  {font-family:Times; color:black; font-size:normal}')
	doc.append('	  table {font-family:Courier; color:black; font-size:small}')
	doc.append('    </style>')
	doc.append('  </HEAD>')
	doc.append('<BODY>')
	doc.append('<CENTER>')
	doc.append('<H1>Process</H1>')
	now, vsz = _get_process_memory_usage()
	doc.append('<table cellpadding="2" cellspacing="2" width="50%">')
	doc.append('<tr>')
	doc.append('<td bgcolor="#D3D3D3"><strong>Resource</strong></td>')
	doc.append('<td bgcolor="#D3D3D3"><strong>Usage</strong></td>')
	doc.append('</tr>')
	doc.append(str('<tr><td>Memory usage</td><td> %.1f MB</td></tr>' % (float(vsz)/1000)))
	tmp = []
	for queue_name in service.get_queue_names():
		queue  = service.get_queue(queue_name)
		number = len(tmp)+1
		tmp.append((number, queue_name, queue.qsize()))
	for number, queue_name, qsize in sorted(tmp):
		doc.append('<tr><td>Queue %i: "<B>%s</B>"</td><td>%i</td></tr>' % (number, queue_name, qsize))
	del tmp
	doc.append('<tr><td>Total active threads</td><td>' + str(threading.active_count()) + '</td></tr>')
	doc.append('</table>')
	doc.append('<P>')
	doc.append('<H1>Threads</H1>')
	doc.append('<table cellpadding="2" cellspacing="2" width="80%">')
	doc.append('<tr>')
	doc.append('<td bgcolor="#D3D3D3"><strong>Thread pool</strong></td>')
	doc.append('<td bgcolor="#D3D3D3"><strong>Task queue</strong></td>')
	doc.append('<td bgcolor="#D3D3D3"><strong>Threads</strong></td>')
	doc.append('<td bgcolor="#D3D3D3"><strong>Restarts</strong></td>')
	for pool in service._pools:
		def_threads   = len(pool.worker_threads)
		alive_threads = 0
		restarts      = max(map(lambda a: a.number, pool.worker_threads)) - def_threads
		for thread in pool.worker_threads:
			if thread.isAlive():
				alive_threads += 1
		if restarts == 0:
			doc.append('<tr><td>%s</td><td>"<B>%s</B>"</td><td>%i</td><td bgcolor="#F5F5F5">None</td></tr>' % (pool.name, pool.queue_name, def_threads))
		else:
			doc.append('<tr><td>%s</td><td>"<B>%s</B>"</td><td>%i</td><td bgcolor="#990033">%i threads has failed!!</td></tr>' % (pool.name, pool.queue_name, def_threads, restarts))
	doc.append('</tr>')
	doc.append('</table>')
	doc.append('<P>')
	doc.append('<HR>')
	return doc

def _finalize_status_html(doc):
	doc.append('</CENTER>')
	doc.append('</BODY>')
	doc.append('</HTML>')
	
def get_simple_stauts_html(service):
	doc = begin_status_html(service)
	_finalize_status_html(doc)
	return '\n'.join(doc)

def get_complete_status_html(service):
	doc = begin_status_html(service)
	doc.append('<H1>Client Quota</H1>')
	doc.append('The server controls how many pending jobs and how much data clients can send to the server.')
	client_quota = mamba.http.Tracking().get_client_quota_usage()
	for ip in client_quota:
		jobs = client_quota[ip]
		jobs.sort()
		doc.append('<P>Client %s has %i jobs pending:</P>' % (ip, len(jobs)))
		for serial, size in jobs:
			doc.append('Serial: %6i  bytes: %7i.<BR>' % (serial, size))
		doc.append('<P>')
	doc.append('<HR>')	
	log = LogData()
	log.load()
	if len(log.log_lines):
		doc.append('<H2>Raw server log - last 100 lines</H2>')
		doc.append('<table cellpadding="2" cellspacing="2" width="100%">')
		doc.append('<tr>')
		doc.append('<td bgcolor="#D3D3D3">Line</td>')
		doc.append('<td bgcolor="#D3D3D3">Log file</td>')
		for i in range(1,min(100, len(log.log_lines))):
			doc.append('<tr><td>' + str(i) + '</td><td><PRE>' + log.log_lines[-i] + '</PRE></td></tr>')
		doc.append('</table>')
		doc.append('<p>')	
	_finalize_status_html(doc)
	return '\n'.join(doc)
	

class Command:
	
	def __init__(self, command_script):
		self.command_script = command_script
		
	def run(self):
		script = Popen(self.command_script, stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
		script_stdout, script_stderr = script.communicate()
		return script.returncode, script_stdout, script_stderr


class Wget(Command):
	
	def __init__(self, url):
		cmd = []
		cmd.append("wget")
		cmd.append("--user-agent='Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.6; en-US; rv:1.9.2) Gecko/20100115 Firefox/3.6'")
		cmd.append("--header='Accept-Language: en-us,en;q=0.5'")
		cmd.append("--header='Accept-Charset: utf-8'")
		cmd.append("-O -")
		cmd.append("'" + url + "'")		
		Command.__init__(self, " ".join(cmd))


class FileCommand(Command):
	
	def __init__(self, filename):
		Command.__init__(self, "file --brief --mime-type --mime-encoding %s" % filename)


class MimeTypes:
	
	CACHE = {}
	TYPE_ENCODING = re.compile("([^;]+); charset=(.+)", re.I)
	EXTENSIONS = {".txt" : "text/plain",
				  ".tsv" : "text/plain",
				  ".csv" : "text/plain",
				  ".pdf" : "application/pdf",
				  ".gz"  : "application/x-gzip",
				  ".xls" : "application/vnd.ms-office",
				  ".ico" : "image/x-icon",
				  ".gif" : "image/gif",
				  ".css" : "text/css",
				  ".html": "text/html",
				  ".htm" : "text/html",
				  ".js"  : "text/javascript"}
	
	@staticmethod
	def guess_type(filename):
		if filename in MimeTypes.CACHE:
			return MimeTypes.CACHE[filename]
			
		mime_type     = "text/plain"
		mime_encoding = "us-ascii"
		
		extension = os.path.splitext(filename)[1].lower()
		
		if extension in MimeTypes.EXTENSIONS:
			mime_type = MimeTypes.EXTENSIONS[extension]
			
		xcode, stdout, stderr = FileCommand(filename).run()
		if xcode == 0 and stdout and not stderr:
			match = MimeTypes.TYPE_ENCODING.match(stdout.rstrip())
			if not mime_type:
				mime_type = match.group(1)
			mime_encoding = match.group(2)
		
		MimeTypes.CACHE[filename] = (mime_type, mime_encoding)

		return mime_type, mime_encoding
		
