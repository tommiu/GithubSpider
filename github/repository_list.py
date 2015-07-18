'''
Created on Jul 17, 2015

@author: tommi
'''
import json

class RepositoryList(object):
    '''
    classdocs
    '''

    def __init__(self, url, etag, repos="[]", next_url=None):
        '''
        Constructor
        '''
        if not url:
            raise ValueError("Parameter '%s' not specified." % ("url"))
        if not etag:
            raise ValueError("Parameter '%s' not specified." % ("etag"))
        
        self.url   = url
        self.etag  = etag
        self.next_url = next_url
        
        self.setRepos(repos)
    
    def __iadd__(self, other):
        self.repos.append(other)
    
    def __str__(self):
        return json.dumps(self.repos)
    
    def getURL(self):
        return self.url
    
    def setURL(self, url):
        self.url = url
    
    def getEtag(self):
        return self.etag
    
    def setETag(self, etag):
        self.etag = etag
    
    def getNextURL(self):
        return self.next_url
    
    def setNextURL(self, next_url):
        self.next_url = next_url
        
    def setRepos(self, repos):
        if isinstance(repos, basestring):
            # 'repos' is given as a string.
            self.repos = json.loads(repos)

        elif isinstance(repos, list):
            # 'repos' is given as a list (=already json-decoded).
            self.repos = repos

        else:
            raise Exception("Given value for 'repos' is not valid: '%s'." % (
                                                                    repos
                                                                    ))