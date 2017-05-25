Python API Client for Clio / clio-python-client
===============

[Clio is a case management](www.docketalarm.com) software suite for lawyers that
stores all documents online. This library is a Python API client 
to access Clio's database and documents.

## License / Credits
    Released Under Apache License, Version 2.0
    Copyright 2015 Michael Sander, Docket Alarm, Inc.

Credit: [Docket Alarm is a legal research platform](www.docketalarm.com) that 
provides access to and analytics of United States legal cases. Docket Alarm 
developed and uses this Clio API client to automatically download court filings 
and push them to Clio's document folders. Read more [about the integration
here](https://www.docketalarm.com/clio).
    
## Getting Started
You will need a functioning Clio account. If you do not have one, [you can 
sign up here](http://www.clio.com). Once you sign up, you will need to create a
[Clio Application](http://api-docs.clio.com/v2/#create-a-clio-application), 
after which you will receive a public and private key. To download and run the 
python client, you will  need [Git](https://git-scm.com/downloads) and 
[Python](https://www.python.org/downloads/). Currently only Python version 
2.7 has been tested, but adding support for Python 3 should not be difficult.

### Downloading Source
Run the following commands to download the python client API and run the API
test program:

`git clone https://github.com/docketalarm/clio-python-client.git`

### Getting an Access Token
Clio uses a system called OAuth to generate access tokens. This process allows 
for secure access to Clio without users sharing their passwords, but it is
a multi-step process. It is highly recommended that you read the [Clio API 
documentation on OAuth](http://api-docs.clio.com/v2/#authorization-with-oauth-2-0).
The following code template will help you obtain an access token.

	import clio.client
	# Initialize the OAuth client with the public and private key.
	auth_cc = clio.client.ClioClient.OAuth(<PUBLIC_KEY>, <PRIVATE_KEY>)
	
	# Generate the clio URL used to generate the code.
	url = auth_cc.authorize_url(<REDIRECT_URI>, <STATE>)
	# Now point your browser to "url" and complete the signup process. The
	# browser will redirect to the REDIRECT_URI, adding code as url argument.
	
	# Convert the code into a token.
	result = auth_cc.get_token(<CODE>, <REDIRECT_URI>)
	# You now have an access token.
	print result['access_token']


### Usage

Once you have an access token, the client should be used in the following form:

    import clio.client
	cc = clio.client.ClioClient('<ACCESS_TOKEN>')
	cc.<HTTP_METHOD>.<CLIO_ENDPOINT>(<KEYWORD_ARGS>)

The `HTTP_METHOD`, `CLIO_ENDPOINT`, and `KEYWORD_ARGS` must be specified 
according to the [Clio API client documentation](http://api-docs.clio.com/).

#### Example:

The following example gets a list of matters from Clio, then gets a specific 
matter. It then posts a document to Clio:


	import clio.client
	cc = clio.client.ClioClient(<ACCESS_TOKEN>)

	# Get a list of matters
	matters = cc.GET.matters(offset=5)
	
	# Getting a specific matter. Does not take kwargs, just positional ones.
	matter = cc.GET.matters(1234)

	# Post a document. Note that uploaded data must use the FileUpload object.
	cc.POST.documents( 
		document = {
			'matter' : { 'id' : matters['matters'][0]['id'] },
			'description' : 'my description',
			'document_category' : { 'name' : 'Legal Research' }},
		document_version = {
			'last_modified_at' : '2015-09-03T23:35:32+00:00', 
			'uploaded_data' : cc.FileUpload('document contents', 
                               'document_filename.txt')
		}
	)