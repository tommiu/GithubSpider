'''
Created on Jul 17, 2015

@author: Tommi Unruh
'''

import json
from github.exceptions import *

class Repository(object):
    """
    Class representing a repository from Github.
    """

    def __init__(self, _dict):
        '''
        Constructor
        '''
        if isinstance(_dict, basestring):
            # '_dict' is given as a string.
            self._dict = json.loads(_dict)

        elif isinstance(_dict, dict):
            # '_dict' is given as a dict (=already json-decoded).
            self._dict = _dict
            
        else:
            raise Exception("Given value for '_dict' is not valid: '%s'." % (
                                                                    _dict
                                                                    ))

    def filter(self, _filter):
        """
        If all key,values match, return True. False otherwise.
        """
        for key in _filter:
            if key in self._dict:
                    if (
                    str(self._dict[key]).lower() != str(_filter[key]).lower()
                    ):
                        return False
            
            else:
                return False
        
        return True
    
    def __str__(self):
        return json.dumps(self._dict)
    
    def __getitem__(self, _key):
        return self.getValue(_key)
    
    def getValue(self, _key):
        """
        General method to acquire values associated with '_key'.
        """
        if _key in self._dict:
            return self._dict[_key]
        else:
            raise KeyNotFoundException(_key)
        
    def getStars(self):
        try:
            KEY = "stargazers_count"
            return self.getValue(KEY)
        except KeyNotFoundException:
            raise DidNotCrawlRepoDetailsException(KEY)
    
    def getSize(self):
        try:
            KEY = "size"
            return self.getValue(KEY)
        except KeyNotFoundException:
            raise DidNotCrawlRepoDetailsException(KEY)
    
    def getURL(self):
        KEY = "url"
        return self.getValue(KEY)
    
    def getDict(self):
        return self._dict