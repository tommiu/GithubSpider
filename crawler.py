'''
Created on Jul 4, 2015

@author: Tommi Unruh
'''

import requests as r
import sys
import json
import re
import os
import shutil

class Crawler(object):
    '''
    classdocs
    '''

    # constants
    OAUTH = {
        "token": "71cc84f627fd38b6d7a2e2ba7daf6792578982d9",
        }
    
    
    
    LINK_API   = "https://api.github.com"
    LINK_REPO_API   = LINK_API + "/repositories"
    LINK_SEARCH_API = LINK_API + "/search/repositories"
    LINK_RATE_LIMIT = LINK_API + "/rate_limit"
    HEADER_USER_AGENT    = "tommiu@web.de"
    HEADER_XRATELIMIT_LIMIT     = "X-RateLimit-Limit"
    HEADER_XRATELIMIT_REMAINING = "X-RateLimit-Remaining"
    HEADER_AUTHORIZATION = "token %s" % OAUTH["token"] 
    
    HEADERS = {
            'User-Agent':    HEADER_USER_AGENT,
            'Authorization': HEADER_AUTHORIZATION,
            }
    
    KEY_NEXT  = "next"
    KEY_ETAG  = "ETag"
    KEY_SINCE = "since"
    KEY_COUNT = "count"
    KEY_START = "start"
    KEY_NEXT_LINK = "next_link"
    KEY_RL_REMAIN = "X-RateLimit-Remaining"
    KEY_CLONE_URL = "clone_url"
    KEY_STATUS_CODE   = "status_code"
    KEY_CRAWLED_LINKS = "crawled_links"
    
    FILTERKEY_STARS = "stars"
    
    COMMENT_CHAR = "#"
    
    def __init__(self):
        '''
        Constructor
        '''
    
    def crawlReposFromBeginning(self, file_links, skip=True):
        """
        Crawl all repo links, ignoring repositories that were already 
        crawled and did not change.
        Start crawling at repository 0.
        'skip' is used to not "recrawl" all the already crawled links to check
        for updates. Instead, we use the last link from the crawled-links-data
        to continue crawling new repositories.
        """
        result = None
        
        current_ratelimit = self.getRateLimit()["core"]["remaining"]
        if current_ratelimit == 0:
            self.endExecution()
        else:
            result = {self.KEY_RL_REMAIN: current_ratelimit}

        repo   = None
        etag   = None
        since  = None
        url    = None
        next_link = None
        copy_only = False

        l_backup = lambda s : s + "_backup"
