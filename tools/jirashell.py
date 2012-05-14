#!/usr/bin/env python

"""
Starts an interactive JIRA session in an ipython terminal. Script arguments
support changing the server and a persistent authentication over HTTP BASIC.
"""

import argparse
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

    basic_auth = (args.username, args.password) if args.username and args.password else ()

    return options, basic_auth

def main():
    options, basic_auth = process_command_line()

    jira = JIRA(options=options, basic_auth=basic_auth)

    from IPython.frontend.terminal.embed import InteractiveShellEmbed

    ipshell = InteractiveShellEmbed(banner1='<JIRA Shell ' + __version__ + ' (' + jira.client_info() + ')>')
    ipshell("*** JIRA shell active; client is in 'jira'."
            ' Press Ctrl-D to exit.')

if __name__ == '__main__':
    status = main()
    exit(status)