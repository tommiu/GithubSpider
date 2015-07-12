'''
Created on Jul 4, 2015

@author: Tommi Unruh
'''

import requests as r
import sys
import json
import re
import os

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
    
    COMMENT_CHAR = "#"
    
    def __init__(self):
        '''
        Constructor
        '''
    
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
    
    def crawlReposFromBeginning(self, file_links):
        """
        Crawl all repo links, ignoring repositories that were already 
        crawled and did not change.
        Start crawling at repository 0.
        """
        repo   = None
        etag   = None
        since  = None
        result = None
        url    = None
        next_link = None
        copy_only = False
        
        l_backup = lambda s : s + "_backup"
#         l_original = lambda s : s[:-7]
        
        file_links_backup = ""
        
        # Filehandle for writing.
        fw = None
        open(file_links, 'a')
        
        # If a links file already exists from earlier crawls, then parse it.
        TEXT_PROCESSING = "Processing contents of file: "
        if os.path.isfile(file_links):
            print "File '%s' exists already. Will be appending to it." % (file_links)

            file_links_backup = l_backup(file_links)
            os.rename(file_links, file_links_backup)
            
            with open(file_links_backup, 'r') as f_links:
                # Open fh for writing.
                fw = open(file_links, 'a')
                
                print TEXT_PROCESSING + str(file_links) + "..."
                sys.stdout.flush()
                
                # 'counter' determines the correct sequence/file-format of
                # the given links-file.
                counter = 0

                for l in f_links.readlines():
                    counter += 1
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

                            if result and url:
                                # Parse next
                                result = self.nextBackupCrawl(
                                                fw, repo, since, next_link,
                                                etag=etag, url=url, 
                                                copy_only=copy_only
                                                )
                                
                            else:
                                # Parse first
                                result = self.nextBackupCrawl(
                                                fw, repo, since, next_link,
                                                etag=etag, copy_only=copy_only
                                                )
                                    
                            url = self.getNextURL(result, next_link)
                                
                            if result[self.KEY_RL_REMAIN] == "0":
                                copy_only = True

                print "Done parsing old data."
                
        if result and result[self.KEY_RL_REMAIN] == "0":
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
        while url and result[self.KEY_RL_REMAIN] != "0":
            # Crawl next page
            result = self.nextCrawl(fw, url=url)
            url    = self.getNextURL(result)

        fw.close()

        if result and result[self.KEY_RL_REMAIN] == "0":
            self.endExecution()

    def nextBackupCrawl(self, fh, repo, since, 
                        next_link, etag=None, 
                        url=None, copy_only=False):
        result = None

        if not copy_only:
            if etag:
                if url:
                    result = self.crawlRepoLinks(url=url, etag=etag)
                else:
                    result = self.crawlRepoLinks(etag=etag)
            elif url:
                result = self.crawlRepoLinks(url=url)
            else:
                result = self.crawlRepoLinks()

        if result[self.KEY_STATUS_CODE] == 200:
            # New results from GitHub
            fh.write("# " + self.KEY_SINCE + ": %s\n" % result[self.KEY_SINCE])
            fh.write("# " + self.KEY_NEXT_LINK  + ": %s\n" % result[self.KEY_NEXT_LINK])
            fh.write("# " + self.KEY_ETAG  + ": %s\n" % result[self.KEY_ETAG])

            fh.write(json.dumps(result[self.KEY_CRAWLED_LINKS]) + "\n")
            fh.flush()
        
        elif result[self.KEY_STATUS_CODE] == 304:
            # Results didn't change since last crawling.
            # Get them from the backup file.
            fh.write("# " + self.KEY_SINCE + ": %s\n" % since)
            fh.write("# " + self.KEY_NEXT_LINK  + ": %s\n" % next_link)
            fh.write("# " + self.KEY_ETAG  + ": %s\n" % etag)
            
            fh.write(str(repo) + "\n")
            fh.flush()

        return result
    
    def nextCrawl(self, fh, url=None):
        result = None
        
        if url:
            result = self.crawlRepoLinks(url=url)
        else:
            result = self.crawlRepoLinks()

        if result[self.KEY_STATUS_CODE] == 200:
            # New results from GitHub
            fh.write("# " + self.KEY_SINCE + ": %s\n" % result[self.KEY_SINCE])
            fh.write("# " + self.KEY_NEXT_LINK  + ": %s\n" % result[self.KEY_NEXT_LINK])
            fh.write("# " + self.KEY_ETAG  + ": %s\n" % result[self.KEY_ETAG])

            fh.write(json.dumps(result[self.KEY_CRAWLED_LINKS]) + "\n")
            fh.flush()
            
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
        
        if resp.status_code != 304:
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
                    result[self.KEY_RL_REMAIN] = resp.headers[self.KEY_RL_REMAIN]
                
                if result[self.KEY_RL_REMAIN] == "0":
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
        else:
            # We already know these repos, skip them.
            print "Already crawled repo - skipping."
            
            # Extract remaining ratelimit.
            if self.KEY_RL_REMAIN in resp.headers:
                result[self.KEY_RL_REMAIN] = resp.headers[self.KEY_RL_REMAIN]
        
        result[self.KEY_CRAWLED_LINKS] = crawled_links
        result[self.KEY_COUNT] = len(crawled_links)
        
        return result

    def getKeyFromCrawlData(self, input_file, output_file,
                                  key=KEY_CLONE_URL):
        with open(input_file, 'r') as fr:
            with open(output_file, 'w') as fw:
                for l in fr.readlines():
                    if not self.isComment(l):
                        if l != "" and l != "[]\n":
                            # Found a list of repo dictionaries. Read it.
                            _list = json.loads(l)
                            for repo in _list:
                                fw.write(str(repo[key]).strip() + "\n")

    def endExecution(self):
        print "Ratelimit reached. Quitting..."
        sys.exit()
        
    def getNextURL(self, _dict, next_link=None):
        """
        Find the URL in _dict and return it.
        Empty string if it does not exist.
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
    
    def showRateLimit(self):
        resp = r.get(self.addOAuth(self.LINK_RATE_LIMIT))
            
        _dict = json.loads(resp.text)["resources"]
        
        print "Rate Limits:"
        print "core:"  , _dict["core"]
        print "search:", _dict["search"]

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