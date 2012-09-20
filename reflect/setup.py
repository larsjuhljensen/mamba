#
# Configure the Core and the application specific stuff.
# For the Reflect project this means to load the default
# CSS styles from the database mentioned in the .ini file.
# Applications subclass mamba.setup.Configuration class
# and does whatever they need to read additionally from the
# same .ini file.
#

import re
import sys
import mamba.setup
import tagger.tagger


class Setup(mamba.setup.Configuration):

	def __init__(self, ini_file):
		mamba.setup.Configuration.__init__(self, ini_file)
		sys.setcheckinterval(10000)
		styles = {}
		for priority in self.sections['styles']:
			styles[int(priority)] = self.sections['styles'][priority]
		types = {}
		for priority in self.sections['types']:
			types[priority] = lambda x: evail(self.sections['types'][priority])
		print '[INIT]  Loading tagger ...'
		self.tagger = tagger.tagger.Tagger()
		self.tagger.SetStyles(styles, types)
		self.tagger.LoadHeaders(self.globals['java_scripts'])
		self.tagger.LoadNames(self.globals['entities_file'], self.globals['names_file'])
		self.tagger.LoadGlobal(self.globals['global_file'])
		self.tagger.LoadLocal(self.globals['local_file'])
