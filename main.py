'''
Created on Jul 4, 2015

@author: Tommi Unruh
'''

from crawler import Crawler
import sys
from args_parser import ModeArgsParser

ARGS_HELP = "help"
ARGS_RATELIMIT   = "ratelimit"
ARGS_CRAWL_REPOS = "crawl"
ARGS_EXTRACT_KEYDATA = "extract"
ARGS_EXTRACTREPOS_FILTERED = "filter"

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
            
        crawler = Crawler(auth_file)
        
    except:
        parser.printHelp(argv[0])
        sys.exit()
        
    if flow[parser.KEY_MODE] == ARGS_HELP:
        parser.printHelp(argv[0])
    
    if flow[parser.KEY_MODE] == ARGS_RATELIMIT:
        _dict = crawler.getRateLimit()
        print "Rate Limits:"
        print "core:"  , _dict["core"]
        print "search:", _dict["search"]

    elif flow[parser.KEY_MODE] == ARGS_CRAWL_REPOS:
            if "ds" in flow or "dontskip" in flow:
                skip = False
            else:
                skip = True
            
            crawler.crawlRepos(flow["in"], skip)
                
    elif flow[parser.KEY_MODE] == ARGS_EXTRACT_KEYDATA:
        if "k" in flow or "key" in flow:
            try:
                key = flow["k"]
            except:
                key = flow["key"]
            finally:
                crawler.getKeyFromCrawlData(flow["in"], flow["out"], key)
            
        else:
            crawler.getKeyFromCrawlData(flow["in"], flow["out"])
    
    elif flow[parser.KEY_MODE] == ARGS_EXTRACTREPOS_FILTERED:
        try:
            _filter = flow["f"]
        except:
            _filter = flow["filter"]
        finally:
            crawler.extractReposFiltered(flow["in"], flow["out"], _filter)

def setupArgs(parser):
    """
    Setup command line arguments combinations.
    """
    # Ratelimit: ratelimit
    explanation = "Check your ratelimit."
    parser.addArgumentsCombination(ARGS_RATELIMIT, explanation=explanation)
    
    # Help: help
    explanation = "Print this help."
    parser.addArgumentsCombination(ARGS_HELP, explanation=explanation)
    
    # Crawl repos: crawl -in file -out file (-s/--skip)
    explanation = (
                "Crawl repositories from Github.com "
                "to file specified with \"-in\". "
                "-ds/--dontskip can be used to first check for updates "
                "for already crawled repositories in file. "
                "The input file will be renamed to input_file_backup."
                )
    parser.addArgumentsCombination(
                                ARGS_CRAWL_REPOS,
                                [["in=", None]],
                                [["ds", "dontskip"], ["a=", "auth"]],
                                explanation=explanation
                                )
    
    explanation = (
                "Extract the value associated with '-k/--key' from "
                "crawled repositories in '-in' and write it to '-out'."
                "Default for 'k/--key' is 'stargazers_count', which "
                "states how often a repository got stared."
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
                "the filter criterion. Currently supported: stars==5, stars=>2 "
                "stars=<5, stars=>2 <10 etc."   
                )
    # Filter repositories: filter -in file -out file -f/--filter filter_arg
    parser.addArgumentsCombination(ARGS_EXTRACTREPOS_FILTERED,
                                   [
                                ["in=", None], 
                                ["out=", None], 
                                ["f=", "filter"]
                                ],
                                   explanation=explanation)

if __name__ == '__main__':
    main(sys.argv)