#         l_original = lambda s : s[:-7]
        
        file_links_backup = ""
        
        # Filehandle for writing.
        fw = None

        # If a links file already exists from earlier crawls, then parse it.
        TEXT_PROCESSING = "Processing contents of file: "
        if os.path.isfile(file_links):
            print "File '%s' exists already. Will be appending to it." % (file_links)

            file_links_backup = l_backup(file_links)
            os.rename(file_links, file_links_backup)
            
            with open(file_links_backup, 'r') as f_links:
                if skip:
                    # We do not want to recrawl old data, so
                    # just copy-paste it.
                    shutil.copyfile(file_links_backup, file_links)
                    
                # Open fh for writing.
                fw = open(file_links, 'a')
                
                print TEXT_PROCESSING + str(file_links) + "..."
                sys.stdout.flush()
                
                # 'counter' determines the correct sequence/file-format of
                # the given links-file.
                counter = 0

                if skip:
                    # We do not want to recrawl old data.
                    # Therefore, get the last next-link from the old data,
                    # so that we can continue crawling from there.
                    old_data  = f_links.readlines()[-4:]

                else:
                    old_data = f_links
 
                # Parse old data.
                for l in old_data:
                    counter += 1
                    
                    # Does the line start with '#', indicating a comment?
                    if self.isComment(l):
                        if self.isSince(l) and counter == 1:
                            since = self.getVal(l)

                        elif self.isNext(l) and counter == 2:
                            next_link = self.getVal(l, sep=' ', index=2)
                            
                        elif self.isEtag(l) and counter == 3:
                            etag = self.getVal(l)
                        
                        else:
                            print l
                            print "Encountered an error with file '%s'." % (
                                                                    file_links
                                                                    )
                            sys.exit()
                    else:
                        if l != "" and counter == 4:
                            repo = l.strip()
                            
                            # We are done with parsing a single block of data,
                            # use this information to crawl data and see,
                            # if GitHub answers with new or old data.
                            # -> The link file can get huge and this way, we 
                            # do not spam the memory with large lists of data.
                            counter = 0

                            if url and not skip:
                                # Parse next
                                result = self.nextBackupCrawl(
                                                fw, repo, since, next_link,
                                                etag=etag, url=url, 
                                                copy_only=copy_only
                                                )
                                
                            elif not skip:
                                # Parse first
                                result = self.nextBackupCrawl(
                                                fw, repo, since, next_link,
                                                etag=etag, copy_only=copy_only
                                                )
                            
                            if result and not skip:
                                # Get next URL to parse.
                                url = self.getNextURL(result, next_link)
                            
                                # Check if we have ratelimit remaining.
                                if result[self.KEY_RL_REMAIN] == 0:    
                                    # No ratelimit remaining, continue
                                    # to only copy the old data and finish.
                                    copy_only = True
                                    
                            elif skip:
                                # Get last URL to continue crawling.
                                url = next_link
                            
                print "Done parsing old data."
        
        if result and result[self.KEY_RL_REMAIN] == 0:
            self.endExecution()

        # Parsing finished or no backup file found. Start crawling new data.
        if not fw or (fw and not url):
            # There was no backup file or we didn't find appropriate data
            # in backup file. Start crawling from the beginning.
            if not fw:
                fw = open(file_links, 'a')

            # Parse first
            result = self.nextCrawl(fw)
            url    = self.getNextURL(result)

        # Parse until ratelimit is reached.
        while url and result[self.KEY_RL_REMAIN] > 0:
            # Crawl next page
            result = self.nextCrawl(fw, url=url)
            url    = self.getNextURL(result)

        fw.close()

        if result and result[self.KEY_RL_REMAIN] == 0:
            self.endExecution()

    def nextBackupCrawl(self, fh, repo, since, 
                        next_link, etag=None, 
                        url=None, copy_only=False):
        """
        Get up-to-date data for already crawled repositories.
        If 'copy_only' is specified, we only copy old data from
        the backup file to not lose any already crawled data.
        """
        result = None

        if not copy_only:
            # copy_only is not specified, so parse data from GitHub.
            if etag:
                if url:
                    result = self.crawlRepoLinks(url=url, etag=etag)
                else:
                    result = self.crawlRepoLinks(etag=etag)
            elif url:
                result = self.crawlRepoLinks(url=url)
            else:
                result = self.crawlRepoLinks()

        if (
        result and result[self.KEY_STATUS_CODE] == 200 and 
        result[self.KEY_RL_REMAIN] > 0 and not copy_only
        ):
            # New results from GitHub
            fh.write("# " + self.KEY_SINCE + ": %s\n" % result[self.KEY_SINCE])
            fh.write("# " + self.KEY_NEXT_LINK  + ": %s\n" % result[self.KEY_NEXT_LINK])
            fh.write("# " + self.KEY_ETAG  + ": %s\n" % result[self.KEY_ETAG])

            fh.write(json.dumps(result[self.KEY_CRAWLED_LINKS]) + "\n")
            fh.flush()
        
        else: 
            # Results didn't change since last crawling OR
            # we do not have ratelimit remaining, so just copy old data.
            fh.write("# " + self.KEY_SINCE + ": %s\n" % since)
            fh.write("# " + self.KEY_NEXT_LINK  + ": %s\n" % next_link)
            fh.write("# " + self.KEY_ETAG  + ": %s\n" % etag)
            
            fh.write(str(repo) + "\n")
            fh.flush()

        if copy_only:
            # copy_only specifies, that we will only copy data from the backup
            # file and finish afterwards.
            # Therefore, we specify the next parsing url for copy purposes.
            result = {
                    self.KEY_RL_REMAIN: 0,
                    self.KEY_NEXT_LINK: next_link
                    }
            print "Copied from old data. Skipping..."

        return result
    
    def nextCrawl(self, fh, url=None):
        """
        Crawl repositories from GitHub.
        'url' is used to specify the next parse-URL.
        """
        result = None
        
        if url:
            result = self.crawlRepoLinks(url=url)
        else:
            result = self.crawlRepoLinks()

        if (
        result[self.KEY_STATUS_CODE] == 200 and 
        result[self.KEY_RL_REMAIN] > 0
        ):
            # New results from GitHub
            fh.write("# " + self.KEY_SINCE + ": %s\n" % result[self.KEY_SINCE])
            fh.write("# " + self.KEY_NEXT_LINK  + ": %s\n" % result[self.KEY_NEXT_LINK])
            fh.write("# " + self.KEY_ETAG  + ": %s\n" % result[self.KEY_ETAG])

            fh.write(json.dumps(result[self.KEY_CRAWLED_LINKS]) + "\n")
            fh.flush()
            
        elif result[self.KEY_RL_REMAIN] == 0:
            result = {
                    self.KEY_RL_REMAIN: 0,
                    self.KEY_NEXT_LINK: ""
                    }
            
        return result

    def crawlRepoLinks(self, since=0, query=[["language", "PHP"]], etag=None,
                       url=None):
        """
        Get public repositories information since 'since', that fit to 'query'.
        
        'etag' can be used to save API-query ratelimit, because the server will
        simply answer with code 304 to indicate no changes since the same last
        query.
        
        'url' can be used instead of 'since' to directly 
        provide the correct url. 
        """
        result = {}
        crawled_links = []
        
        headers = self.HEADERS.copy()
        if etag:
            headers["If-None-Match"] = etag
            
        resp = None
        
        if not url:
            print "Crawling, starting from repository %d." % (since)
            result[self.KEY_SINCE] = since
            resp = r.get(self.addOAuth(self.LINK_REPO_API + "?since=" + str(since)),
                         headers=headers)
        else:
            print "Crawling next: %s." % (url)
            
            # Extract the value for 'since' from 'url'.
            since = None
            _, _help = url.split("?")
            args = _help.split("&")
            for arg in args:
                if arg.startswith("since"):
                    _, since = arg.split("=")
                    break

            result[self.KEY_SINCE] = since
            
            resp = r.get(url, headers=headers)
            
        # Extract necessary information from response.
        if resp.links:
            # Extract next link.
            result[self.KEY_NEXT_LINK] = resp.links["next"]["url"]
            
        # Extract etag.
        if self.KEY_ETAG in resp.headers:
            result[self.KEY_ETAG] = resp.headers[self.KEY_ETAG]
     
        # Extract status code.
        result[self.KEY_STATUS_CODE] = resp.status_code
        
        # 304 = old data.
        # 403 = rate limit exceeded.
        if resp.status_code != 304 and resp.status_code != 403:
            # If GitHub answered with new results, parse them.
            decoded = json.loads(resp.text)

            for _dict in decoded:
                # Check if filters apply to link.
                does_fit = True

                resp = r.get(self.addOAuth(_dict["url"]),
                         headers=headers)
                decoded = json.loads(resp.text)
                
                # Extract remaining ratelimit.
                if self.KEY_RL_REMAIN in resp.headers:
                    result[self.KEY_RL_REMAIN] = int(
                                            resp.headers[self.KEY_RL_REMAIN]
                                            )
                
                if result[self.KEY_RL_REMAIN] == 0:
                    break
                
                for filter_key, filter_value in query:
                    if filter_key in decoded:
                        if not decoded[filter_key] == filter_value:
                            does_fit = False
                            break
                    else:
                        does_fit = False
                        break
                
                if does_fit:
