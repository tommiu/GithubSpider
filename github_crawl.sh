#!/bin/sh

pgrep -f python\ /media/shared_data/workspace/githubSpider/main.py > /dev/null || python /media/shared_data/workspace/githubSpider/main.py repo_links crawled/links
