#!/usr/bin/python

import pexpect
import sys

def main(args):
    if len(args) != 3:
        print "Wrong arguments. Expected (in order): in_file_path out_directory_path line_number"
        sys.exit()
    in_path, out_path, linenumber = args
    
    processes = []
    for _ in xrange(4):
        processes.append(
                spawnCloner(in_path, out_path, linenumber)
                )

    for process in processes:
        process.expect(pexpect.EOF)

def spawnCloner(in_path, out_path, linenumber):
    process = pexpect.spawn("python main.py clone -in %s -out %s -l %s" % (in_path, out_path, linenumber),timeout=None, ignore_sighup=False)
    process.logfile = sys.stdout
    
    return process

main(sys.argv[1:])
