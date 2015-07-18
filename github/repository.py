'''
Created on Jul 17, 2015

@author: tommi
'''

import json

class Repository(object):
    '''
    classdocs
    '''

    def __init__(self, encoded_json):
        '''
        Constructor
        '''
        self._dict = json.loads(encoded_json)
        
