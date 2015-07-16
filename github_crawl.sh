#!/bin/sh

pgrep -f python\ main.py > /dev/null || python main.py crawlRepos crawled/data
