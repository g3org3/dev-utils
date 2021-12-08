#!/usr/bin/env python
import argparse
import json
import os
import re
from typing import Tuple
import requests as r
import signal
import subprocess
import sys
import yaml
import inquirer
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from emoji import emojize
from datetime import datetime
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
  def jira_project_key(self):
    return self.environment.get('jira').get('project_key')

  @property
  def github_host(self):
    return self.environment.get('github').get('host')

  @property
  def github_main_branch(self):
    return self.environment.get('github').get('main_branch')

  @property
  def github_repo(self):
    return self.environment.get('github').get('repo')

  def set_session(self, value):
    self.environment['jira']['session'] = value

  def __str__(self):
    return yaml.dump(self.environment, Dumper=yaml.Dumper, sort_keys=False)

HOME = os.environ['HOME']
GLOBAL_CONFIG_PATH = f'{HOME}/.jarc.yml'

def get_env(args: Namespace) -> Env:
  env = {
    "version": "1",
    "jira": {"host": "api.atlassian.com", "session": "", "project_key": ""},
    "github": {"host": "github.com", "main_branch": "main", "repo": ""}
  }

  if os.path.isfile(GLOBAL_CONFIG_PATH):
    with open(GLOBAL_CONFIG_PATH) as fh:
      result = yaml.load(fh, yaml.Loader)
      if result:
        env = result
  else:
    print(colored(f"No config file found at {GLOBAL_CONFIG_PATH}", "yellow"))
  return Env(env)


def main():
  parser = argparse.ArgumentParser(prog="Dev Utils", description="Dev cli helper")
  parser.add_argument(
    "--verbose", "-v",
    help="Show more information",
    action="store_true"
  )
  parser.add_argument(
    "--pr", "-p",
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
    help="Open jira ticket or pr in github",
    choices=['jira','pr']
  )
  parser.add_argument(
    "--branch", "-b",
    help="List the available branches and checkout",
    nargs="?",
    const='*',
  )
  parser.add_argument(
    "--jira_ticket", "-j",
    help="specify the jira ticket to avoid reading the branch name"
  )
  parser.add_argument(
    "--save-session", "-s",
    help="Save jira session cookie"
  )
  parser.add_argument(
    "--update", "-u",
    help="Update dev-utils repo",
    action="store_true"
  )
  parser.add_argument(
    "--version",
    action="version",
    version='%(prog)s 0.3.0'
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


def shell(cmd: str, cwd=None, err_exit=False):
  result = subprocess.Popen(cmd.split(' '), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
  output = result.stdout.read().decode().strip()
  error = result.stderr.read().decode().strip()
  error = None if error == "" else error

  if err_exit and error:
    print(colored(error, 'red'))
    exit(1)

  if err_exit and not error:
    return output

  return (error, output)


def get_ticket_from_branch(args: Namespace, env: Env) -> Tuple[str, str]:
  if args.jira_ticket:
    ticket_regex = r'([a-zA-Z]+)?-?([0-9]+)'
    ticket_pattern = re.compile(ticket_regex)
    result = ticket_pattern.search(args.jira_ticket)
    if result.groups:
      number = result.group(2)
      if number:
        sprint = None
        ticket = f'{env.jira_project_key}-{number}'
        if args.verbose:
          print(f"sprint-number: [{colored(sprint, 'green')}]")
          print(f"ticket-id: [{colored(ticket, 'green')}]")
        return (sprint, ticket)

  branch = get_branch(args)
  valid_branch_regex = r'(s[0-9]+\/)?([A-Z]+-[0-9]+)(-\w+)?'
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

    if self.args.pr:
      self.pr()
    elif self.args.desc:
      self.desc()
    elif self.args.open:
      self.open()
    elif self.args.branch:
      self.branch()
    elif self.args.save_session:
      self.save_session()
    elif self.args.update:
      self.update()
    elif self.args.verbose:
      pass
    else:
      parser.print_help()

  def update(self):
    dev_utils_path = f'{HOME}/code/dev-utils'
    pip = f'{dev_utils_path}/.direnv/python-3.8.2/bin/pip'
    output = shell('git status --porcelain', cwd=dev_utils_path, err_exit=True)
    if output == "":
      print("Pulling latest changes")
      (err, output) = shell('git pull origin master', cwd=dev_utils_path)
      print("Installing dependencies")
      shell(f'{pip} install -r requirements.txt')
      print(f'status [{colored("done")}]')

  def open(self):
    (branch, ticket) = get_ticket_from_branch(self.args, self.env)
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

  def save_session(self):
    self.env.set_session(self.args.save_session)
    with open(GLOBAL_CONFIG_PATH, 'w') as fh:
      fh.write(f"{self.env}")
      print(f"update rc [{colored('done', 'green')}]")

  def desc(self):
    (branch, ticket) = get_ticket_from_branch(self.args, self.env)
    r = self.jira.get(f'/rest/api/2/issue/{ticket}?') #fields=summary,description
    if r is None:
      exit(1)
    summary = r['fields']['summary']
    description = r['fields']['description']
    points = r['fields']['customfield_10006']
    points = f'({points}) ' if points else ''
    github = r['fields']['customfield_11100']
    pr_status = github.split(', details=PullRequestOverallDetails')[0].split('state=')[1]
    pr_status = colored(f'{pr_status} ', 'yellow')
    comments = r['fields']['comment']
    owner = None

    # for k in r['fields'].keys():
    #   print(f"{k}|| {r['fields'][k]}")
    print(f"\n{emojize(':memo:')} {pr_status}{points}{summary}")
    if owner:
      print(f"owner: {owner}")
    print("")
    print(emojize(description))
    for c in comments['comments']:
      display_name = c['author']['displayName']
      body = c['body']
      updated = datetime.strptime(c['updated'], '%Y-%m-%dT%H:%M:%S.%f%z').strftime('%Y-%m-%d %H:%M %z')
      print(f'{colored(updated, "blue")} {display_name}: {body}')

  def branch(self):
    output = shell('git branch', err_exit=True)
    branches = [''.join(branch.split('*')).strip() for branch in output.split('\n')]
    if self.args.branch != '*':
      branches = [branch for branch in branches if self.args.branch in branch]
    questions = [
      inquirer.List('branch', message="What branch?", choices=branches)
    ]
    answers = inquirer.prompt(questions)
    branch = answers.get('branch')
    output = shell('git status --porcelain --untracked-files=no', err_exit=True)
    if output=="":
      shell(f"git checkout {branch}", err_exit=True)
    else:
      print(colored('Expected clean directory, please commit or stash your pending changes', 'yellow'))
      print(output)

  def pr(self):
    (branch, ticket) = get_ticket_from_branch(self.args, self.env)
    link = (
      f"https://{self.env.github_host}/"
      f"{self.env.github_repo}/compare/{self.env.github_main_branch}...dev:"
      f"{branch}"
    )

    response = self.jira.get(f'/rest/api/2/issue/{ticket}?fields=summary,customfield_10006')

    print("\nPull Request")

    if response:
      summary = response['fields']['summary']
      points = response['fields']['customfield_10006']
      name = f"[{ticket}] - ({points}) {summary}"
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
