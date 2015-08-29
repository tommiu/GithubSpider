'''
Created on Aug 29, 2015

@author: tommi
'''
import os
import errno
import sys

class DataManager(object):
    '''
    Manages the saving and loading of data.
    '''
    COMMENT_CHAR = "#"
    
    KEY_ETAG  = "ETag"
    KEY_THIS_URL  = "url"
    KEY_NEXT_URL  = "next_url"

    def __init__(self):
        '''
        Constructor
        '''
        
    def parseNextBlock(self, fh):
        """
        Parse next block of data. Expect:
        1. List of dictionaries.
        2. # url: https://api.github.com/repositories?since=XXX
        3. # ETag: W/"unique_string"
        4. # next_url: https://api.github.com/repositories?since=XXX
        """
        url       = None
        etag      = None
        repos     = None
        url_link  = None
        
        # 'counter' determines the correct sequence/file-format of
        # the given links-file.
        counter   = 0
        # Parse four lines of data.
        for l in fh:
            counter += 1
            
            # Does the line start with '#', indicating a comment?
            if self.isComment(l):
                
                # IMPORTANT: By specifying counter < 4, any order of
                # url, next_url and etag is allowed.
                # The speedloss of having to do extra checks of 
                # isURL() and isNext() is negligible.
                if self.isURL(l) and counter == 2:
                    url = self.getVal(l, sep=' ', index=2)

                elif self.isEtag(l) and counter == 3:
                    etag = self.getVal(l)
                    
                elif self.isNext(l) and counter == 4:
                    next_url = self.getVal(l, sep=' ', index=2)
                    
                else:
                    raise IOError("File is malformatted, stopping at line: "
                                  "%s" % l)

            else:
                if l != "" and counter == 1:
                    repos = l.strip()

            # We are done with parsing a single block of data.
            if counter == 4:
                if url and etag and repos and next_url:
                    return (
                        repos.strip(), url.strip(), 
                        etag.strip(), next_url.strip()
                        )

                else:
                    raise IOError("Encountered an error: "
                                  "Data in file is malformatted.\n"
                                  "found repos? %s\n"
                                  "url: %s\n"
                                  "etag: %s\n"
                                  "next url: %s" % (
                                            "Yes" if repos else "No",
                                            str(url),
                                            str(etag),
                                            str(next_url)
                                            ))
                    
        # For loop exited before returning, indicating the end 'fh'.
        return None
    
    def getDataLikeTail(self, filename, count, stepsize=2048):
        """
        Efficient way to read the last lines of a huge file.
        """
        sep = "\n"
        
        with open(filename, 'rb') as fh:
            # Go to end of file.
            pos = 0
            linecount = 0
            fh.seek(0, os.SEEK_END)
            
            while linecount <= count:
                try:
                    # Go backwards in file.
                    fh.seek(-stepsize, os.SEEK_CUR)
                    
                    # Count found newlines.
                    linecount += fh.read(stepsize).count(sep)
    
                    # We just went forwards, so go back again.
                    fh.seek(-stepsize, os.SEEK_CUR)
                    print "stepped back once"
                except IOError as e:
                    if e.errno == errno.EINVAL:
                        # Attempted to seek past the start while stepping back.
                        stepsize = fh.tell()
                        fh.seek(0, os.SEEK_SET)
                        
                        # Read from beginning.
                        linecount += fh.read(stepsize).count(sep)
                        
                        pos = 0
                        break

                pos = fh.tell()
                
        # Now read data.
        with open(filename, 'r') as fh:
            fh.seek(pos, os.SEEK_SET)
            
            for line in fh:
                # We found n (or even more) lines, 
                # so we could need to skip some lines.
                if linecount > count:
                    linecount -= 1
                    continue
                
                # Otherwise return data.
                yield line
    
    def writeRepositoryList(self, fh, repository_list):
        """
        Write crawled repository_list to filehandler 'fh'.
        """
        fh.write(str(repository_list) + "\n")
        fh.write(self.COMMENT_CHAR + " " + self.KEY_THIS_URL  + ": %s\n" % 
                repository_list.getURL())
        fh.write(self.COMMENT_CHAR + " " + self.KEY_ETAG      + ": %s\n" % 
                 repository_list.getEtag())
        fh.write(self.COMMENT_CHAR + " " + self.KEY_NEXT_URL  + ": %s\n" % 
                 repository_list.getNextURL())

        fh.flush()
    
    def isComment(self, _str):
        return _str.startswith(self.COMMENT_CHAR)
    
    def isEtag(self, _str):
        try:
            key, _ = _str.split(":")
            if key[2:] == self.KEY_ETAG:
                return True
            
        except ValueError:
            pass
        
        return False
    
    def isURL(self, _str):
        try:
            _, key, _ = _str.split(" ")
            if key.startswith(self.KEY_THIS_URL):
                return True
            
        except ValueError:
            pass
        
        return False
    
    def isNext(self, _str):
        try:
            _, key, _ = _str.split(" ")
            if key.startswith(self.KEY_NEXT_URL):
                return True
            
        except ValueError:
            pass
        
        return False
    
    def extractNextURL(self, generator):
        for l in generator:
            if self.isNext(l):
                return self.getVal(l, sep=' ', index=2)
        
        # No next URL found.
        raise IOError("next_url not found.")
    
    def getVal(self, _str, sep=':', index=1):
        """
        Return the val if _str includes one.
        Otherwise return False.
        """
        # "# " + self.KEY_SINCE + ": %d\n" % result[self.KEY_SINCE])
        # "# " + self.KEY_ETAG  + ": %s\n" % result[self.KEY_ETAG])
        try:
            _arr = _str.split(sep)
            return _arr[index].strip()
        except ValueError:
            return False
