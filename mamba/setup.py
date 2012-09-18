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
import ConfigParser


_single_config = None

def config(configuration = None):
	global _single_config
	if configuration and not _single_config:
		_single_config = configuration
		import mamba.util
		if _single_config.log.active:
			mamba.util.init_log(_single_config.log.server)
	return _single_config

def config_is_true(text):
	return str(text).lower() in ("1", "true", "on", "y","yes")


class Configuration:
	
	class Server:
		
		def __init__(self):
			self.host          = "localhost"
			self.port          = 8080
			self.version       = "1.0"
			self.wait_on_port  = False
			self.auto_restart  = False
			self.plugins       = [os.path.abspath("./")]
			self.user_cookie   = os.path.basename(self.plugins[-1]) + "_UUID"
			self.user_database = None
			self.www_dir       = os.path.abspath("./www")
			
		def from_config(self, config):
			try:
				for name, value in config.items("SERVER"):
					name = name.lower()
					if name == 'host':
						self.host = value
					elif name == 'port':
						self.port = int(value)
					elif name == 'version':
						self.version = value
					elif name == 'wait_on_port':
						self.wait_on_port = config_is_true(value)
					elif name == 'auto_restart':
						self.auto_restart = config_is_true(value)
					elif name == 'plugins':
						self.plugins = map(os.path.abspath, map(str.strip, value.split(';')))
						self.user_cookie = os.path.basename(self.plugins[-1]) + "_UUID"
					elif name == 'user_database':
						self.user_database = value
					elif name == "www_dir":
						self.www_dir = os.path.abspath(value)
					else:
						sys.stderr.write('Unknown config parameter "%s" in section [SERVER].\n' % name)
			except ConfigParser.NoSectionError:
				pass
	
	class Security:
		
		def __init__(self):
			self.password = '32f7222026696f30787889194dee83e5' # The MD5 key for password 'Eclipse'.
			self.trusted = '127.0.0.1'
		
		def from_config(self, config):
			try:
				for name, value in config.items('SECURITY'):
					setattr(self, name, value)
			except ConfigParser.NoSectionError:
				pass
			
	class OtherServers:
		
		def __init__(self):
			self.servers = []
			
		def from_config(self, config):
			try:
				for server_name in config.options('OTHER-SERVERS'):
					server_url = config.get('OTHER-SERVERS', server_name)
					self.servers.append(server_url)
			except ConfigParser.NoSectionError:
				pass
								
	class ThreadPool:
		
		def __init__(self, pool_name, queue_name=None, threads=1, parameters={}):
			self.name    = pool_name
			self.queue   = queue_name
			self.threads = threads
			self.params  = parameters
		
		def initialize(self, options, globals):
			self.params = {}
			for key in globals:
				self.params[key] = globals[key]
			for item in map(str.strip, options.split(";")):
				if item:
					units = item.strip().split("=")
					if len(units) and units[-1] == "":
						del units[-1]
					if len(units) == 2:
						key, value = item.strip().split("=")
						if key == "queue":
							self.queue = value
						elif key == "threads":
							self.threads = int(value)
						else:
							if key in globals:
								print "[INIT]  Warning! Thread pool '%s' overwrites [GLOBALS] parameter '%s' from '%s' to '%s'" % (self.name, key, globals, value)
							self.params[key] = value
				
	class Http:
		
		def __init__(self):
			self.commands        = 'GET POST'
			self.max_wait        = 5
			self.max_msg_header  = 4096
			self.max_msg_content = 10E6
			self.max_data_total  = 1000E6
			self.max_data_client = 100E6
			self.max_http_total  = 1000
			self.max_http_client = 16
			self.error_details   = False
			
		def from_config(self, config):
			try:
				for name, value in config.items('HTTP'):
					name = name.lower()
					if name == 'command':
						self.commands = value
					elif name == 'max_wait':
						self.max_wait = value
					elif name == 'max_msg_header':
						self.max_msg_header = value
					elif name == 'max_msg_content':
						self.max_msg_content = value
					elif name == 'max_data_total':
						self.max_data_total = value
					elif name == 'max_data_client':
						self.max_data_client = value
					elif name == 'max_http_total':
						self.max_http_total = value
					elif name == 'max_http_client':
						self.max_http_client = value
					elif name == 'error_details':
						self.error_details = config_is_true(value)
			except ConfigParser.NoSectionError:
				pass
			
	class Debug:
		
		def __init__(self):
			self.timing = False
			self.names  = {}
			
		def from_config(self, config):
			try:
				for option in config.options('SHOW-DEBUG'):
					name = option
					self.names[name] = int(config.get('SHOW-DEBUG', name))
					if name.lower() == 'timing':
						self.timing = int(config.get('SHOW-DEBUG', name))
			except ConfigParser.NoSectionError:
				pass
			
	class Log:
		
		def __init__(self):
			self.active     = False
			self.logdir     = None
			self.server     = None
			self.download   = None
			
		def from_config(self, config):
			try:
				for name, value in config.items('LOG'):
					name = name.lower()
					if name == 'active':
						self.active = config_is_true(value)
					elif name == 'logdir':
						if not os.path.exists(value):
							raise Exception, 'Log dir "%s" does not exist' % value
						self.logdir = value
					elif name == 'server':
						self.server = value
					elif name == 'download':
						self.download = value
			except ConfigParser.NoSectionError:
				pass
			if self.logdir:
				if self.server:
					self.server = os.path.join(self.logdir, self.server)
				if self.download:
					self.download = os.path.join(self.logdir, self.download)
			
	class Watchdog:
		
		def __init__(self):
			self.active        = True
			self.renew_threads = True
			self.memory_log    = None
			self.periodicity   = 10
			
		def from_config(self, config):
			try:
				for name, value in config.items('WATCHDOG'):
					name = name.lower()
					if name == 'active':
						self.active = config_is_true(value)
					elif name == 'memory_log':
						self.memory_log = value
					elif name == 'periodicity':
						self.periodicity = int(value)
			except ConfigParser.NoSectionError:
				pass
			
	class Track:
		
		def __init__(self):
			self.active      = False
			self.logdir      = None
			self.max_go_back = 3
			self.faildir     = None
			
		def from_config(self, config):
			try:
				for name, value in config.items('TRACK'):
					name = name.lower()
					if name == 'active':
						self.active = config_is_true(value)
					elif name == 'logdir':
						self.logdir = value
					elif name == 'max_go_back':
						self.max_go_back = int(value)
					elif name == 'faildir':
						self.faildir = value
			except ConfigParser.NoSectionError:
				pass
			
	class Delays:
		
		def __init__(self):
			self.names = {}
			self.names["*"] = 1
			
		def from_config(self, config):
			try:
				for name in config.options("DELAYS"):
					delay = float(config.get("DELAYS", name))
					self.names[name] = delay
			except ConfigParser.NoSectionError:
				pass
				
		def get_min_wait(self, resource):
			if resource == None:
				return 0
			elif resource in self.names:
				return self.names[resource]
			else:
				return self.names["*"]
				
				
	def __init__(self, ini_file = None):
		self.ini_file       = ini_file
		self.queues         = {}
		self.globals        = {}
		self.sections       = {}
		self.user_settings  = {}
		self.plugins        = {}
		self.thread_pools   = {}
		
		self.server         = Configuration.Server()
		self.security       = Configuration.Security()
		self.other_servers  = Configuration.OtherServers()
		self.delays         = Configuration.Delays()
		self.http           = Configuration.Http()
		self.debug          = Configuration.Debug()
		self.log            = Configuration.Log()
		self.watchdog       = Configuration.Watchdog()
		self.track          = Configuration.Track()
				
		global _single_config
		if _single_config:
			raise RuntimeError, 'The Core.Setup.Configuration class is a singleton. You cannot instantiate it again.'
		else:
			if ini_file and not os.path.exists(ini_file):
				print '[INIT]  Error: Config. file %s did not exist.' % ini_file
			else:
				config = ConfigParser.ConfigParser()
				if ini_file:
					#print '[INIT]  Reading configuration file', ini_file
					config.read(ini_file)
				#else:
				#	print '[INIT]  No .ini file specified, using default settings.'
					
				self.server.from_config(config)
				self.security.from_config(config)
				self.other_servers.from_config(config)
				self.delays.from_config(config)
				self.http.from_config(config)
				self.debug.from_config(config)
				self.log.from_config(config)
				self.watchdog.from_config(config)
				self.track.from_config(config)
				
				try:
					for param in config.options("GLOBALS"):
						self.globals[param] = config.get("GLOBALS", param)
				except ConfigParser.NoSectionError:
					pass
				
				try:
					for queue_name in config.options("QUEUES"):
						type    = None
						threads = 0
						units = config.get("QUEUES", queue_name).split(";")
						if len(units) and units[-1] == "":
							del units[-1]
						if not units:
							raise Exception, "Queue defined without any declaration of queue type (fifo or priority) as a minimum."
						elif len(units) == 1:
							type = units[0]
						elif len(units) == 2:
							type, threads = units[0], int(units[1].split("=")[1].strip())
						else:
							raise Exception, "Too many values (separated by ';') found in definition of queue '%s'." % queue_name
						self.queues[queue_name] = type
						if threads:
							if queue_name not in self.thread_pools:
								self.thread_pools[queue_name] = []
							pool = Configuration.ThreadPool(queue_name, queue_name, threads)
							pool.initialize(config.get("QUEUES", queue_name), self.globals)
							self.thread_pools[queue_name].append(pool)
				except ConfigParser.NoSectionError:
					pass
					
				try:
					for param in config.options("USER-SETTINGS"):
						self.user_settings[param] = config.get("USER-SETTINGS", param)
				except ConfigParser.NoSectionError:
					pass
				
				try:
					for pool_name in config.options("THREAD-POOLS"):
						pool = Configuration.ThreadPool(pool_name)
						pool.initialize(config.get("THREAD-POOLS", pool.name), self.globals)                            
						if pool.queue_name not in self.queues and pool.queue_name.lower() != "main":
							raise Exception, "Thread pool '%s' mentions queue '%s' which is not found under the [QUEUES] section." % (pool.name, pool.queue_name)
						if pool.queue_name not in self.thread_pools:
							self.thread_pools[queue_name] = []
						self.thread_pools[queue_name].append(pool)
				except ConfigParser.NoSectionError:
					pass
					
				for section in config.sections():
					self.sections[section] = {}
					for option in config.options(section):
						self.sections[section][option] = config.get(section, option)
				
				if "main" not in self.thread_pools:
					params  = {}
					for key in self.globals:
						params[key] = self.globals[key]
					self.thread_pools["main"] = [Configuration.ThreadPool("main", "main", 1, params)]
					print "[INIT]  No queues defined, creating 'main' with one worker."
