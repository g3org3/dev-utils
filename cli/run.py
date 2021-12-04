#!/usr/bin/env python
import argparse
import os
import re
import requests as r
import signal
import subprocess
import sys
import yaml
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from emoji import emojize
from termcolor import colored


@dataclass
class Env:
  environment: any
  VERSION: str = "v0.1.1"

  @property
  def jira_host(self):
    return self.environment.get('jira').get('host')

  @property
  def jira_session(self):
    return self.environment.get('jira').get('session')

  @property
  def github_host(self):
    return self.environment.get('github').get('host')

  @property
  def github_main_branch(self):
    return self.environment.get('github').get('main_branch')

  @property
  def github_repo(self):
    return self.environment.get('github').get('repo')

  def __str__(self):
    return yaml.dump(self.environment, Dumper=yaml.Dumper)


def get_env(args: Namespace):
  env = {"jira": {"host": "api.atlassian.com"}, "github": {"host": "github.com", "main_branch": "main"}}
  home = os.environ['HOME']
  config_path = f'{home}/.jarc.yml'
  if os.path.isfile(config_path):
    with open(config_path) as fh:
      env = yaml.load(fh, yaml.Loader)
  else:
    print(colored("No config file found at ~/.jarc.yml", "yellow"))
  return Env(env)


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
    "--desc", "-d",
    help="Fetches the description from the ticket",
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
  jira = JiraApi(env, args)
  cli = Cli(args, env, jira)
  cli.run(parser)


def get_branch(args: Namespace) -> str:
  (error, branch) = shell('git rev-parse --abbrev-ref HEAD')
  if error:
    if args.verbose:
      print(f"branch-name: [{colored('failed', 'red')}]")
    exit(1)
  return branch


def shell(cmd: str):
  result = subprocess.Popen(cmd.split(' '), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  output = result.stdout.read().decode().strip()
  error = result.stderr.read().decode().strip()
  error = None if error == "" else error
  return (error, output)


def get_ticket_from_branch(args: Namespace):
  branch = get_branch(args)
  valid_branch_regex = r'^(s[0-9]+\/)?([A-Z]+-[0-9]+)(-\w+)?'
  branch_pattern = re.compile(valid_branch_regex)
  result = branch_pattern.search(branch)
  if not result:
    print(colored("Could not get details from your branch", "yellow"))
    exit(1)
  (sprint, ticket, desc) = result.groups()

  if args.verbose:
    print(f"sprint-number: [{colored(sprint, 'green')}]")
    print(f"ticket-id: [{colored(ticket, 'green')}]")

  return (branch, ticket)


@dataclass
class JiraApi:
  args: Namespace
  host: str
  cookies = {"JSESSIONID": None}
  proxies = {"https": None, "http": None}
  headers = {"user-agent": "curl/7.8.12"}

  def __init__(self, env: Env, args: Namespace) -> None:
    os.environ['NO_PROXY'] = '*'
    self.cookies['JSESSIONID'] = env.jira_session
    self.host = env.jira_host
    self.args = args

  def get(self, endpoint):
    url = f'https://{self.host}{endpoint}'
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
  jira: JiraApi

  def run(self, parser: ArgumentParser):
    if self.args.verbose:
      print(f"{self.args}\n\n{self.env}")

    if self.args.create_pr:
      self.create_pr()
    elif self.args.desc:
      self.desc()
    elif self.args.open:
      self.open()
    elif self.args.verbose:
      pass
    else:
      parser.print_help()

  def open(self):
    (branch, ticket) = get_ticket_from_branch(self.args)
    url = None
    if self.args.open == 'j':
      url = (
        f"https://{self.env.jira_host}/secure/RapidBoard.jspa"
        f"?rapidView=2704&view=detail&selectedIssue={ticket}"
      )
    elif self.args.open == 'jira':
      url = (
        f"https://{self.env.jira_host}/browse/"
        f"{ticket}"
      )
    elif self.args.open == 'pr':
      url = (
        f"https://{self.env.github_host}/"
        f"{self.env.github_repo}/compare/{self.env.github_main_branch}...dev:"
        f"{branch}"
      )
    else:
      print("valid options are: 'jira', 'pr'")
    if url:
      if self.args.verbose:
        print(url)
      os.system(f'xdg-open "{url}"')

  def desc(self):
    (branch, ticket) = get_ticket_from_branch(self.args)
    r = self.jira.get(f'/rest/api/2/issue/{ticket}?fields=summary,description')
    if r is None:
      exit(1)
    summary = r['fields']['summary']
    description = r['fields']['description']
    print(f"\n{emojize(':memo:')} {summary}")
    print("")
    print(emojize(description))

  def create_pr(self):
    (branch, ticket) = get_ticket_from_branch(self.args)
    link = (
      f"https://{self.env.github_host}/"
      f"{self.env.github_repo}/compare/{self.env.github_main_branch}...dev:"
      f"{branch}"
    )

    response = self.jira.get(f'/rest/api/2/issue/{ticket}?fields=summary')

    print("\nPull Request")

    if response:
      summary = response['fields']['summary']
      name = f"[{ticket}] - {summary}"
      copy_to_clipboard(name)
      print(f"name: {colored(name, 'yellow')} # copied to your clipboard!")

    print(f"link: {link}")
    open_link(link, press_enter_message=True)


def signal_handler(sig, frame):
  print('')
  sys.exit(0)


def open_link(link, press_enter_message=False):
  if press_enter_message:
    print("[press enter to open in browser ]")
    input()
  (error, machine) = shell('uname -s')
  if not error and machine == 'Linux':
    os.system(f'xdg-open "{link}"')
  elif not error and machine == 'Darwin':
    os.system(f'open "{link}"')
  else:
    print(f'could not detect your OS machine:[{machine}] error:[{error}]')


def copy_to_clipboard(text):
  (error, machine) = shell('uname -s')
  if not error and machine == 'Linux':
    os.system(f'echo -e "{text}" | xclip -i -selection clipboard')
  elif not error and machine == 'Darwin':
    os.system(f'echo -e "{text}" | pbcopy')
  else:
    print(f'could not detect your OS machine:[{machine}] error:[{error}]')


if __name__ == "__main__":
  signal.signal(signal.SIGINT, signal_handler)
  main()
