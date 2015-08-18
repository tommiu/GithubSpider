'''
Created on Aug 13, 2015

@author: Tommi Unruh
'''

import subprocess
import os
from time import sleep
import sys

class GitDownloader(object):
    """
    Manages the download of git repositories.
    """
    def cloneAllFromFile(self, filename, linenumber=0):
        with open(filename, 'r') as fh:
            if linenumber > 1:
                self.goToLine(fh, linenumber)

            l = fh.readline()
            while l:
                try:
                    self.cloneRepoLink(l.strip())
                
                except RepositoryExistsException as err:
                    print err
                    print "Skipping to next link in file."
                    
                finally:
                    linenumber += 1
            
    def cloneRepoLink(self, link):
        msg = "Cloning repository: %s..." % link
        
        print "%s\r" % msg,
        sys.stdout.flush()
        process = subprocess.Popen(["git", "clone", link], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        if stderr:
            if "already exists and is not an empty directory." in stderr:
                raise RepositoryExistsException(str(stderr))
        
        print "%s Done." % msg
        print stdout
    
    def goToLine(self, fh, linenumber):
        """
        Go to 'linenumber' of a huge text file in an (memory-)efficient way.
        """
        if linenumber < 1:
            raise IOError(
                "Specified linenumber '%d' is smaller than 1." % linenumber
                )
        
        fh.seek(0, os.SEEK_SET)
        for _ in range(0, linenumber - 1):
            fh.readline()
            

class RepositoryExistsException(BaseException):
    pass