'''
Created on Jul 4, 2015

@author: Tommi Unruh
'''

from crawler import Crawler
import sys
import getopt

USAGE_ARGS = [
        ("ratelimit", "", "Show current rate limit"),
        ("links\t"    , "", "Crawl repository cloning links."),
#         ("-w", "--write", "Activate the custom logging function.\n"
#         "\t\t\t\tIf you do not specify your own custom logger, then the standard\n"
#         "\t\t\t\tcustom logger will be used. It creates HTML pages from the\n"
#         "\t\t\t\tvulnerability scanning results."),
        ("-q", "--query"  , "Specify a GitHub search query for the link" 
         "crawling.\n\t\t\t\tThe default value is \"language:PHP\""),
        ("-h", "--help"  , "Print this help."),
        ]

ARGS_RATELIMIT   = "ratelimit"
ARGS_CRAWL_LINKS = "crawl1000"

def main(argv):
    """
    Entry point of execution. Handles program arguments and
    acts accordingly. 
    """
    crawler = Crawler()
    
    flow = controlFlow(argv)
    
    if flow[0] == ARGS_RATELIMIT:
        crawler.showRateLimit()
        
    elif flow[0] == ARGS_CRAWL_LINKS:
        if len(flow) == 2:
            crawler.crawlSearching(flow[1])
        else:
            crawler.crawlSearching()

def controlFlow(argv):
    """
    Handle command line arguments.
    """
    # argv[1] determines code control flow.
    if len(argv) < 2:
        usage(argv[0])
        sys.exit(0)
    
    query = None
    
    try:
        opts, _ = getopt.getopt(argv[2:], "hq:", ["help", "query="])

    except getopt.GetoptError as err:
        print str(err)
        usage(argv[0])
        sys.exit(0)
    
    for o, v in opts:
        if o in (USAGE_ARGS[2][0], USAGE_ARGS[2][1]):
            if v:
                query = v
            else:
                usage(argv[0])
                sys.exit(0)
        # -h, --help
        elif o in(USAGE_ARGS[-1][0], USAGE_ARGS[-1][1]):
            usage(argv[0])
            sys.exit(0)
        ## -i, --ignore
        #elif o in(USAGE_ARGS[1][0], USAGE_ARGS[1][1]):
        #    ignore_arg = v
    
    if argv[1] == ARGS_RATELIMIT:
        return [ARGS_RATELIMIT,]
    elif argv[1] == ARGS_CRAWL_LINKS:
        return [ARGS_CRAWL_LINKS, query] if query else [ARGS_CRAWL_LINKS,]
    
    else:
        usage(argv[0])
        sys.exit(0)

def usage(path):
    """
    Prints help.
    """
    usage = ("[ratelimit/-h]")
    
    # for each option available, construct its usage string
    for option, longoption, description in USAGE_ARGS:
        usage += "\n\t%s%s%s\t:\t%s\n" % (
                                    option, 
                                    ", " if longoption else "", 
                                    longoption, 
                                    description
                                    )

    slash_count = path.count("/")
    
    # shorten program path if necessary for readability
    if slash_count:        
        slash_index = path.rfind("/")
        
        if slash_count > 2:
            path = ".../" + path[slash_index+1:]
            
    print "Usage: " + path + " " + usage

if __name__ == '__main__':
    main(sys.argv)