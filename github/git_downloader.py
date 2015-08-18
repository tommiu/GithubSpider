'''
Created on Aug 13, 2015

@author: Tommi Unruh
'''

import subprocess
import os
from time import sleep
import sys
import signal
import imp

import pdb

class GitDownloader(object):
    """
    Manages the download of git repositories.
    """
    def __init__(self, dir_path):
        self.OUT_DIR = dir_path
    
        if self.OUT_DIR[-1] != "/":
            self.OUT_DIR += "/"
            
        self.plugins = {} 
                
    def cloneAllFromFile(self, filename, linenumber=0):
        """
        Clone repositories from links, that are read from 'filename', starting
        at linenumber 'linenumber'.
        """
        linenumber = int(linenumber)
        self.interrupt = False
        
        def catchInterrupt(signum, frame):
            """
            Catch CTRL-C/D and exit in a safe manner.
            """
            file_path = self.OUT_DIR + "cloning_interrupted"
            print (
                "Stopped at line '%d'. Also wrote the linenumber to "
                "file '%s'."
                ) % (linenumber, file_path)
            
            # Write linenumber to file, so that the user can continue there
            # next time.
            with open(file_path, 'w') as fh:
                fh.write(str(linenumber) + "\n")
            
            self.interrupt = True
            
        with open(filename, 'r') as fh:
            # If specified skip lines in links-file.
            if linenumber > 1:
                self.goToLine(fh, linenumber)

            # Catch process-kill signal.
            signal.signal(signal.SIGTERM, catchInterrupt)
            
            # Also catch Ctrl-C/D.
            signal.signal(signal.SIGINT,  catchInterrupt)

            l = fh.readline()
            while l and not self.interrupt:
                try:
                    print "Trying link on line %d in file '%s'" % (linenumber, 
                                                                   filename)
                    self.cloneRepoLink(l.strip())
                
                except (
                    RepositoryExistsException, 
                    RepositoryDoesNotExistException
                    ) as err:
                        print str(err).strip()
                        print "Skipping..."
                    
                finally:
                    linenumber += 1
                    l = fh.readline()
            
            # Remove backup signal handlers.
            # SIG_DFL is the standard signal handle for any signal.
            signal.signal(signal.SIGTERM, signal.SIG_DFL)
            signal.signal(signal.SIGINT,  signal.SIG_DFL)
            
            if not self.interrupt:
                print "End of file reached, my work is done!"
            
    def cloneRepoLink(self, link):
        msg     = "Cloning repository: %s..." % link
        out_dir = self.OUT_DIR + link[link.rfind("/") + 1 : -4]

        print "%s" % msg,
        sys.stdout.flush()
        
        # Start cloning the repository from 'link' simply using 'git' from
        # the user's system PATH variable.
        process = subprocess.Popen(["git", "clone", link, out_dir], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        if stderr != "" and stderr != "\n" :
            if "already exists and is not an empty directory." in stderr:
                raise RepositoryExistsException(str(stderr))
            
            elif "does not exist" in stderr:
                raise RepositoryDoesNotExistException(str(stderr))
        
        if not self.interrupt:
            print "%s Done." % msg
        
        if stdout:
            print stdout
        
        # If any success handler was specified by the user,
        # execute it using the path of the downloaded repository as an argument.
        try:
            if not self.interrupt:
                self.runSuccessHandler(out_dir)
    
        except OSError as err:
            print err
        
    def goToLine(self, fh, linenumber):
        """
        Go to 'linenumber' of a huge text file in an (memory-)efficient way.
        """
        if linenumber < 1:
            raise IOError(
                "Specified linenumber '%d' is smaller than 1." % linenumber
                )

        fh.seek(0, os.SEEK_SET)

        # Skip lines until desired line is reached.
        for _ in range(0, linenumber - 1):
            read = fh.readline()
            if read == "":
                # Empty string represents EOF.
                raise OutOfScopeException(msg="goToLine error: ", 
                                          line=linenumber)

    def setSuccessHandler(self, package_path):
        """
        Load a python package, that will be executed each time a repository
        was successfully downloaded.
        """
        # Get module infos from module in 'package_path'.
        # For that, we need to split the path into its package and the module.
        # Example: example/dir/module.py
        # -> Name: module
        # -> [Path: example/dir]
        try:
            plugin_name = package_path[package_path.rfind("/")+1:-3]
            plugin_dir  = package_path[:package_path.rfind("/")]
            
            info = imp.find_module(plugin_name, [plugin_dir])
    
            self.plugins[package_path] = imp.load_module(plugin_name, *info)
            
        except Exception as err:
            raise OSError(err)
        
    def runSuccessHandler(self, dir_path):
        """
        Execute each specified success handler.
        """
        _files = os.listdir(dir_path)
        if self.plugins:
            for key in self.plugins:
                self.plugins[key].run(_files)

class RepositoryExistsException(BaseException):
    pass

class RepositoryDoesNotExistException(BaseException):
    pass

class OutOfScopeException(BaseException):
    def __init__(self, msg=None, line=None):
        if msg:
            self.message = msg
            
        if line:
            self.message += "Line %d is out of scope." % line
            
        else:
            self.message = (
                    "goToLine() was called with a linenumber, "
                    "which was out of scope."
                    )
        
    def __str__(self):
        return self.message