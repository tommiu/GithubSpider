'''
Created on Jul 4, 2015

@author: Tommi Unruh
'''

import sys
import re
import os
import shutil

from github.session import Session as GithubSession
from github.repository_list import RepositoryList
from github.exceptions import RatelimitExceededException
import signal
from github.oauthManager import *
import errno
from github.data_manager import DataManager

class Crawler(object):
    '''
    classdocs
    '''

    # constants
    FILE_AUTHENTICATION = "authentication"
    
    LINK_API   = "https://api.github.com"
    LINK_REPO_API   = LINK_API + "/repositories"
    LINK_SEARCH_API = LINK_API + "/search/repositories"
    LINK_RATE_LIMIT = LINK_API + "/rate_limit"
    HEADER_USER_AGENT    = None
    HEADER_XRATELIMIT_LIMIT     = "X-RateLimit-Limit"
    HEADER_XRATELIMIT_REMAINING = "X-RateLimit-Remaining"
    
    KEY_NEXT  = "next"
    KEY_SINCE = "since"
    KEY_COUNT = "count"
    KEY_START = "start"
    KEY_RL_REMAIN = "X-RateLimit-Remaining"
    KEY_CLONE_URL = "clone_url"
    KEY_STATUS_CODE   = "status_code"
    KEY_CRAWLED_LINKS = "crawled_links"
    
    FILTERKEY_STARS = "stars"
    
    # GitHub Session object
    s = None
    
    def __init__(self, file_path):
        '''
        Constructor
        '''
        # DataManager handles file reading/writing.
        self.datamanager  = DataManager()
        
        # Get OAuth from file 'authentication'.
        auth_file    = file_path
        auth_manager = OAuthManager(filename=auth_file)
        auth = None
        try:
            auth = auth_manager.getAuthData()
            
        except (AuthFileNotFoundException, AuthException):
            # Authentication file not found or malformatted. Recreate it.
            auth = self.initiateAuthCreation(auth_manager)
              
        except NoCredentialsException:
            oauth      = None
            user_agent = None
                
        if auth:
            oauth       = auth[auth_manager.KEY_OAUTH]
            user_agent  = auth[auth_manager.KEY_USER_AGENT]
    
        self.OAUTH = oauth
        self.HEADER_USER_AGENT = user_agent
        
        self.HEADERS = {
                    'User-Agent':    self.HEADER_USER_AGENT,
                    'Authorization': "token %s" % self.OAUTH,
                    }
        
        # Setup authentication and settings
        self.s = GithubSession(self.OAUTH, self.HEADER_USER_AGENT)
        
    def initiateAuthCreation(self, auth_manager):
        try:
            auth_manager.createAuth()
            auth = auth_manager.getAuthData()
            print "Authentication process done. Continuing..."
            
        except OAuthCreationException:
            # OAuth error. Maybe the OAuth token could not be created, because
            # it already exists.
            print (
                "OAuth error. Maybe authentication file could not be written "
                "because of missing write-privilege."
                )
            sys.exit()
        
        return auth
        
    def crawlReposWUpdate(self, data_filename):
        self.crawlRepos(data_filename, skip=False)
    
    def crawlRepos(self, file_links, skip=True, _filter=None):
        current_ratelimit = self.getRateLimit()["core"]["remaining"]
        if current_ratelimit == 0:
            self.endExecution()
        
        url = None
        copy_only = False
        
        file_links_backup = ""

        # Filehandle for writing.
        fw = None
        f_links = None
        
        
        TEXT_PROCESSING = "Processing contents of file: "
        # If a links file already exists from earlier crawls, then parse it.
        if os.path.isfile(file_links):
            print "File '%s' exists already. Will be appending to it." % (file_links)

            file_links_backup = file_links + "_backup"
            
            def restoreBackup(signum, frame):
                """
                Inner function: Restore original file from backup upon 
                termination in backup process.
                """
                msg = "Got exit signal. Restoring original file from backup..."
                print "\n%s\r" % (msg), 
                
                if fw:
                    fw.close()

                if f_links:
                    f_links.close()

                # Copy backup file back.
                shutil.copyfile(file_links_backup, file_links)
                
                print "%s Done." % (msg)
                
                sys.exit()
            
            # Catch process-kill signal.
            signal.signal(signal.SIGTERM, restoreBackup)
            
            # Also catch Ctrl-C/D.
            signal.signal(signal.SIGINT, restoreBackup)

            os.rename(file_links, file_links_backup)
            
            f_links     = open(file_links_backup, 'r')
            
            if skip:
                # We do not want to recrawl old data, so
                # just copy-paste it.
                shutil.copyfile(file_links_backup, file_links)
                    
            # Open fh for writing.
            fw = open(file_links, 'a')
            
            print TEXT_PROCESSING + str(file_links) + "..."
            sys.stdout.flush()

            if skip:
                # We do not want to recrawl old data.
                # Therefore, get the last next-link from the old data,
                # so that we can continue crawling from there.
                data = self.datamanager.getDataLikeTail(file_links, 
                                                            1, stepsize=65)

                url = self.datamanager.extractNextURL(data)
            else:
                old_data = f_links
 
            etag  = None
            repos = None
            next_url = None
            
            file_pos = None
            # Parse old data if skip was not specified.
            while 1 and not skip:
                try:
                    file_pos    = old_data.tell()
                    parsed_data = self.datamanager.parseNextBlock(old_data)

                    if parsed_data:
                        _repos, url, etag, next_url = parsed_data
                        
                        repos = RepositoryList(
                                    url, etag, repos=_repos,
                                    next_url=next_url
                                    )
        
                        if not skip:
                            try:
                                # Update data, by requesting Github API.
                                self.nextBackupCrawl(fw, repos, 
                                                     copy_only=copy_only,
                                                     _filter=_filter)
                                
                            except RatelimitExceededException:
                                    # No ratelimit remaining, continue
                                    # to only copy the old data and finish.
                                    copy_only = True

                    # We finished parsing the old data.                    
                    else:
                        break
                    
                # Encountered malformatted block, probably because
                # the original data file was cut/edited.
                # Rewind the file position and skip one line.
                except IOError as err:
                    old_data.seek(file_pos, os.SEEK_SET)
                    old_data.readline()
                    print err, " Skipping this line!"

            if repos:
                url = repos.getNextURL()
                
            # Remove backup signal handlers.
            # SIG_DFL is the standard signal handle for any signal.
            signal.signal(signal.SIGTERM, signal.SIG_DFL)
            signal.signal(signal.SIGINT,  signal.SIG_DFL)
            print "Done parsing old data."
            
            if copy_only:
                self.endExecution()
        
        repos = None
        
        try:
            # Parsing finished or no backup file found. Start crawling new data.
            if not fw:
                # There was no backup file
                fw = open(file_links, 'a')
            
            if not url:
                # We do not have a URL to start form yet.
                # Start crawling from the beginning.
                repos = self.nextCrawl(fw, _filter=_filter)
                url   = repos.getNextURL()

            # Parse until ratelimit is reached.
            while url:
                # Crawl next page
                repos = self.nextCrawl(fw, url=url, _filter=_filter)
                url   = repos.getNextURL()
    
            fw.close()
            
        except RatelimitExceededException:
            self.endExecution()

    def nextBackupCrawl(self, fh, repository_list, 
                        copy_only=False, _filter=None):
        """
        Get up-to-date data for already crawled repositories.
        If 'copy_only' is specified, we only copy old data from
        the backup file to not lose any already crawled data.
        """
        result = None

        if not copy_only:
            # We do not want to simply copy the old data - 
            # check for an update.
            print "Updating from: %s" % repository_list.getURL()
            
            result = self.s.update(repository_list)
            
            if result:
                print "Found update!"
        
        if _filter:
            # Filter results
            repository_list.filter(self.s, self.DEFAULT_REPO_FILTER)
        
        self.datamanager.writeRepositoryList(fh, repository_list)
        
        return result

    def nextCrawl(self, fh, url=None, _filter=None):
        """
        Crawl repositories from GitHub.
        'url' is used to specify the next parse-URL.
        """
        result = None

        _format = "Crawling: %s"
        if url:
            print _format % url
            result = self.s.getRepos(url=url)
        else:
            print _format % "From beginning."
            result = self.s.getRepos()


        if _filter:
            # Filter results
            result.filter(self.s, _filter)

        # Write new results from Github.
        self.datamanager.writeRepositoryList(fh, result)

        return result
        
    def getKeyFromCrawlData(self, input_file, output_file,
                                  key=KEY_CLONE_URL):
        """
        Extract the value for 'key' from every crawled repository in file
        'input_file'.
        Output is redirected into 'output_file'.
        """
        with open(input_file, 'r') as fr:
            with open(output_file, 'w') as fw:
                for l in fr.readlines():
                    if not self.isComment(l):
                        if l != "":
                            repos = RepositoryList(repos=l)
                            
                            if not repos.isEmpty():
                                # Found a list of repo dictionaries.
                                # Read it and get its value for 'key'.
                                for repo in repos:
                                    fw.write(str(repo[key]).strip() + "\n")

    def extractReposFiltered(self, input_file, output_file,
                             _filter=None):
        """
        Extract any repository from 'input_file' that matches 'filter',
        into 'output_file'.
        """
        flow = []
        if _filter:
            flow = self.parseFilter(_filter)
        else:
            print "No filter specified. Quitting..."
            sys.exit()
        
        if flow[0] == -1:
            print "Could not parse filter correctly. Quitting..."
            sys.exit()
            
        fr = open(input_file, 'r')
        fw = open(output_file, 'w') 
        
        filtered_repos = RepositoryList()
        for l in fr.readlines():
            if not self.isComment(l):
                if l != "" and l != "[]\n":
                    # Found a list of repo dictionaries. Read it.
                    repos = RepositoryList(repos=l)
                    is_suitable = True
                    
                    for repo in repos:
                        # Apply filter and append 
                        # suitable repos to the result.
                        if flow[0] == self.FILTERKEY_STARS:
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
                                    
                            if is_suitable:
                                filtered_repos += repo
                                
        fw.write(str(filtered_repos))
                                
        fr.close()
        fw.close()
                    
    def parseFilter(self, _filter):
        """
        Parse a given filter and extract interesting values.
        """
        flow = [-1, -1, -1, -1]
        
        if _filter:
            # Expecting filter of type 'keyword="values"'. A value can be
            # "=5", so do not just .split("=").
            index = _filter.find("=")

            if index > 0:
                key   = _filter[0:index].strip()
                val   = _filter[index+1:].strip()
            else:
                raise ValueError("Filter format is wrong. You gave: %s."
                                 "However, expected is '%s'!" % (
                                                    _filter, "key=\"values\""
                                                    ))
            
            if key == self.FILTERKEY_STARS and val:
                flow[0] = self.FILTERKEY_STARS
                
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
                            "stars=\"=2\", stars=\">2 <5\", stars=\"<10\""
                            )
            else:
                raise ValueError("Filter not known: %s" % (key))
        return flow
    
    def endExecution(self):
        print "Ratelimit reached. Quitting..."
        sys.exit()
        
    def getNextURL(self, _dict, next_link=None):
        """
        Find the URL in _dict and return it.
        Empty string if it does not exist.
        'next_link' can be used to specify an alternative if there is no
        link in _dict.
        """
        if self.KEY_NEXT_URL in _dict:
            return _dict[self.KEY_NEXT_URL]
        else:
            if next_link:
                return next_link
            else:
                return ""
        
    def search(self, q="language:PHP", sort=None, order=None):
        """
        Search GitHub for 'q'.
        Any search is limited to 1000 results.
        """
        # Could yield problems, because no deep copy is done.
        # TODO: (maybe)
        resp = r.get(self.addOAuth(self.LINK_SEARCH_API + "?q=" + q),
                     headers=self.HEADERS)
        
        decoded = json.loads(resp.text)
        
        for _dict in decoded["items"]: 
            print _dict["clone_url"]
            
        return decoded
    
    def getRateLimit(self):
        return self.s.getRatelimit()

    def addOAuth(self, url):
        """
        Add the OAuth get-parameter to the specified 'url'.
        """
        token_query = "access_token=" + self.OAUTH
        if url.find('?') != -1:
            url += "&" + token_query
        else:
            url += "?" + token_query 
    
        return url
    
    ### LEGACY CODE
    ### ~~~~~~~~~~~
    def crawlSearchDays(self, start, end, q="langauge:PHP", sort=None, order=None):
        """
        Crawl the clone urls for the search query 'q'.
        However, the query will be modified to only show results of
        a certain day.
        This will be repeated until each day in [start, end] was queried.
        Therefore, 'start' and 'end' have to be dates of format YYYY-MM-DD.
        
        Some days may be skipped due to different length of months.
        """
        # Check start and end format first.
        r = re.compile('^[0-9]{4}-[0-9]{2}-[0-9]{2}$')
        if not r.match(start) or not r.match(end):
            # 'start' or 'end' have a wrong format.
            print (
                "'start' and 'end' are expected to be of format YYYY-MM-DD."
                "'%s' and '%s' were given." % (start, end)
                )
            return -1
        
        else:
            # Parameters are ok, continue
            pass
    
    def crawlSearching(self, q="language:PHP", sort=None, order=None):
        """
        Crawl the clone urls for the search query 'q'.
        The response is split into 10 URLs with 100 repositories each.
        """
        per_page = 100
        page     = 0
        
        for page in range(1, 11):
            resp = self.search(q + "&per_page=" + str(per_page) + 
                               "&page=" + str(page))
            
            # Check if the response was empty, so that we can reduce
            # the load on the GitHub API servers.
            if not resp["items"]:
                break