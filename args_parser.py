'''
Created on Jul 19, 2015

@author: Tommi Unruh
'''

import re
import sys
from itertools import izip

class ArgsParser(object):
    '''
    classdocs
    '''

    KEY_MODE  = "mode"
    KEY_ORDER = "order"
    KEY_ARGS_OPTIONAL  = "optional_args"
    KEY_ARGS_NECESSARY = "necessary_args"
    KEY_ARGS_OPTIONAL_WVAL  = "optional_args_w_value"
    KEY_ARGS_NECESSARY_WVAL = "necessary_args_w_value"

    ARGS_RATELIMIT   = "ratelimit"
    ARGS_CRAWL_REPOS = "crawl"
    ARGS_EXTRACT_KEYDATA = "extract"
    ARGS_EXTRACTREPOS_FILTERED = "filter"
    
    def __init__(self):
        '''
        Constructor
        '''
        self.combinations = {}
        
        # Setup argument combinations.
        # Each combination has its own dictionary.
        
        # Ratelimit: ratelimit
        self.addArgumentsCombination(self.ARGS_RATELIMIT)
        
        # Crawl repos: crawl -in file -out file (-s/--skip)
        self.addArgumentsCombination(self.ARGS_CRAWL_REPOS, [
                                                        ["in=", None]
                                                        ], [["ds", "dontskip"],])

        # Extract key data: extract -in file -out file (-k/--key)
        self.addArgumentsCombination(self.ARGS_EXTRACT_KEYDATA, [
                                                        ["in=", None], 
                                                        ["out=", None]
                                                        ], [["k=", "key"]])
        
        # Extract key data: extract -in file -out file (-k/--key)
        self.addArgumentsCombination(self.ARGS_EXTRACTREPOS_FILTERED, [
                                                ["in=", None], 
                                                ["out=", None], 
                                                ["f=", "filter"]
                                                ])
    
    def addArgumentsCombination(self, mode, necessary_args=None, 
                                optional_args=None, order=None):
        """
        Prepare a dictionary of necessary and optional values,
        with and without values respectively.
        """
        self.combinations[mode] = {
                self.KEY_ORDER: [],
                self.KEY_ARGS_OPTIONAL:  [],
                self.KEY_ARGS_NECESSARY: [],
                self.KEY_ARGS_OPTIONAL_WVAL:  [],
                self.KEY_ARGS_NECESSARY_WVAL: [],
                }
        
        # Parse necessary arguments.
        if necessary_args:
            # Parse short versions first
            for s_arg, l_arg in necessary_args:
                # If a key ends in "=", we expect it to 
                # be a key-value pair.
                if s_arg:
                    if s_arg[-1] == "=":
                        (self.combinations[mode]
                         [self.KEY_ARGS_NECESSARY_WVAL].append(
                                            [s_arg[:-1], l_arg]
                                            ))
                        
                    else:
                        # Key does not end in "=".
                        (self.combinations[mode]
                         [self.KEY_ARGS_NECESSARY].append(
                                            [s_arg, l_arg]
                                            ))
                    
                elif not l_arg:
                    # s_arg and l_arg are both None, which is not correct.
                    raise NoneTypeCombinationException()
        
        # Parse optional arguments.        
        if optional_args:
            # Parse short versions first
            for s_arg, l_arg in optional_args:
                # If a key ends in "=", we expect it to 
                # be a key-value pair.
                if s_arg:
                    if s_arg[-1] == "=":
                        (self.combinations[mode]
                         [self.KEY_ARGS_OPTIONAL_WVAL].append(
                                            [s_arg[:-1], l_arg]
                                            ))
                        
                    else:
                        # Key does not end in "=".
                        (self.combinations[mode]
                         [self.KEY_ARGS_OPTIONAL].append(
                                            [s_arg, l_arg]
                                            ))
                    
                elif not l_arg:
                    # s_arg and l_arg are both None, which is not correct.
                    raise NoneTypeCombinationException()
                
        # Setup order of arguments. 
        # This is important for returning the results.
        # Arguments on the command line can be mixed up!
        if order:
            self.combinations[mode][self.KEY_ORDER] = order
            
        else:
            # No order specified, so build the default one:
            # Necessary arguments first, as specified. Then optional ones.
            if necessary_args:
                for s_arg, l_arg in necessary_args:
                    if s_arg[-1] == "=":
                        self.combinations[mode][self.KEY_ORDER].append(
                                                                s_arg[:-1]
                                                                )
                    else:
                        self.combinations[mode][self.KEY_ORDER].append(
                                                                s_arg
                                                                )
                        
            if optional_args:
                for s_arg, l_arg in optional_args:
                    if s_arg[-1] == "=":
                        self.combinations[mode][self.KEY_ORDER].append(
                                                                s_arg[:-1]
                                                                )
                    else:
                        self.combinations[mode][self.KEY_ORDER].append(
                                                                s_arg
                                                                )
                
    def parseArgs(self, args):
        # Expects args[0] to be a mode value, 
        # i.e. it should not have a minus sign in front of it.
        if args[0].strip()[0] == "-":
            raise WrongFormatException(args[0])
        
        # Parse mode:
        if args[0] == self.ARGS_RATELIMIT:
            # No options needed - skip them.
            return self.getOpts(self.ARGS_RATELIMIT, args[1:])
            
        elif args[0] == self.ARGS_CRAWL_REPOS:
            # Options: -in=value -out=value (-s, --skip)
            return self.getOpts(self.ARGS_CRAWL_REPOS, args[1:])
        
        elif args[0] == self.ARGS_EXTRACT_KEYDATA:
            return self.getOpts(self.ARGS_EXTRACT_KEYDATA, args[1:])
        
        elif args[0] == self.ARGS_EXTRACTREPOS_FILTERED:
            return self.getOpts(self.ARGS_EXTRACTREPOS_FILTERED, args[1:])
        
        else:
            raise WrongModeException(args[0])
        
    def getOpts(self, mode, args):
        """
        Parse args and return them in order, as specified by self.combinations.
        """
        # Remark: re_short_option will also match long options.
        # Therefore, look for long options first, then for short options.
        re_long_option  = re.compile("--([a-zA-Z]+)")
        re_short_option = re.compile("-([a-zA-Z]+)")
