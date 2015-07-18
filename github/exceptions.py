'''
Created on Jul 18, 2015

@author: Tommi Unruh
'''

class RatelimitExceededException(BaseException):
    def __str__(self):
        return "Your ratelimit is exceeded!"
    
class UnavailableRepoException(BaseException):
    def __str__(self):
        return "Repository is unavailable."