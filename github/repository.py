'''
Created on Jul 17, 2015

@author: tommi
'''

import json

class Repository(object):
    '''
    classdocs
    '''

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
                if self._dict[key] != _filter[key]:
                    return False
            
            else:
                return False
            
        return True
    
    def __str__(self):
        return json.dumps(self._dict)
    
    def getURL(self):
        return self._dict["url"]
    
    def getDict(self):
        return self._dict