'''
Created on Aug 29, 2015

@author: tommi
'''
import os
import errno
import sys
from github.repository_list import RepositoryList

class DataManager(object):
    '''
    Manages the saving and loading of data.
    '''
    COMMENT_CHAR = "#"
    
    KEY_ETAG  = "ETag"
    KEY_THIS_URL  = "url"
    KEY_NEXT_URL  = "next_url"
    
    FILTERKEY_SIZE  = "size"
    FILTERKEY_STARS = "stars"
    FILTERKEY_EMPTY = "nofilter"
    
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
    
    @staticmethod
    def isComment(_str):
        return _str.startswith(DataManager.COMMENT_CHAR)    

    @staticmethod
    def getKeysFromCrawlData(input_file, output_file, keys):
        """
        Extract the value for 'key' from every crawled repository in file
        'input_file'.
        Output is redirected into 'output_file'.
        """
        # Parse "keys". Can be a single key or 
        # multiple keys seperated by commas.
        if "," in keys:
            print "yolo" 
            sys.exit()
        
        header = ""
        
        # Extract values
        with open(input_file, 'r') as fr:
            with open(output_file, 'w') as fw:
                # Write "header" line first.
                fw.write(header + "\n")
                
                for l in fr:
                    if not DataManager.isComment(l):
                        if l != "":
                            repos = RepositoryList(repos=l)
                            
                            if not repos.isEmpty():
                                # Found a list of repo dictionaries.
                                # Read it and get its value for 'key'.
                                for repo in repos:
                                    fw.write(str(repo[keys]).strip() + "\n")
        
    @staticmethod                            
    def extractReposFiltered(input_file, output_file,
                             _filter=None):
        """
        Extract any repository from 'input_file' that matches 'filter',
        into 'output_file'.
        """
        flow = []
        try:
            flow = DataManager.parseFilter(_filter)
            
        except Exception as err:
            print err
            sys.exit()
        
        if flow[0] == -1:
            print "Could not parse filter correctly. Quitting..."
            sys.exit()
        
        elif flow[0] == DataManager.FILTERKEY_EMPTY:
            print "Empty filter specified, copying all repositories."
            
        fr = open(input_file, 'r')
        fw = open(output_file, 'w') 
        
        filtered_repos = RepositoryList()
        for l in fr.readlines():
            if not DataManager.isComment(l):
                if l != "" and l != "[]\n":
                    # Found a list of repo dictionaries. Read it.
                    repos = RepositoryList(repos=l)
                    
                    for repo in repos:
                        is_suitable = True
                        
                        # Apply filter and append 
                        # suitable repos to the result.
                        if flow[0] == DataManager.FILTERKEY_STARS:
                            # Extract stars value
                            stars = repo.getStars()
                            
                            if flow[1] != -1:
                                if stars != flow[1]:
                                    is_suitable = False
                            else:
                                if flow[2] != -1:
                                    # specified filter: stars > flow[2]
                                    if stars <= flow[2]:
                                        is_suitable = False
                                if flow[3] != -1:
                                    # specified filter: stars < flow[3]
                                    if stars >= flow[3]:
                                        is_suitable = False
                                
                        elif flow[0] == DataManager.FILTERKEY_SIZE:
                            # Extract size value
                            size = repo.getSize()
                            
                            if flow[1] != -1:
                                # specified filter: size > flow[1]
                                if size <= flow[1]:
                                    is_suitable = False
                            else:
                                if flow[2] != -1:
                                    # specified filter: size > flow[2]
                                    if size >= flow[2]:
                                        is_suitable = False
                                        
                        elif flow[0] == DataManager.FILTERKEY_EMPTY:
                            pass
                                        
                        if is_suitable:
                            filtered_repos += repo
        
        # Print out the number of matched repositories.
        _len = len(filtered_repos)
        _str = "repository" if _len == 1 else "repositories"
        print "%d %s matched and written to file." % (_len, _str)
        fw.write(str(filtered_repos))
                                
        fr.close()
        fw.close()
    
    @staticmethod
    def parseFilter(_filter):
        """
        Parse a given filter and extract interesting values.
        """
        flow = [-1, -1, -1, -1]

        if _filter:
            # Expecting filter of type 'keyword="values"'. A value can be
            # "=5", so do not just .split("=").
            index = _filter.find(":")

            if index > 0:
                key   = _filter[0:index].strip()
                val   = _filter[index+1:].strip()
            else:
                raise ValueError("Filter format is wrong. You gave: %s. "
                                 "However, expected is '%s'!" % (
                                                    _filter, "key:\"values\""
                                                    ))
            
            if key == DataManager.FILTERKEY_STARS and val:
                flow[0]
                
                # Expecting "=int", ">int", "<int", ">int <int",
                # "<int >int" or "" 
                for _val in val.split(" "):
                    # Ignore empty values
                    if _val:
                        # Check for "=int"
                        index = _val.find("=")
                        if index != -1:
                            # Found "="

                            # Ignore values found earlier.
                            flow[1] = int(_val[index+1:].strip())
                        
                            # Break and ignore rest.
                            break

                        # Check for ">int"
                        index = _val.find(">")
                        if index != -1:
                            # Found ">"
                            
                            flow[2] = int(_val[index+1:].strip())
                            
                            continue
                        
                        # Check for "<int"
                        index = _val.find("<")
                        if index != -1:
                            # Found "<"
                            
                            flow[3] = int(_val[index+1:].strip())
                
                if (
                flow[1] == -1 and flow[2] != -1 and flow[3] != -1 and 
                flow[2] + 1 >= flow[3]
                ):
                    raise ValueError("Filter will not yield "
                                     "any results: >%d <%d." % (
                                                        flow[2], flow[3]
                                                        ))
                elif (
                flow[1] == -1 and flow[2] == -1 and flow[3] == -1      
                ):
                    raise ValueError(
                            "Filter could not be parsed. \nExample filters: "
                            "stars:\"=2\", stars:\">2 <5\", stars:\"<10\""
                            )
                    
            elif key == DataManager.FILTERKEY_SIZE and val:
                flow[0] = key
                
                # Expecting ">int", "<int", ">int <int",
                # "<int >int" or "" 
                for _val in val.split(" "):
                    # Ignore empty values
                    if _val:
                        # Check for ">int"
                        index = _val.find(">")
                        if index != -1:
                            # Found ">"
                            
                            flow[1] = int(_val[index+1:].strip())
                            
                            continue
                        
                        # Check for "<int"
                        index = _val.find("<")
                        if index != -1:
                            # Found "<"
                            
                            flow[2] = int(_val[index+1:].strip())

                if flow[1] >= flow[2] - 1:
                    raise ValueError(
                            "Filter will not yield any results: >%d <%d." % (
                                                                flow[1], flow[2]
                                                                )
                            )
                
                elif flow[1] == -1 and flow[2] == -1:
                    raise ValueError(
                            "Filter could not be parsed. \nExample filters: "
                            "size:\">50 <1000\", size=\"<500\", size:\">1000\""
                            )
            
            elif key == DataManager.FILTERKEY_EMPTY:
                flow[0] = key
                
            else:
                raise ValueError("Filter not known: %s" % (key))

        return flow
    
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