#                     crawled_links.append(decoded["clone_url"])
                    crawled_links.append(decoded)
        elif resp.status_code == 304:
            # We already know these repos, skip them.
            print "Already crawled repo - skipping."
            
        # Extract remaining ratelimit.
        if self.KEY_RL_REMAIN in resp.headers:
            result[self.KEY_RL_REMAIN] = int(
                                        resp.headers[self.KEY_RL_REMAIN]
                                        )
                
        result[self.KEY_CRAWLED_LINKS] = crawled_links
        result[self.KEY_COUNT] = len(crawled_links)


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
                        if l != "" and l != "[]\n":
                            # Found a list of repo dictionaries. Read it.
                            _list = json.loads(l)
                            for repo in _list:
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
        
        result = []
        for l in fr.readlines():
            if not self.isComment(l):
                if l != "" and l != "[]\n":
                    # Found a list of repo dictionaries. Read it.
                    _list = json.loads(l)
                    
                    for repo in _list:
                        is_suitable = True
                        
                        # Apply filter and append 
                        # suitable repos to the result.
                        if flow[0] == self.FILTERKEY_STARS:
                            # Extract stars value
                            stars = int(repo["stargazers_count"])
                            
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
                                result.append(repo)
                                
        fw.write(json.dumps(result))
                                
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
        if self.KEY_NEXT_LINK in _dict:
            return _dict[self.KEY_NEXT_LINK]
        else:
            if next_link:
                return next_link
            else:
                return ""
    
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
    
    def isSince(self, _str):
        try:
            key, _ = _str.split(":")
            if key[2:] == self.KEY_SINCE:
                return True
            
        except ValueError:
            pass
        
        return False
    
    def isNext(self, _str):
        try:
            _, key, _ = _str.split(" ")
            if key.startswith(self.KEY_NEXT_LINK):
                return True
            
        except ValueError:
            pass
        
        return False
    
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
        resp = r.get(self.addOAuth(self.LINK_RATE_LIMIT))
            
        _dict = json.loads(resp.text)["resources"]
        return _dict

    def addOAuth(self, url):
        """
        Add the OAuth get-parameter to the specified 'url'.
        """
        token_query = "access_token=" + self.OAUTH["token"]
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