'''
Created on Jul 17, 2015

@author: Tommi Unruh
'''

import requests
import json

from exceptions import *
from github.repository_list import RepositoryList
from github.repository import Repository
from time import sleep

class Session(object):
    """
    This class saves the user's authorization infos and is able to do requests
    to the Github API on behalf of the authorized user.
    """

    SLEEP = 0.5

    URL_API   = "https://api.github.com"
    URL_REPOS      = URL_API + "/repositories"
    URL_SEARCH     = URL_API + "/search/repositories"
    URL_RATE_LIMIT = URL_API + "/rate_limit"
    
    KEY_ETAG = "ETag"
    KEY_RL_REMAIN = "X-RateLimit-Remaining"
    
    STATUS_UNAVAILABLE = 403

    def __init__(self, OAuth=None, user_agent=None):
        """
        Setup session.
        """
        self.HEADERS = {}
        
        if OAuth and user_agent:
            self.setOAuth(OAuth)
            self.setUserAgent(user_agent)
            
            self.HEADERS = {
                'User-Agent':    user_agent,
                'Authorization': "token %s" % OAuth
            }

        elif not OAuth:
            print (
                "No authorization token given, continuing unauthenticated.\n"
                "Unauthenticated requests are limited to 60 per hour, while\n"
                "authenticated requests are limited to 5000 per hour."
                )
    
    def getRatelimit(self):
        """
        Request Github API for ratelimit info for this session.
        """
        resp = self.sessionRequestGet(self.URL_RATE_LIMIT)
        _dict = json.loads(resp.text)

        if resp.status_code == 200:
            return _dict["resources"]
        else:
            raise Exception("Encountered a problem. Github answered with"
                            ":\n%s" % _dict)
            
        return _dict

    def getRepos(self, since=0, url=None):
        """
        Get a list of repositories.
        """
        response = None
        if url:
            response = self.sessionRequestGet(url)
        else:
            url = self.URL_REPOS + "?since=" + str(since)
            response = self.sessionRequestGet(url)
        
        etag  = response.headers[self.KEY_ETAG]
        repos = json.loads(response.text)
        next_url = response.links["next"]["url"]
        
        repos = RepositoryList(url, etag, repos, next_url)
        
        return repos
    
    def getRepo(self, url):
        """
        Query a single repository.
        """
        response = self.sessionRequestGet(url)
        
        return Repository(response.text)
    
    def update(self, repository_list):
        """
        Query API for an updated list of 'repository_list'.
        """
        header = {"If-None-Match": repository_list.getEtag()}
        response = self.sessionRequestGet(repository_list.getURL(), header)

        if response.status_code == 200:
            # Found update
            
            etag  = response.headers[self.KEY_ETAG]
            repos = json.loads(response.text)
            next_url = response.links["next"]["url"]
        
            repository_list.setETag(etag)
            repository_list.setRepos(repos)
            repository_list.setNextURL(next_url)
            
            return True
        
        return False
        
    def sessionRequestGet(self, url, headers=None):
        """
        Send a get-request with all session-headers.
        """
        try:
            if headers:
                header = self.HEADERS.copy()
                header.update(headers)
    
                response = requests.get(url, headers=header)
            else:
                response = requests.get(url, headers=self.HEADERS)
            
            if response.status_code == self.STATUS_UNAVAILABLE:
                if response.headers[self.KEY_RL_REMAIN] == 0:
                    # Ratelimit 0 reached.
                    raise RatelimitExceededException()
                
                else:
                    # Unavailable resource
                    raise UnavailableRepoException()
        
        except requests.exceptions.ConnectionError as err:
            print err
            print "Sleeping %d seconds and retrying with same URL." % self.SLEEP
            sleep(0.5)
            response = self.sessionRequestGet(url, headers)
            
        return response

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
    
    def setOAuth(self, OAuth):
        self.OAuth = OAuth
    
    def setUserAgent(self, user_agent):
        self.user_agent = user_agent
        
    def setPerPage(self, per_page):
        per_page = int(per_page)
        
        if per_page:
            self.per_page = per_page
        else:
            raise ValueError("'per_page' parameter could not be set.")