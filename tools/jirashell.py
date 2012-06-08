#!/usr/bin/env python

"""
Starts an interactive JIRA session in an ipython terminal. Script arguments
support changing the server and a persistent authentication over HTTP BASIC.
"""

import argparse
from getpass import getpass
from sys import exit
from jira.client import JIRA
from jira import __version__

def process_command_line():

    parser = argparse.ArgumentParser(description='Start an interactive JIRA shell with the REST API.')
    jira_group = parser.add_argument_group('JIRA server connection options')
    jira_group.add_argument('-s', '--server',
                            help='The JIRA instance to connect to, including context path.')
    jira_group.add_argument('-r', '--rest-path',
                            help='The root path of the REST API to use.')
    jira_group.add_argument('-v', '--rest-api-version',
                            help='The version of the API under the specified name.')

    basic_auth_group = parser.add_argument_group('BASIC auth options')
    basic_auth_group.add_argument('-u', '--username',
                                  help='The username to connect to this JIRA instance with.')
    basic_auth_group.add_argument('-p', '--password',
                                  help='The password associated with this user.')
    basic_auth_group.add_argument('-P', '--prompt-for-password', action='store_true',
                                  help='Prompt for the password at the command line.')

    oauth_group = parser.add_argument_group('OAuth options (for already-authenticated tokens)')
    oauth_group.add_argument('-at', '--access-token',
                             help='OAuth access token for the user.')
    oauth_group.add_argument('-ats', '--access-token-secret',
                             help='Secret for the OAuth access token')
    oauth_group.add_argument('-ck', '--consumer-key',
                             help='OAuth consumer key.')
    oauth_group.add_argument('-k', '--key-cert',
                             help='Private key to sign OAuth requests with (should be the pair of the public key\
                                   configured in the JIRA application link)')

    try:
        get_ipython
    except NameError:
        pass
    else:
        exit("Running ipython inside ipython isn't supported. :(")

    args = parser.parse_args()

    options = {}
    if args.server:
        options['server'] = args.server
    if args.rest_path:
        options['rest_path'] = args.rest_path
    if args.rest_api_version:
        options['rest_api_version'] = args.rest_api_version

    if args.prompt_for_password:
        args.password = getpass()

    basic_auth = (args.username, args.password) if args.username and args.password else ()

    oauth = {}
    if args.access_token:
        with open(args.key_cert, 'r') as key_cert_file:
            key_cert_data = key_cert_file.read()
        oauth = {
            'access_token': args.access_token,
            'access_token_secret': args.access_token_secret,
            'consumer_key': args.consumer_key,
            'key_cert': key_cert_data,
        }

    return options, basic_auth, oauth

def main():
    options, basic_auth, oauth = process_command_line()

    jira = JIRA(options=options, basic_auth=basic_auth, oauth=oauth)

    from IPython.frontend.terminal.embed import InteractiveShellEmbed

    ipshell = InteractiveShellEmbed(banner1='<JIRA Shell ' + __version__ + ' (' + jira.client_info() + ')>')
    ipshell("*** JIRA shell active; client is in 'jira'."
            ' Press Ctrl-D to exit.')

if __name__ == '__main__':
    status = main()
    exit(status)