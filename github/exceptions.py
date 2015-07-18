'''
Created on Jul 18, 2015

@author: Tommi Unruh
'''
from Crypto.Util.RFC1751 import _key2bin

class RatelimitExceededException(BaseException):
    def __str__(self):
        return "Your ratelimit is exceeded!"
    
class UnavailableRepoException(BaseException):
    def __str__(self):
        return "Repository is unavailable."
    
class DidNotCrawlRepoDetailsException(BaseException):
    def __init__(self, _key=None):
        self._key = _key
            
    def __str__(self):
        if self._key:
            return (
                "This repository object does not contain the specified key '%s', "
                "because its detailed representation was not requested "
                "beforehand." % self._key
                )
        else:
            return (
                "This repository object does not contain the specified key, "
                "because its detailed representation was not requested "
                "beforehand."
                )
    
class KeyNotFoundException(BaseException):
    def __init__(self, _key=None):
        self._key = _key
            
    def __str__(self):
        if self._key:
            return (
            "This repository object does not contain the specified key: %s" % (
                                                                    self._key
                                                                    )        
            )
        
        else:
            return (
            "This repository object does not contain the specified key."      
            )