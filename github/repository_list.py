'''
Created on Jul 17, 2015

@author: Tommi Unruh
'''
import json
from github.repository import Repository
from github.exceptions import UnavailableRepoException

class RepositoryList(object):
    """
    Class representing a list of repositories from Github.
    """

    def __init__(self, url=None, etag=None, repos="[]", next_url=None):
        '''
        Constructor
        '''
        self.url   = url
        self.etag  = etag
        self.next_url = next_url

        self.setRepos(repos)

    def filter(self, session, _filter):
        """
        Remove repositories from list, that do not match filter.
        '_filter' should be a dictionary stating a value for each defined key.
        e.g. {"language": "PHP", "stargazers_count": 5}.
        
        Additionally, we get more details for each repository, because
        we query each repository individually.
        """
        filtered_repos = []
        for repo in self.repos:
            # Query repo and check filter.
            try:
                full_repo = session.getRepo(repo.getURL())
                
                if full_repo.filter(_filter):
                    filtered_repos.append(full_repo)
                    
            except UnavailableRepoException:
                # Skip repository
                pass
               
        self.repos = filtered_repos
        
    def __iadd__(self, other):
        self.repos.append(other)
        return self
    
    def __str__(self):
        """
        Get textual representation of list of repositories.
        """
        repos_decoded = []
        
        for repo in self.repos:
            repos_decoded.append(repo.getDict())
            
        return json.dumps(repos_decoded)
    
    def __iter__(self):
        """
        Iterate over the list of repositories in self.repos.
        """
        ctr = 0
        while ctr < len(self.repos):
            yield self.repos[ctr]
            ctr += 1
    
    def isEmpty(self):
        return True if not self.repos else False
    
    def getURL(self):
        return self.url
    
    def setURL(self, url):
        self.url = url
    
    def getEtag(self):
        return self.etag
    
    def setETag(self, etag):
        self.etag = etag
    
    def getNextURL(self):
        return self.next_url
    
    def setNextURL(self, next_url):
        self.next_url = next_url
        
    def setRepos(self, repos):
        self.repos = []
        
        if isinstance(repos, basestring):
            # 'repos' is given as a string.
            repos = json.loads(repos)
            
            self.repos = []
            for _dict in repos:
                # Transform each dictionary into a Repository object.
                self.repos.append(Repository(_dict))
            
            return True
            
        elif isinstance(repos, list):
            # 'repos' is given as a list (=already json-decoded).
            # Check if the list is populated with dictionaries or
            # Repository objects.
            for _obj in repos:
                if isinstance(_obj, dict):
                    # _obj is dict, transform it to Repository.
                    self.repos.append(Repository(_obj))
                
                elif isinstance(_obj, Repository):
                    # _obj already is Repository, just append it.
                    self.repos.append(_obj)

            return True

        raise Exception("Given value for 'repos' is not valid: '%s'." % (
                                                                repos
                                                                ))