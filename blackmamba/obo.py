#!/usr/bin/env python

import re

class Term:
	
	def __init__(self):
		self.id = None
		self.name = None
		self.definition = None
		self.synonyms = set()
		self.parents = set()
		self.children = set()
		
	def __str__(self):
		return "%s ! %s" % (self.id, self.name)
		
	def info(self):
		s = []
		s.append("[Term]")
		s.append("id  : %s" % self.id)
		s.append("name: %s" % self.name)
		s.append("def : %s" % self.definition)
		for x in self.synonyms:
			s.append("synonym: %s" % x)
		for x in self.parents:
			s.append("parent: %s" % x)
		for x in self.children:
			s.append("child: %s" % x)
		s.append("")
		return "\n".join(s)

class Ontology:
	
	TERM     = re.compile("\[Term\]")
	OBSOLETE = re.compile("is_obsolete: true")
	ID       = re.compile("id: +(.+)")
	NAME     = re.compile("name: +(.+)")
	DEF      = re.compile('def: +"(.+)"( +\[.*\])?')
	SYNONYM  = re.compile('synonym: +"(.+)" (.+) \[.*\]')
	IS_A     = re.compile("(is_a: +([^ ]+)|relationship: +part_of +([^ ]+))")
	
	
	def __init__(self, filename=None):
		self.root  = None
		self.terms = {}
		self.child_parent = {}
		if filename:
			self.load(filename)
			
	def add(self, lines):
		term = Term()
		for line in lines:
			if Ontology.OBSOLETE.match(line):
				return
		for line in lines:
			m = Ontology.ID.match(line)
			if m:
				term.id = m.group(1)
				continue
			m = Ontology.NAME.match(line)
			if m:
				term.name = m.group(1)
				term.synonyms.add(term.name)
				continue
			m = Ontology.DEF.match(line)
			if m:
				term.definition = m.group(1)
				continue
			m = Ontology.SYNONYM.match(line)
			if m:
				if m.group(2) not in ("BROAD", "NARROW"):
					term.synonyms.add(m.group(1))
			m = Ontology.IS_A.match(line)
			if m:
				term.parents.add(m.group(2))
		if term.id != None:
			self.terms[term.id] = term

	def load(self, filename):
		buffer = []
		for line in open(filename):
			line = line[:-1]
			if Ontology.TERM.match(line):
				if len(buffer) > 0:
					self.add(buffer)
					buffer = []
			buffer.append(line)
		if len(buffer):
			self.add(buffer)
			buffer = []
		self.root = None
		for id in self.terms:
			term = self.terms[id]
			if len(term.parents) == 0:
				if self.root == None:
					self.root = term
				else:
					print "Inconsistent root!", term.id, term.name
		for cid in self.terms:
			child = self.terms[cid]
			for pid in child.parents:
				parent = self.terms[pid]
				parent.children.add(child)
			tmp = set()
			for pid in child.parents:
				tmp.add(self.terms[pid])
			child.parents = tmp
		
		
if __name__ == '__main__':
	obo = Ontology("/home/purple1/dictionary/doid.obo")
	for id in obo.terms:
		term = obo.terms[id]
		print term.info()