#         re_long_option_val  = re.compile("--([a-zA-Z]+)(?:[\s=]([^-]+))")
#         re_short_option_val = re.compile("-([a-zA-Z]+)(?:[\s=]([^-]+))")
        
        result = {}
        skip   = False
        parsed_vals = []
        
#         combination = self.combinations[mode]
        for i, _ in enumerate(args):
            if not skip:
                key      = None
                full_key = None
                
                # Check for long option.
                long_hit = re_long_option.match(args[i])
                
                if long_hit:
                    key      = long_hit.group(1)
                    full_key = long_hit.group(0)
                    
                else:
                    # No long option found, check for short option.
                    short_hit = re_short_option.match(args[i])
                    if short_hit:
                        key      = short_hit.group(1)
                        full_key = short_hit.group(0)
                
                if not key:
                    # No short, no long option found.
                    raise WrongFormatException(args[i])
                    
                val = self.parseNextKeyValue(args, i)
                    
                if val:
                    skip = True
                
                # Check if key-val pair is correct for this command.
                is_permitted = self.argPermitted(full_key, val, mode)
                
                if is_permitted:
                    result[key] = val
                    
            else:
                skip = False
        
        # Are necessary arguments still missing?
        if self.isMissingArgs(self.combinations[mode]):
            raise MissingParameterException(self.combinations[mode])
        
        # Add mode to result
        parsed_vals.append(mode)
        
        # Bring arguments in order.
        for elem in self.combinations[mode][self.KEY_ORDER]:
            if elem in result:
                parsed_vals.append(result[elem])
        
        return parsed_vals
    
    def parseNextKeyValue(self, args, i):
        """
        Check next argument for a given value for this key.
        """
        val = None
        
        if len(args) > i + 1:
            parsed_val = args[i+1]
            if len(parsed_val) > 1 and parsed_val[0:2] != "--" and parsed_val[0] != "-":
                val = parsed_val
                
            elif len(parsed_val) == 1 and parsed_val != "-":
                val = parsed_val
        
        return val
    
    def isMissingArgs(self, combination):
        if (
        combination[self.KEY_ARGS_NECESSARY] or 
        combination[self.KEY_ARGS_NECESSARY_WVAL]
        ):
            return True
    
    def argPermitted(self, key, val, mode):
        """
        Check if a given key-val pair is correctly specified.
        If so, remove it from the combination dictionary, so that 
        it will be ignored for further parsing.
        """
        KEY_SHORT = 0
        KEY_LONG  = 1
        
        combination = self.combinations[mode]
        
        found_permitted_arg = False
        orig_key = key
        key_type = -1
        
        # clear key from leading minuses. (e.g. --abc or -abc = abc)
        if key[0] == "-":
            key = key[1:]
            key_type = KEY_SHORT
            
        if key[0] == "-":
            key = key[1:]
            key_type = KEY_LONG
            
        # Check if value is permitted in keys which do not need a value.
        for i, combinations_key in enumerate(
                                combination[self.KEY_ARGS_NECESSARY]
                                ):
            if (
            key_type == KEY_SHORT and combinations_key[KEY_SHORT] == key or 
            key_type == KEY_LONG  and combinations_key[KEY_LONG] == key
            ):
                # Key found.
                # Was a value given?
                if val:
                    raise UnneccessaryValueException(orig_key)
                else:
                    combination[self.KEY_ARGS_NECESSARY].pop(i)
                    found_permitted_arg = True
        
        if not found_permitted_arg:
            # Check if value is permitted in keys which do need a value.
            for i, combinations_key in enumerate(
                                    combination[self.KEY_ARGS_NECESSARY_WVAL]
                                    ):
                if (
                key_type == KEY_SHORT and combinations_key[KEY_SHORT] == key or 
                key_type == KEY_LONG  and combinations_key[KEY_LONG] == key
                ):
                    # Key found.
                    # Was a value given?
                    if val:
                        combination[self.KEY_ARGS_NECESSARY_WVAL].pop(i)
                        found_permitted_arg = True
                    else:
                        raise MissingValueException(orig_key)
        
        if not found_permitted_arg:
            # Check if value is permitted in optional keys 
            # which do not need a value.
            for i, combinations_key in enumerate(
                                    combination[self.KEY_ARGS_OPTIONAL]
                                    ):
                if (
                key_type == KEY_SHORT and combinations_key[KEY_SHORT] == key or 
                key_type == KEY_LONG  and combinations_key[KEY_LONG] == key
                ):
                    # Key found.
                    # Was a value given?
                    if val:
                        raise UnneccessaryValueException(orig_key)
                    else:
                        combination[self.KEY_ARGS_OPTIONAL].pop(i)
                        found_permitted_arg = True
                        
        if not found_permitted_arg:
            # Check if value is permitted in optional keys
            # which do need a value.
            for i, combinations_key in enumerate(
                                    combination[self.KEY_ARGS_OPTIONAL_WVAL]
                                    ):
                if (
                key_type == KEY_SHORT and combinations_key[KEY_SHORT] == key or 
                key_type == KEY_LONG  and combinations_key[KEY_LONG] == key
                ):
                    # Key found.
                    # Was a value given?
                    if val:
                        combination[self.KEY_ARGS_OPTIONAL_WVAL].pop(i)
                        found_permitted_arg = True
                    else:
                        raise MissingValueException(orig_key)
        
        if not found_permitted_arg:
            raise WrongParameterException(mode, orig_key)
        
        return found_permitted_arg
    
