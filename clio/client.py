help = """
----------------------------------------------------
Python API Client for Clio

Description: A python API client for the Clio API.

Copyright 2015 Michael Sander, Docket Alarm, Inc.
Released Under Apache License, Version 2.0
----------------------------------------------------

General Usage

	import clio.client
	cc = clio.client.ClioClient('<ACCESS_TOKEN>')
	cc.<HTTP METHOD>.<CLIO_ENDPOINT>(<KEYWORD ARGS>)

Example:

	import clio.client
	cc = clio.client.ClioClient('<ACCESS_TOKEN>')

	# Get a list of matters
	matters = cc.GET.matters(offset=5)
	
	# Getting a specific matter.does not take kwargs, just positional ones.
	matter = cc.GET.matters(1234)

	# Post a document
	cc.POST.documents( 
		document = {
			'matter' : { 'id' : matters['matters'][0]['id'] },
			'description' : 'my description',
			'document_category' : { 'name' : 'Legal Research' }},
		document_version = {
			'last_modified_at' : '2015-09-03T23:35:32+00:00', 
			'uploaded_data' : cc.FileUpload('document text', 'bar.txt')
		}
	)

The client can also assist with obtaining an access token using the code below,
but to learn more about obtaining an access token, read the api documentation.

	import clio.client
	# The client has a separate API for obtaining the an access token.
	auth_cc = clio.client.ClioClient.OAuth(<PUBLIC_KEY>, <PRIVATE_KEY>)
	
	# Get the clio URL used to generate the code.
	url = auth_cc.authorize_url(<REDIRECT_URI>, <STATE>)
	# Now point your browser to this URL and complete the signup process. The
	# browser will redirect to the REDIRECT_URI, adding code as url argument.
	
	# Convert the code into a token.
	result = auth_cc.get_token(<CODE>, <REDIRECT_URI>)
	# You now have an access token.
	print result['access_token']

Further documentation of the API can be found at:
	http://api-docs.clio.com/
"""

import json
import urllib
import urllib2
import datetime
import logging

# This library is required to encode and upload Files.
# https://github.com/JeremyGrosser/python-poster
try:
	from poster.encode import multipart_encode, MultipartParam
except ImportError:
	logging.warning("Cannot import python-poster library, will not be able to "
		"upload documents.\nDownload python-poster: "
		"https://github.com/JeremyGrosser/python-poster")
	multipart_encode, MultipartParam = None, None

################################################################################
# Global API Settings
api = 'https://app.goclio.com/api/v2/'
api_oauth = 'https://app.goclio.com/oauth/'
# Timeout in seconds for contacting Clio.
TIMEOUT = 60
# Set to True to enable debug logging.
DEBUG = False

################################################################################
# The Main API call

