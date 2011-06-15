'''
Created on Jun 14, 2011

@author: jbernard
'''
import cPickle as pickle
import os
import Image as img
from cStringIO import StringIO
import thread

CACHEFILE = 'thumbs.cache'

def resizePic(fn, width, height):
		""" Re-encode the picture at self.count to fit the view. """

		pic = img.open(fn)
		pic.draft('RGB', (width, height))
		if pic.mode == 'P':
			pic = pic.convert()
		filew, fileh = pic.size
		# determine how the file width compares to the view width
		ratio = float(width) / filew
		# and scale the height accordingly
		pheight = fileh * ratio
		pic = pic.resize((int(width), int(pheight)), img.ANTIALIAS)
		out = StringIO()
		pic.save(out, 'JPEG')
		encoded = out.getvalue()
		out.close()
		
		return encoded
	
class ThumbCache:
	def __init__(self, dir, size, width, height):
		self.filename = os.path.join(dir, 'thumbs.cache')
		self.cacheChanged = False
		self.width = width
		self.height = height
		self.lrumap = []
		self.maxSize = size
		self.mutex = thread.allocate_lock()
		
		# try to load the cache file if it exists
		self.cache = {}
		
		if (os.path.exists(self.filename)):
			print "Loading thumbnail cache"
			
			try:
				f = open(self.filename)
			except:
				print "Error opening thumbnail cache file"
			else:
				try:
					self.cache = pickle.load(f)
				except:
					print "Error loading thumbnail cache"
					self.cache = {}
					return
					
			for k in self.cache:
				self.appendMap(k)
			self.adjustMap()
			print str(len(self.cache)) + " thumbnails loaded from cache"
		else:
			print "Cache file does not exist - no thumbnails loaded"
	
	def sortMap(self):
		def cmplru (left, right):
			if (left[0] > right[0]): return 1
			if (left[0] < right[0]): return -1
			return 0
		
		self.lrumap = sorted(self.lrumap, cmp=cmplru)
	
	def adjustMap(self):
		while len(self.lrumap) > self.maxSize:
			(lru, key) = self.lrumap[0]
			del self.cache[key]
			del self.lrumap[0]
		i = 0
		for m in self.lrumap:
			m[0] = i
			i += 1
			
	def appendMap(self, key):		
		self.lrumap.append([self.maxSize, key])
	   
	def addMap(self, key):
		self.appendMap(key)
		self.adjustMap()
	   
	def updateMap(self, key):
		for m in self.lrumap:
			if m[1] == key:
				m[0] = self.maxSize # force to have the highest possible lru value
				break
		self.sortMap()
		self.adjustMap()
		   
	def getImageData(self, filename):
		mt = 0
		try:
			mt = os.path.getmtime(filename)
		except os.error:
			# file does not exist
			return None
		
		self.mutex.acquire()
	   
		if filename in self.cache:
			if self.cache[filename]['mtime'] >= mt:
				# don't load the file - just use the cache
				self.updateMap(filename)
				self.mutex.release()
				return self.cache[filename]['data']
			
			# file is in the cache but out of date
			self.updateMap(filename)
		else:
			# file is not in the cache - add it
			self.cache[filename] = {}
			self.addMap(filename)
			
		# either file is newer than cache
		# or file is NOT yet in the cache
		# load it in either case
		self.cache[filename]['data'] = resizePic(filename, self.width, self.height)
		self.cache[filename]['mtime'] = mt
	  
		self.cacheChanged = True
		
		self.mutex.release()
		return self.cache[filename]['data']
	
	def hasChanged(self):
		return self.cacheChanged
	
	def size(self):
		return len(self.cache)
	
	def __str__(self):
		return str(self.lrumap)
	
	def saveCache(self):
		if self.hasChanged():
			self.mutex.acquire()
			try:
				f = open(self.filename, 'w')
			except:
				print "Error opening thumbnail cache file for write"
			else:
				try:
					pickle.dump(self.cache, f)
				except:
					print "Error saving thumbnail cache"
				else:
					f.close()
					self.cacheChanged = False
			self.mutex.release()
		