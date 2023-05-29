import json
import os
import re


from multiprocessing.pool import ThreadPool

import git
from git.repo import Repo
import github

from typing import Dict, List, Optional

from github.Repository import Repository


import logging


ORGANIZATION: str = "oneanimation-rnd"
TOKEN = None


def get_token() -> Optional[str]:
    global TOKEN
    if TOKEN is None:
        with open(os.path.expanduser("~/.confgen.json")) as fp:
            data = json.load(fp)
            TOKEN = data.get("gh_token")
    return TOKEN


def get_github() -> github.Github:
    return github.Github(get_token())


def get_repos(org: Optional[str] = None) -> List[Repository]:
    if org is None:
        org = ORGANIZATION
    gh = get_github()
    gh_org = gh.get_organization(org)  # type: ignore
    logging.info(f"Getting all repos from {org}")
    return list(gh_org.get_repos())


def clone_repos(repos: List[Repository], clone_dir="./clones") -> List[Repo]:
    pool = ThreadPool()

    def _clone_repo(repo: Repository):
        repo_dir = os.path.join(clone_dir, repo.full_name)
        clone_url = re.sub(
            "(https://)", r"\1%s:x-oauth-basic@" % TOKEN, repo.clone_url
        )
        if os.path.exists(repo_dir):
            local_clone = git.Repo(repo_dir)  # pyright: ignore
            remote = local_clone.remotes[0]
            url = remote.url.rsplit("@", 1)[-1]
            logging.info(f"Pulling {repo.default_branch} from {url}")
            remote.pull(repo.default_branch, force=True)
        else:
            url = clone_url.rsplit("@", 1)[-1]
            logging.info(f"Cloning from {url} to {repo_dir}")
            local_clone = git.Repo.clone_from(  # pyright: ignore
                clone_url, repo_dir
            )
        return local_clone

    if not os.path.exists(clone_dir):
        os.makedirs(clone_dir)

    results = {}
    for repo in repos:
        results[repo.full_name] = pool.apply_async(_clone_repo, args=(repo,))

    local_clones = []
    for res in results:
        val = results[res].get()
        local_clones.append(val)

    pool.close()
    return local_clones


def clone_all_repos(clone_dir="./clones") -> List[Repo]:
    repos = get_repos()
    return clone_repos(repos, clone_dir=clone_dir)


def get_package_name(repo: Repo) -> Optional[str]:
    repo_dir = repo.working_dir
    package_file = os.path.join(repo_dir, "package.py")
    if os.path.exists(package_file):
        with open(package_file) as fp:
            for line in fp.readlines():
                match = re.match(r"name\s*=\s*[\"'](.*)[\"']$", line)
                if match:
                    return match.group(1)


def get_clones(clone_dir="./clones", org: str = ORGANIZATION):
    clones = []
    org_dir = os.path.join(clone_dir, org)

    if not os.path.exists(org_dir):
        logging.info(f"{org_dir} does not exists")
        return clones

    for dirname in os.listdir(org_dir):
        dirname = os.path.join(org_dir, dirname)

        if not os.path.isdir(dirname):
            continue

        try:
            repo = Repo(dirname)
            clones.append(repo)
        except Exception:
            pass

    return clones


def get_package_repo_mapping(
    repos: Optional[List[Repo]] = None, clone_dir: str = "./clones"
) -> Dict[str, Repo]:
    if repos is None:
        repos = clone_all_repos(clone_dir)
    mapping = {}
    for repo in repos:
        package_name = get_package_name(repo)
        if package_name:
            mapping[package_name] = repo
    return mapping


if __name__ == "__main__":
    clones = get_clones()
    for package, repo in get_package_repo_mapping(clones).items():
        logging.info(package, os.path.basename(repo.working_dir))
