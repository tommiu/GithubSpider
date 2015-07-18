'''
Created on Jul 18, 2015

@author: Tommi Unruh
'''

class RatelimitExceededException(object):
    def __str__(self):
        return "Your ratelimit is exceeded!"