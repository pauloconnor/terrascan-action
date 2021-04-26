#!/usr/bin/env python3

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import git

GIT_WORKSPACE = "/github/workspace/"
TERRASCAN_PATH = "/usr/local/bin/terrascan"


def get_command_line_options(args):
    options = []

    if args.config_path:
        options.append("-c %s" % args.config_path)

    if args.iac_type:
        options.append("-i %s" % args.iac_type)

    if args.iac_version:
        options.append("--iac-version %s" % args.iac_version)

    if args.policy_path:
        options.append("-p %s" % args.policy_path)

    if args.policy_type:
        options.append("-t %s" % args.policy_type)

    if args.skip_rules:
        options.append("--skip-rules=%s" % args.skip_rules)

    if args.tag_lines == "true":
        options.append("-o json")

    return " ".join(options)


def get_dir_list(changed_only, src, path_ignore):
    dirs = []

    if changed_only == "true":
        event_path = os.environ.get("GITHUB_EVENT_PATH")
        event_data = ""
        with open(event_path) as f:
            event_data = json.load(f)
        if os.environ.get("GITHUB_EVENT_NAME") == "pull_request":
            base = event_data["pull_request"]["base"]["sha"]
        elif os.environ.get("GITHUB_EVENT_NAME") == "push":
            base = event_data["before"]
        else:
            base = ""

        repo = git.Repo(os.environ.get("GITHUB_WORKSPACE"))

        for item in repo.index.diff(str(base)):
            if str(item.a_path.parent) not in dirs:
                if path_ignore and (re.search(path_ignore, str(item.a_path.parent))):
                    continue
                dirs.append(str(item.a_path.parent))
    else:
        for file in Path(src).rglob("*.tf"):
            if file.parent not in dirs:
                if path_ignore and (re.search(path_ignore, str(file.parent))):
                    continue
                dirs.append(str(file.parent))
    return dirs


def parse_message(message):

    base_path = os.environ.get("GITHUB_WORKSPACE") + "/"
    root_dir = message["results"]["scan_summary"]["file/folder"]
    if message["results"]["violations"]:
        for violation in message["results"]["violations"]:
            if violation["severity"].upper() == "HIGH":
                level = "error"
            else:
                level = "warning"
            filename = os.path.join(
                os.path.dirname(root_dir),
                violation["file"],
            ).replace(base_path, "")
            line_number = violation["line"]
            error = "{} ({}) : {} ({}) - {} ({})".format(
                violation["rule_name"],
                violation["rule_id"],
                violation["resource_type"],
                violation["resource_name"],
                violation["description"],
                violation["category"],
            )
            print("::%s file=%s,line=%s::%s" % (level, filename, line_number, error))
        error = ""


def run_terragrunt(args):

    if not os.path.isfile(TERRASCAN_PATH):
        print("::debug::terrascan is required to perform this action")
        exit(1)

    options = get_command_line_options(args)
    dir_list = get_dir_list(args.changed_only, args.iac_dir, args.ignore_path)
    exit_code = 0
    print(options)
    for dir in dir_list:
        command_string = TERRASCAN_PATH + " scan " + options + " -d " + dir
        if args.debug:
            print(command_string)

        result = subprocess.run(
            [command_string],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
        )
        if result.stdout:
            if args.tag_lines == "true":
                parse_message(json.loads(result.stdout.decode("utf8")))
            else:
                print(result.stdout.decode("utf8"))
        elif result.stderr:
            print(result.stderr.decode("utf8"))
            sys.exit(2)

        if result.returncode > exit_code:
            exit_code = result.returncode
    if args.only_warn:
        exit(0)
    else:
        exit(exit_code)


def main():
    parser = argparse.ArgumentParser(description="Terragrunt GitHub action")

    parser.add_argument("--changed_only", default=os.environ.get("INPUT_CHANGED_ONLY"))
    parser.add_argument("--config_path", default=os.environ.get("INPUT_CONFIG_PATH"))
    parser.add_argument("--debug", default=os.environ.get("INPUT_DEBUG"))
    parser.add_argument("--iac_dir", default=os.environ.get("INPUT_IAC_DIR"))
    parser.add_argument("--iac_type", default=os.environ.get("INPUT_IAC_TYPE"))
    parser.add_argument("--iac_version", default=os.environ.get("INPUT_IAC_VERSION"))
    parser.add_argument("--ignore_path", default=os.environ.get("INPUT_IGNORE_PATH"))
    parser.add_argument("--only_warn", default=os.environ.get("INPUT_ONLY_WARN"))
    parser.add_argument("--policy_path", default=os.environ.get("INPUT_POLICY_PATH"))
    parser.add_argument("--policy_type", default=os.environ.get("INPUT_POLICY_TYPE"))
    parser.add_argument("--skip_rules", default=os.environ.get("INPUT_SKIP_RULES"))
    parser.add_argument(
        "--tag_lines",
        default=os.environ.get("INPUT_TAG_LINES"),
    )

    args = parser.parse_args()
    if args.debug:
        print(args)
    run_terragrunt(args)


if __name__ == "__main__":
    main()