class ClioClient(object):
	def __init__(self, access_token):
		'''
		The access token should always be set. If you do not have an access 
		token, use the oauth api below to obtain one.
		'''
		self.access_token = self._to_data(access_token, "access_token")
	
	class FileUpload(object):
		'''
		An object that represents a file to upload, used when crafting API 
		calls to upload files. See example in comments above.
		'''
		def __init__(self, data, filename = "", content_type=""):
			self.data = ClioClient._to_data(data, "data")
			self.filename = ClioClient._to_data(filename, "filename")
			self.content_type = ClioClient._to_data(content_type, "content_type")
	
	@classmethod
	def _to_data(cls, data, data_type = ""):
		'''No unicode can get into the HTTP request, otherwise unicode decode
		errors may be raised. Use this function to find and fix the issues.'''
		if isinstance(data, unicode):
			logging.warning("%s: is in unicode, converting to str"%data_type)
			data = data.encode('utf8')
		if not isinstance(data, str):
			logging.error("%s not returning str: %s"%(data_type, type(data)))
		return data
	
	@property
	def POST(self):
		return self._PropClass(self, "POST")
	
	@property
	def GET(self):
		return self._PropClass(self, "GET")
	
	@property
	def DELETE(self):
		return self._PropClass(self, "DELETE")
	
	@property
	def PUT(self):
		return self._PropClass(self, "PUT")
	
	class OAuth(object):
		'''
		A class that assists with getting OAuth setup with Clio.
		'''
		def __init__(self, public_key, private_key):
			self.public_key = public_key
			self.private_key = private_key
		
		def authorize_url(self, redirect_uri, state = ''):
			'''
			The first step in obtaining an access token. Returns a URL which
			you need to point a browser to complete the clio signup process.
			
			The browser will redirect to redirect_uri and provide a code.
			'''
			return api_oauth + 'authorize?' + urllib.urlencode({
				'response_type' : 'code',
				'client_id' : self.public_key,
				'redirect_uri' : redirect_uri,
				'state' : state or '',
			})
		
		def get_token(self, code, redirect_uri):
			'''
			This method converts the code to an access token.
			'''
			post_args = urllib.urlencode({
				'client_id':     self.public_key,
				'client_secret': self.private_key,
				'grant_type': 'authorization_code',
				'code' : code,
				'redirect_uri' : redirect_uri,
			})
			return json.loads(urllib.urlopen(api_oauth + '/token', 
				data = post_args).read())
	
	class _PropClass(object):
		'''
		Internal class only used to convert properties into functions.
		'''
		def __init__(self, clioclient, method):
			self.clioclient, self.method = clioclient, method
		def __getattr__(self, endpoint):
			def func(*args, **kwargs):
				return self.clioclient._call(endpoint, self.method, 
					*args, **kwargs)
			return func
	
	@classmethod
	def _to_keyvalue(cls, q, _parent_key = None):
		'''
		Internal function that converts dictionaries into key-values.
		'''
		if isinstance(q, (int, str, unicode, cls.FileUpload)):
			return [(_parent_key, q)]
		if isinstance(q, (datetime.datetime)):
			return [(_parent_key, str(q))]
		if isinstance(q, dict):
			key = (lambda k: "%s[%s]"%(_parent_key, k)) if _parent_key \
					else lambda k: k
			# Use sum to flatten each of the lists.
			return sum([cls._to_keyvalue(v, key(k)) 	
				for k, v in q.items()], [])
		raise Exception("Unexpected type: %s"%type(q))
	
	@classmethod
	def urlencode(cls, q):
		return "&".join(["%s=%s"%(k, 
			urllib.quote(v) if isinstance(v, basestring) else v) 
			for k, v in cls._to_keyvalue(q)])
	
	@classmethod
	def multipart(cls, q):
		'''
		Encode a dictionary into multipart encoding.
		'''
		if not MultipartParam or not multipart_encode:
			raise Exception("Cannot encode documents without python-poster")
		def encode_one(k, v):
			if isinstance(v, cls.FileUpload):
				return MultipartParam(k, value = v.data, 
					filename = v.filename, filetype = v.content_type)
			else:
				k = cls._to_data(k, "encode_one k")
				v = cls._to_data(v, "encode_one v")
				return MultipartParam(k, value = v)
		return multipart_encode([encode_one(k, v) 
			for k, v in cls._to_keyvalue(q)])
	
	def deb(self, *args, **kwargs):
		if DEBUG:
			try:
				if args and isinstance(args[0], (str, unicode)):
					args = list(args)
					args[0] = "CLIO %s %s"%(self.access_token, args[0])
				logging.info(*args, **kwargs)
			except Exception as e:
				logging.error("Error with CLIO logging: %s"%repr(e))
	
	def err(self, *args, **kwargs):
		try:
			if args and isinstance(args[0], (str, unicode)):
				args = list(args)
				args[0] = "CLIO %s %s"%(self.access_token, args[0])
			logging.error(*args, **kwargs)
		except Exception as e:
			logging.error("Error with CLIO logging: %s"%repr(e))
	
	def _call(self, endpoint, method="GET", *args, **kwargs):
		'''
		Internal function that does the heavy lifting of calling the Clio API.
		'''
		method = self._to_data(method, "method")
		if method not in ["GET", "POST", "DELETE", "PUT"]:
			raise Exception("Expecting a GET or POST request, not: %s"%method)    
		
		# Prepare the URL and arguments
		url = api + endpoint
		if args:
			url += "/" + "/".join(map(unicode, args))
		self.deb("URL %s: %s\n%s", method, url, kwargs)
		if 'documents' in endpoint:
			if method == "GET":
				urlargs = self.urlencode(kwargs) if kwargs else ""
				req = urllib2.Request(url + "?" + urlargs)
			else:
				# Posted Documents use multipart-form encoded data.
				datagen, headers = self.multipart(kwargs)
				datagen = self._to_data("".join(sorted(datagen)), "datagen")
				req = urllib2.Request(self._to_data(url, 'url'), datagen)
				for k, v in headers.items():
					# We must endcode any unicode values into bytes.
					req.add_header(
						self._to_data(k, "call k"), 
						self._to_data(v, "call v"))
		else:
			# Everything else uses JSON
			if kwargs:
				jsonargs = json.dumps(kwargs)
				self.deb("JSON args:\n%s", jsonargs)
				req = urllib2.Request(url, jsonargs)
				req.add_header('Content-Type', 'application/json')
			else:
				req = urllib2.Request(url)
		
		# A well known hack to get urllib to return the correct HTTP method.
		req.get_method = lambda: method
		# Add our authorization token.
		req.add_header('Authorization', 'Bearer ' + self.access_token)
		
		# Make the call
		try:
			response = urllib2.urlopen(req, timeout = TIMEOUT)
		except urllib2.HTTPError as e:
			out = e.fp.read()
			self.err("Call Error: %s %s %s\n%s %s", method, url, kwargs,	
				e.code, out)
			if e.code in [400, 409]:
				# Return error messages due to malformed requests.
				try:
					json.loads(out)
				except:
					# Occasionally error 400s are returned as HTML, 
					# in which case, just raise the original error.
					raise e
			else:
				raise
		else:
			# Success read the results.
			out = response.read()
			self.deb("Success: %s", out)
		try:
			# The results are in JSON, read them.
			out = json.loads(out)
		except:
			raise Exception("Not JSON: " + out)    
		
		return out

if __name__ == "__main__":
	print help
