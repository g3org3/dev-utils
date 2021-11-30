#!/usr/bin/env python
import argparse
import os
import re
import requests as r
import subprocess
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from termcolor import colored
from typing import Optional


@dataclass
class Env:
  VERSION: str
  SESSION: Optional[str] = None

def get_env(args: Namespace):
  env = {"SESSION": None, "VERSION": "0.1.0"}
  home = os.environ['HOME']
  config_path = f'{home}/.jarc'
  if os.path.isfile(config_path):
    with open(config_path) as fh:
      for line in fh.readlines():
        if '=' in line:
          key = line.split('=')[0].strip()
          value = line.split('=')[1].strip()
          env[key] = value
  else:
    if args.verbose:
      print("no config file found")
  return Env(env['VERSION'], env['SESSION'])


def main():
  parser = argparse.ArgumentParser(description="Dev cli helper")
  parser.add_argument(
    "--verbose", "-v",
    help="Show more information",
    action="store_true"
  )
  parser.add_argument(
    "--create-pr", "-c",
    help="Generate link to create a PR to be merged on the latest release branch",
    action="store_true"
  )
  parser.add_argument(
    "--how",
    help="Fetches the description from the jira ticket",
    action="store_true"
  )
  parser.add_argument(
    "--open", "-o",
    help="Open either github or jira",
  )
  # parser.add_argument(
  #   "--rebase", "-r",
  #   help="Rebase current branch with the latest release branch",
  #   action="store_true"
  # )
  # parser.add_argument(
  #   "--create-branch", "-b",
  #   help="Create new branch",
  # )
  # parser.add_argument(
  #   "--undo-commit", "-u",
  #   help="Undo the latest commit",
  #   action="store_true"
  # )
  # parser.add_argument(
  #   "--open-pr-in-browser", "-o",
  #   help="Open the PR of current branch",
  #   action="store_true"
  # )
  # parser.add_argument(
  #   "--new-jira-ticket", "-j",
  #   help="Create new jra ticket in backlog",
  # )
  args = parser.parse_args()
  env = get_env(args)
  cli = Cli(args, env)
  cli.run(parser)


def get_branch(args: Namespace) -> str:
  result = subprocess.Popen('git rev-parse --abbrev-ref HEAD'.split(' '), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  branch = result.stdout.read().decode().strip()
  if result.stderr.read().decode().strip() != '':
    if args.verbose:
      print(f"branch-name: [{colored('failed', 'red')}]")
    exit(1)
  return branch


def get_branch_and_details(args: Namespace):
  branch = get_branch(args)
  branch_pattern = re.compile('^s([0-9])+/CFCCON-([0-9]+)_?((_?[a-zA-Z0-9]+)*)')
  result = branch_pattern.search(branch)
  if not result:
    print("Could not get details from your branch")
    exit(1)
  (sprint, ticket, desc, extra) = result.groups()
  if args.verbose:
    print(f"sprint-number: [{colored(sprint, 'green')}]")
    print(f"ticket-id: [{colored(ticket, 'green')}]")

  return (branch, ticket, sprint)


@dataclass
class JiraApi:
  args: Namespace
  cookies = {"JSESSIONID": None}
  proxies = {"https": None, "http": None}
  headers = {"user-agent": "curl/7.8.12"}

  def __init__(self, jsessionid: str, args: Namespace) -> None:
    os.environ['NO_PROXY'] = '*'
    self.cookies['JSESSIONID'] = jsessionid
    self.args = args

  def get(self, endpoint):
    url = f'https://jiradbg.deutsche-boerse.de{endpoint}'
    res = r.get(url, proxies=self.proxies, cookies=self.cookies, headers=self.headers)
    if res.status_code != 200:
      if self.args.verbose:
        print(colored(res.text, 'red'))
      print(colored(f"Tried to call jira but we received {res.status_code}", 'yellow'))
      return None
    return res.json()


@dataclass
class Cli:
  args: Namespace
  env: Env

  def run(self, parser: ArgumentParser):
    if self.args.verbose:
      print(f"{self.args}\n{self.env}")

    if self.args.create_pr:
      self.create_pr()
    elif self.args.how:
      self.how()
    elif self.args.open:
      self.open()
    else:
      parser.print_help()

  def open(self):
    (branch, ticket, sprint) = get_branch_and_details(self.args)
    url = None
    if self.args.open == 'jira':
      url = (
        "https://jiradbg.deutsche-boerse.de/secure/RapidBoard.jspa"
        f"?rapidView=2704&view=detail&selectedIssue=CFCCON-{ticket}"
      )
    elif self.args.open == 'pr':
      url = (
        "https://github.deutsche-boerse.de/"
        "dev/cs.cfc_connect/compare/release/2204...dev:"
        f"{branch}"
      )
    else:
      print("valid options are: 'jira', 'pr'")
    if url:
      if self.args.verbose:
        print(url)
      os.system(f'xdg-open "{url}"')

  def how(self):
    (branch, ticket, sprint) = get_branch_and_details(self.args)
    if self.env.SESSION:
      jira = JiraApi(self.env.SESSION, self.args)
      r = jira.get(f'/rest/api/2/issue/CFCCON-{ticket}?fields=summary,description')
      summary = r['fields']['summary']
      description = r['fields']['description']
      print(summary)
      print(description)


  def create_pr(self):
    (branch, ticket, sprint) = get_branch_and_details(self.args)
    link = (
      "https://github.deutsche-boerse.de/"
      "dev/cs.cfc_connect/compare/release/2204...dev:"
      f"{branch}"
    )

    print("Pull Request")

    if self.env.SESSION:
      jira = JiraApi(self.env.SESSION, self.args)
      r = jira.get(f'/rest/api/2/issue/CFCCON-{ticket}?fields=summary')
      summary = r['fields']['summary']
      name = f"[#{ticket}] - {summary}"
      os.system(f'echo {name} | xclip -i -selection clipboard')
      print(f"name: {colored(name, 'yellow')} # copied to your clipboard!")
    print(f"link: {link}")
    os.system(f'xdg-open "{link}"')


if __name__ == "__main__":
  main()
