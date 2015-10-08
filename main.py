'''
Created on Jul 4, 2015

@author: Tommi Unruh
'''

from crawler import Crawler
import sys
from args_parser import ModeArgsParser
from github.git_downloader import GitDownloader, OutOfScopeException
import json

ARGS_HELP = "help"
ARGS_RATELIMIT   = "ratelimit"
ARGS_CRAWL_REPOS = "crawl"
ARGS_CLONE_REPOS = "clone"
ARGS_EXTRACT_KEYDATA = "extract"
ARGS_EXTRACTREPOS_FILTERED = "filter"

REPO_KEY_LANGUAGE   = "language"
DEFAULT_REPO_FILTER = {REPO_KEY_LANGUAGE: "PHP"}

REPO_ALLOWED_KEYS = [
                'issues_url', 'stargazers_count', 'forks_url', 'mirror_url', 
                'subscription_url', 'notifications_url', 'collaborators_url',
                'updated_at', 'private', 'pulls_url', 'issue_comment_url', 
                'labels_url', 'has_wiki', 'full_name', 'owner', 'statuses_url', 
                'id', 'keys_url', 'description', 'subscribers_count', 
                'tags_url', 'network_count', 'downloads_url', 'assignees_url', 
                'contents_url', 'has_pages', 'git_refs_url', 
                'open_issues_count', 'clone_url', 'watchers_count', 
                'git_tags_url', 'milestones_url', 'languages_url', 'size', 
                'homepage', 'fork', 'commits_url', 'releases_url', 
                'issue_events_url', 'archive_url', 'comments_url', 
                'events_url', 'contributors_url', 'html_url', 'forks', 
                'compare_url', 'open_issues', 'git_url', 'svn_url', 
                'merges_url', 'has_issues', 'ssh_url', 'blobs_url', 
                'git_commits_url', 'hooks_url', 'has_downloads', 'watchers', 
                'name', 'language', 'url', 'created_at', 'pushed_at', 
                'forks_count', 'default_branch', 'teams_url', 'trees_url', 
                'branches_url', 'subscribers_url', 'stargazers_url']

def main(argv):
    """
    Entry point of execution. Handles program arguments and
    acts accordingly. 
    """
    auth_file = "authentication"
    
    # Setup command line arguments.
    parser = ModeArgsParser()
    setupArgs(parser)
    
    flow    = None
    crawler = None
    
    try:
        flow = parser.parseArgs(argv[1], argv[2:])
        
        # Check if authentication file was specified.
        if "a" in flow:
            auth_file = flow["a"]
        elif "auth" in flow:
            auth_file = flow["auth"]
        
    except:
        parser.printHelp(argv[0])
        sys.exit()

    # Evaluate program arguments and start program.
    if flow[parser.KEY_MODE] == ARGS_HELP:
        parser.printHelp(argv[0])
    
    if flow[parser.KEY_MODE] == ARGS_RATELIMIT:
        crawler = Crawler(auth_file)
        _dict = crawler.getRateLimit()
        print "Rate Limits:"
        print "core:"  , _dict["core"]
        print "search:", _dict["search"]

    elif flow[parser.KEY_MODE] == ARGS_CRAWL_REPOS:
            crawler = Crawler(auth_file)
            
            if "ds" in flow or "dontskip" in flow:
                skip = False
            else:
                skip = True
            
            try:
                if "f" in flow:
                    _filter = flow["f"]
                    _filter = convertIntoDict(_filter)
                
                elif "filter" in flow:
                    _filter = flow["filter"]
                    _filter = convertIntoDict(_filter)
                    
                else:
                    _filter = DEFAULT_REPO_FILTER
                    
            except Exception as err:
                print err
                
            finally:
                crawler.crawlRepos(flow["in"], skip, _filter=_filter)

    elif flow[parser.KEY_MODE] == ARGS_EXTRACT_KEYDATA:
        if "k" in flow or "key" in flow:
            try:
                key = flow["k"]
            except:
                key = flow["key"]
            finally:
                Crawler.getKeyFromCrawlData(flow["in"], flow["out"], key)
            
        else:
            Crawler.getKeyFromCrawlData(flow["in"], flow["out"])
    
    elif flow[parser.KEY_MODE] == ARGS_EXTRACTREPOS_FILTERED:
        try:
            _filter = flow["f"]
        except:
            _filter = flow["filter"]
        finally:
            Crawler.extractReposFiltered(flow["in"], flow["out"], _filter)
            
    # cloning repos
    elif flow[parser.KEY_MODE] == ARGS_CLONE_REPOS:
        downloader = GitDownloader(flow["out"])
        
        try:
            _line = flow["l"]
        except:
            try:
                _line = flow["_line"]
            except:
                _line = 0
        
        delete = False
        if "d" in flow or "delete" in flow:
            delete = True

        plugin = False
        try:
            downloader.setSuccessHandler(flow["p"])
            plugin = True

        except Exception as err:
            try:
                downloader.setSuccessHandler(flow["plugin"])
                plugin = True
            except:
                pass
        
        if delete and not plugin:
            print (
                "A combination of -d/--delete without -p/--plugin is "
                "not allowed."
                )
            sys.exit()
        
        try:
            downloader.cloneAllFromFile(
                                    flow["in"], 
                                    linenumber=_line, 
                                    delete=delete
                                    )
            
        except OutOfScopeException as err:
            print (
                "The specified line number '%s' in parameter '-l/--line' is "
                "out of scope for file '%s'." % (_line, flow["in"])
                )

