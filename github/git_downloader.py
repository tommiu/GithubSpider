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

import shutil

import pexpect

class GitDownloader(object):
    """
    Manages the download of git repositories.
    """
    def __init__(self, dir_path):
        self.OUT_DIR = dir_path
    
        if self.OUT_DIR[-1] != "/":
            self.OUT_DIR += "/"
            
        self.plugins = {} 
                
    def cloneAllFromFile(self, filename, linenumber=0, delete=False):
        """
        Clone repositories from links, that are read from 'filename', starting
        at linenumber 'linenumber'.
        """
        clone_count    = 0
        linenumber     = int(linenumber)
        self.interrupt = False
        
        if delete:
            print (
                "Cloning was called with 'delete' specified. After cloning "
                "and processing a repository, it will be deleted again to " 
                "free space."
                )
        
        def catchInterrupt(signum, frame):
            """
            Catch CTRL-C/D and exit in a safe manner.
            """
            file_path = self.OUT_DIR + "cloning_interrupted"
            
            # Write linenumber to file, so that the user can continue there
            # next time.
            with open(file_path, 'w') as fh:
                fh.write(str(filename) + "\n")
                fh.write(str(linenumber) + "\n")
                
            print (
                "Stopped at line '%d'. Cloned %d repositories.\n" 
                "Also wrote path of the link file "
                " and the linenumber to file '%s'."
                ) % (linenumber, clone_count, file_path)

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
                out_dir = None
                try:
                    print "Trying link on line %d in file '%s'" % (linenumber, 
                                                                   filename)
                    out_dir = self.cloneRepoLink(l.strip(), linenumber)
                    clone_count += 1
                    # If any success handler was specified by the user,
                    # execute it using the path of the 
                    # downloaded repository as an argument.
                    try:
                        if not self.interrupt:
                            # If a plugin was specified to process
                            # the repository, it will be run.
                            self.runSuccessHandler(out_dir)
            
                    except OSError as err:
                        print err
                
                except pexpect.TIMEOUT:
                    print "Timed out."
                    print "Skipping..."

                # EOF = process finished in unhandled way.
                except pexpect.EOF:
                    clone_count += 1
                
                except (
                    RepositoryExistsException, 
                    RepositoryDoesNotExistException,
                    CredentialsExpectedException
                    ) as err:
                        print err.message
                        print "Skipping..."
                        
                        try:
                            out_dir = err.out_dir
                        
                        # CredentialsExpectedException does not
                        # have a 'out_dir' variable.
                        except:
                            pass

                finally:
                    linenumber += 1
                    l = fh.readline()
                    
                    if delete and out_dir:
                        # Delete repository.
                        print "Deleting directory '%s'." % out_dir
                        shutil.rmtree(out_dir)
            
            # Remove backup signal handlers.
            # SIG_DFL is the standard signal handle for any signal.
            signal.signal(signal.SIGTERM, signal.SIG_DFL)
            signal.signal(signal.SIGINT,  signal.SIG_DFL)
            
            if not self.interrupt:
                print "End of file reached, my work is done!"
        
    def cloneRepoLink(self, link, int_test):
        msg     = "Cloning repository: %s..." % link
         
        last_slash_index  = link.rfind("/")
        second_last_index = link.rfind("/", 0, last_slash_index)
         
        repo_name   = link[last_slash_index + 1 : -4]
        author_name = link[second_last_index + 1 : last_slash_index]
         
        # reponame_authorname-format enables us to clone repositories of
        # the same name, but of different authors.
        out_dir = self.OUT_DIR + author_name + "_" + repo_name
 
        print "%s" % msg
        sys.stdout.flush()
         
        # Start cloning the repository from 'link' simply using 'git' from
        # the user's system PATH variable. 
        # 1 hour max. per repository until timeout.
        process = pexpect.spawn("git", ["clone", link, out_dir], 3600)
        expectation = process.expect([
                            'Username',
                            'already exists and is not an empty directory',
                            'does not exist'
                            ])
        
        if expectation == 0:
            raise CredentialsExpectedException()
        
        elif expectation == 1:
            raise RepositoryExistsException(
                                        process.before + process.after, 
                                        out_dir
                                        )
        
        elif expectation == 2:
            raise RepositoryDoesNotExistException(
                                        process.before + process.after, 
                                        out_dir
                                        )
        
        return out_dir        

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
        if self.plugins:
            _files = os.listdir(dir_path)
            for key in self.plugins:
                self.plugins[key].run(_files)


class CredentialsExpectedException(BaseException):
    def __init__(self, msg=None):
        if msg:
            self.message = msg
            
        else:
            self.message = (
                    "Login credentials were requested."
                    )

class RepositoryExistsException(BaseException):
    def __init__(self, msg=None, out_dir=None):
        if msg:
            self.message = msg
            
        else:
            self.message = (
                    "Repository does exist already."
                    )
            
        if out_dir:
            self.out_dir = out_dir

class RepositoryDoesNotExistException(BaseException):
    def __init__(self, msg=None, out_dir=None):
        if msg:
            self.message = msg
            
        else:
            self.message = (
                    "Repository is not accessible on GitHub.com."
                    )
            
        if out_dir:
            self.out_dir = out_dir
            


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