class WrongModeException(BaseException):
    def __init__(self, val=None):
        self.val = val
        
    def __str__(self):
        if self.val:
            return "Mode '%s' is not implemented." % self.val
        
        else:
            return "Given mode is not implemented."

class WrongFormatException(BaseException):
    def __init__(self, val=None):
        self.val = val
        
    def __str__(self):
        if self.val:
            return "Argument '%s' is malformed." % self.val
        
        else:
            return "An argument is malformed."
        
class NoneTypeCombinationException(BaseException):
    def __str__(self):
        return "Combination cannot contain combination [None, None]."
    
class MissingValueException(BaseException):
    def __init__(self, val=None):
        self.val = val
        
    def __str__(self):
        if self.val:
            return "You did not specify a value for key '%s'." % self.val
        
        else:
            return "You did not specify a necessary value."
        
class MissingParameterException(BaseException):
    def __init__(self, combinations=None):
        self.combinations = combinations
        
    def __str__(self):
        KEY_ARGS_NECESSARY      = "necessary_args"
        KEY_ARGS_NECESSARY_WVAL = "necessary_args_w_value"
        
        if self.combinations:
            missing = ""
            for _list in self.combinations[KEY_ARGS_NECESSARY]:
                if _list[1] != None:
                    missing += "-%s/--%s, " % (_list[0], _list[1])
                else:
                    missing += "-%s, " % (_list[0])
                    
            for _list in self.combinations[KEY_ARGS_NECESSARY_WVAL]:
                if _list[1] != None:
                    missing += "-%s/--%s, " % (_list[0], _list[1])
                else:
                    missing += "-%s, " % (_list[0])
            
            missing = missing[:-2]
            return "Missing parameters: %s"  % missing
        
        else:
            return "Missing parameters. Aborting..."
        
class UnneccessaryValueException(BaseException):
    def __init__(self, val=None):
        self.val = val
        
    def __str__(self):
        if self.val:
            return (
                "You did specify a value for key '%s',"
                " but it does not need one." % self.val
                )
        
        else:
            return (
                "You did specify a value for a key,"
                " which does not need one."
                )
            
class WrongParameterException(BaseException):
    def __init__(self, mode, param):
        self.mode  = mode
        self.param = param
        
    def __str__(self):
        return (
            "Parameter '%s' is not allowed for command '%s'." % (
                                            self.param, self.mode
                                            )
            )