def convertIntoDict(_str):
    try:
        _dict = json.loads(_str)
        
    except:
        _dict = None
    
    if isinstance(_dict, dict):
        valid = True
        for key in _dict:
            if key not in REPO_ALLOWED_KEYS:
                valid = False
                invalid_key = key
                break
            
        if valid:
            return _dict
        
        else: 
            raise ValueError("Dictionary key '%s' is not a valid "
                             "key of a repository" % invalid_key)
    
    raise ValueError("Filter should be specified as a "
                     "JSON-decoded python dictionary.")

def setupArgs(parser):
    """
    Setup command line arguments combinations.
    """
    # Ratelimit: ratelimit
    explanation = "Check your ratelimit."
    parser.addArgumentsCombination(ARGS_RATELIMIT, 
                                   optional_args=[["a=", "auth"]],
                                   explanation=explanation)
    
    # Help: help
    explanation = "Print this help."
    parser.addArgumentsCombination(ARGS_HELP, explanation=explanation)
    
    # Crawl repos: crawl -in file -out file (-s/--skip, -a/--auth, -f/--filter)
    explanation = (
                "Crawl repositories from Github.com "
                "to file specified with \"-in\". "
                "-ds/--dontskip can be used to first check for updates "
                "for already crawled repositories in file. "
                "The input file will be renamed to input_file_backup. "
                "Use -f/--filter followed by a python dictionary to "
                "specify a filter to only save information of repositories "
                "which apply to that filter. "
                "The default filter is {\"language\": \"PHP\"}, but any "
                "python dictionary is allowed."
                )
    parser.addArgumentsCombination(
                                ARGS_CRAWL_REPOS,
                                [["in=", None]],
                                [
                            ["ds", "dontskip"], 
                            ["a=", "auth"], 
                            ["f=", "filter"]
                            ],
                                explanation=explanation
                                )
    
    explanation = (
                "Extract the value associated with '-k/--key' from "
                "crawled repositories in '-in' and write it to '-out'."
                "Default for 'k/--key' is 'clone_url', which "
                "specifies the URL for cloning a repository."
                )
    # Extract key data: extract -in file -out file (-k/--key)
    parser.addArgumentsCombination(ARGS_EXTRACT_KEYDATA,
                                   [["in=", None], ["out=", None]], 
                                   [["k=", "key"]],
                                   explanation=explanation
                                   )
    
    explanation = (
                "Filter the repositories from file '-in' and write "
                "filtered repositories to '-out'. '-f/--filter' specifies "
                "the filter criterion. Currently supported: stars:=x, stars:>x "
                "stars:<x, stars:>x <y. size:>x, size:<y, size:>x <y, "
                "nofilter:."
                )
    # Filter repositories: filter -in file -out file -f/--filter filter_arg
    parser.addArgumentsCombination(ARGS_EXTRACTREPOS_FILTERED,
                                   [
                                ["in=", None], 
                                ["out=", None], 
                                ["f=", "filter"]
                                ],
                                   explanation=explanation)
    
    explanation = (
                "Clone repositories from the links specified in file '-in' "
                "to directory '-out'. Use optional parameter -l/--line to "
                " specify the line number from which to start in file '-in'. "
                "-p/--plugin can be specified to "
                "execute a python package for each repository, right after one "
                "was downloaded. -d/--delete can then additionally be used, to "
                "also delete the repository after having examined it using "
                "-p/--plugin."
                )
    # Clone repositories: clone -in file -out dir 
    #                                    -p/--plugin python_package_path
    #                                    -l/--line   line_number
    parser.addArgumentsCombination(ARGS_CLONE_REPOS,
                                   [
                                ["in=", None], 
                                ["out=", None], 
                                ],
                                   [
                                ["p=", "plugin"], 
                                ["d", "delete"], 
                                ["l=", "line"]
                                ],
                                   explanation=explanation)

if __name__ == '__main__':
    main(sys.argv)