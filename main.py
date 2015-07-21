'''
Created on Jul 4, 2015

@author: Tommi Unruh
'''

from crawler import Crawler
import sys
from args_parser import ModeArgsParser

USAGE_ARGS = [
        ("ratelimit", "", "Show current rate limit"),
        ("links\t"    , "", "Crawl repository cloning links."),
#         ("-w", "--write", "Activate the custom logging function.\n"
#         "\t\t\t\tIf you do not specify your own custom logger, then the standard\n"
#         "\t\t\t\tcustom logger will be used. It creates HTML pages from the\n"
#         "\t\t\t\tvulnerability scanning results."),
        ("-q", "--query"  , "Specify a GitHub search query for the link " 
         "crawling.\n\t\t\t\tThe default value is \"language:PHP\""),
        ("-d", "--days", "(Necessary for 'crawlDays' command.)\n"
         "\t\t\t\tSpecify a start and end date for the link "
         "crawling\n\t\t\t\twhich respects the creation day of repositories.\n"
         "\t\t\t\tThe search query will be repeated for every day in [start, end].\n"
         "\t\t\t\tExample: -d '2015-05-15,2015-05-20' will\n"
         "\t\t\t\ttrigger search queries for five days."),
        ("-h", "--help"  , "Print this help."),
        ]

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
    # Setup command line arguments.
    parser = ModeArgsParser()
    setupArgs(parser)
    crawler = Crawler()
    
    flow = parser.parseArgs(argv[1], argv[2:])
    
    if flow[0] == ARGS_HELP:
        parser.printHelp(argv[0])
    
    if flow[0] == ARGS_RATELIMIT:
        _dict = crawler.getRateLimit()
        print "Rate Limits:"
        print "core:"  , _dict["core"]
        print "search:", _dict["search"]

    elif flow[0] == ARGS_CRAWL_REPOS:
            if len(flow[1:]) == 2:
                crawler.crawlRepos(flow[1], skip=False)
            else:
                crawler.crawlRepos(flow[1])
                
    elif flow[0] == ARGS_EXTRACT_KEYDATA:
        if len(flow[1:]) == 3:
            crawler.getKeyFromCrawlData(flow[1], flow[2], flow[3])
        else:
            crawler.getKeyFromCrawlData(flow[1], flow[2])
    
    elif flow[0] == ARGS_EXTRACTREPOS_FILTERED:
        if len(flow[1:]) == 3:
            crawler.extractReposFiltered(flow[1], flow[2], flow[3])

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
                                ARGS_CRAWL_REPOS, [["in=", None]],
                                [["ds", "dontskip"],],
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