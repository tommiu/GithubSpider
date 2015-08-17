'''
Created on Jul 21, 2015

@author: Tommi Unruh
'''

import requests as r
import getpass
import json
import os

class OAuthManager(object):
    """
    Manages creation and loading/parsing of authorization data for Github.com.
    """

    KEY_OAUTH = "OAuth"
    KEY_USER_AGENT = "user_agent"

    def __init__(self, filename=None):
        '''
        Constructor
        '''
        self.FILE  = filename
        self.AUTH  = None
    
    def getAuthData(self):
        if not self.AUTH:
            # OAuth not found, try to parse it from file.
            self.parseAuthentication(self.FILE)

        return self.AUTH
    
    def parseAuthentication(self, filename):
        try:
            with open (filename, 'r') as fh:
                # Parse first line, should be OAuth token.
                oauth = fh.readline().strip()
                # Parse second line, should be user agent.
                user_agent = fh.readline().strip()

                if oauth == "" or user_agent == "":
                    raise AuthException()
                
                self.setAuth(oauth, user_agent)

        except IOError:
            raise AuthFileNotFoundException()
        
    def createAuth(self):
        print (
            "Authentication file not found! This is probably your first use.\n"
            "We need to install an OAuth token for this crawler to work.\n"
            "This token does not need ANY access to your Github account.\n"
            "You can create one manually on https://github.com/settings/tokens\n"
            "or let me create one for you. However, you will need to specify\n"
            "your github username and password once. It will not be remembered "
            "or transfered somewhere else than github."
            )
        
        manual_oauth = False
        user_input   = self.getValidUserInput(
                                    "Do you want to enter one manually? [y/N]", 
                                    ["y", "Y", "N", "n"], 
                                    default="N"
                                    )
        
        if user_input.lower() == "y" :
            manual_oauth = True
        
        oauth    = None
        username = None
        
        if manual_oauth:
            oauth    = raw_input("Please enter your OAuth token: ").strip()
            username = raw_input("Please enter your Github email: ").strip()
        else:
            print (
                "Alright, let's create an OAuth token for your "
                "Github account and this application!"
                )
            
            oauth, username = self.createOAuthUntilSuccess()

        with open(self.FILE, 'w') as fh:
            fh.write(oauth.strip()    + "\n")
            fh.write(username.strip() + "\n")
        
        print (
            "OAuth file \"authentication\" successfully written!\n"
            "Future executions will automatically read your authentication data"
            " from that file."
            )
        
        self.setAuth(oauth, username)
    
    def createOAuthUntilSuccess(self):
        """
        Repeat asking the user for username/password, until a valid
        combination is specified. This data will be used to create an OAuth
        token for the 'username' account.
        """
        username = raw_input("Please enter your Github email: ")
        password = getpass.getpass("Please enter your Github password: ")
            
        oauth = self.createOAuthToken(username, password)

        return (oauth, username)

    def createOAuthToken(self, username, password, header=None):
        """
        Request Github API for OAuth token creation.
        'header' can be used to pass extra headers, which are necessary for
        two-factor authentication.
        """
        url = "https://api.github.com/authorizations"

        payload = {
                "scopes": [],
                "note": "githubSpider token."
                }
        
        resp = r.post(url,
                      auth=(username, password),
                      data=json.dumps(payload),
                      headers=header)

        oauth = self.processOAuthResponse(resp, username, password)
        
        return oauth
    
    def processOAuthResponse(self, resp, username, password):
        decoded = json.loads(resp.text)
        oauth = None
        
        if resp.status_code == 201:
            # Success.
            print (
                "OAuth successfully created in file 'authentication'.\n"
                "Remember: Do not transfer your OAuth token to anybody!"
                )
            oauth = decoded["token"]
            
        elif resp.status_code == 422:
            # OAuth already exists.
            print (
                "Error: OAuth already exists for this application.\n"
                "Visit https://github.com/settings/tokens and delete\n"
                "the githubSpider token. Then, please try again."
                )

        elif resp.status_code == 401:
            # Bad credentials or two-factor authentication.
            # Check for two-factor authentication header: 
            # "X-GitHub-OTP: required; :2fa-type", 
            # where 2fa-type = "sms" or other case
            
            KEY_TWO_FACTOR = "X-GitHub-OTP"
            if KEY_TWO_FACTOR in resp.headers:
                two_factor_header = resp.headers[KEY_TWO_FACTOR]
                
                # Check if two-factor-authentication is done via SMS or App.
                method = None
                if two_factor_header.find("sms") != -1:
                    method = "via SMS"
                else:
                    method = "via your Github application"
                    
                print (
                    "You setup two-factor authentication. You should get "
                    "the one-time password %s shortly." % method
                    )
                
                two_factor_pw = raw_input(
                                    "Please enter your one-time password: "
                                    )
                
                header = {KEY_TWO_FACTOR: two_factor_pw}
                
                # Query OAuth creation again, this time send username, password
                # and one-time password.
                oauth = self.createOAuthToken(username, password, header)
                
            else:
                # Bad credentials.
                print (
                    "Error: Bad credentials, try again."
                    )

                self.createOAuthUntilSuccess()
            
        elif resp.status_code == 403:
            # API rate limit exceeded.
            print (
                "Your Github API rate limit is already exceeded. "
                "Cannot query API for OAuth creation until rate limit is reset."
                )
            
        if not oauth:
            raise OAuthCreationException()
        
        return oauth
    
    def getValidUserInput(self, msg, valid_answers, default=None):
        """
        Ask user to input data until he entered a valid input.
        If 'default' is given, it will be returned on no user input (=user 
        just input "\n").
        """
        if default:
            valid_answers.append("")
            
        user_input = raw_input(msg)
        while not self.isValidUserInput(user_input, valid_answers):
            user_input = raw_input(msg)
        
        if user_input == "" and default:
            user_input = default
        
        return user_input
        
    def isValidUserInput(self, user_input, valid_answers):
        for answer in valid_answers:
            if user_input == answer:
                return True
            
        return False
    
    def setAuth(self, oauth, user_agent):
        self.testAuth(oauth)
        
        self.AUTH = {
                self.KEY_OAUTH: oauth,
                self.KEY_USER_AGENT: user_agent
                }
        
    def testAuth(self, oauth_token):
        url    = "https://api.github.com"
        header = {
                "Authorization": "token %s" % (oauth_token)  
                }
        
        resp = r.get(url, headers=header)
        
        if resp.status_code != 200:
            print (
                "Found bad credentials in authentication "
                "file 'authentication'."
                )
            
            user_input = self.getValidUserInput(
                                    "Do you want to delete it? [Y/n]", 
                                    ["y", "Y", "N", "n"], 
                                    default="Y"
                                    )
            
            if user_input.lower() == "y":
                msg = "Deleting authentication file..."
                print "%s\r" % (msg), 
                
                os.remove(self.FILE)
        
                print "%s Done." % (msg)
                
                raise AuthException()
            
            else:
                print "You chose to not delete the authentication data."
                
                raise NoCredentialsException()

        
### Exceptions
class AuthException(BaseException):
    def __str__(self):
        return "No allowed authentication found in file 'authentication'."
    
class AuthFileNotFoundException(BaseException):
    def __str__(self):
        return "Authentication file not found. Expecting file 'authentication'."
    
class OAuthCreationException(BaseException):
    def __str__(self):
        return "Failed to create OAuth token."
    
class NoAuthException(BaseException):
    def __str__(self):
        return (
            "No OAuth or user agent available. "
            "Did you specify or parse them before?"
            )
        
class NoCredentialsException(BaseException):
    def __str__(self):
        return "No credentials given."