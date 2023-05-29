import os
import json
import shutil
import hashlib
import fnmatch
import re
import logging

from typing_extensions import Literal
from typing import List, Sequence, Tuple


from .getrepos import get_clones, get_package_repo_mapping


include_dir = "./includes"


rez_paths = [
    "/Volumes/rnd/oa_pipeline.v2/packages/int/",
    # "/Volumes/rnd/oa_pipeline.v2/packages/ext/",
    # "/Volumes/rnd/toolbox/system",
]


default_config = {
    "include": [
        "./python",
        "./maya",
    ],
    "extraPaths": [
        "/Volumes/profiles/tahmed/Repos/sapper_excludes/completion/maya/2018/py",
    ],
    "venvPath": "/Volumes/profiles/tahmed/.virtualenvs",
    "venv": "devenv379",
    "pythonVersion": 3.7,
    "pythonPlatform": "Linux",
    "typeCheckingMode": "on",
}


no_translate = [
    "/Volumes/rnd/oa_pipeline.v2/packages/ext/*",
    "/Volumes/rnd/toolbox/*",
    "/Volumes/profiles/tahmed/.oa-packages-v2/*",
    "/opt/*",
]

ignore_paths = [
    "/Volumes/rnd/oa_pipeline.v2/packages/dev/talha.ahmed/*"
]


def ensure_dir(directory=include_dir, empty=True):
    if empty:
        if os.path.exists(directory):
            shutil.rmtree(directory)
    if not os.path.exists(directory):
        os.makedirs(directory)
    return directory


def get_paths(var="PYTHONPATH"):
    paths = os.environ.get(var, "")
    paths = paths.split(os.pathsep)
    return paths


def get_config(infile="./pyrightconfig.json"):
    if os.path.isfile(infile):
        with open(infile) as _fp:
            config = json.load(_fp)
            config.update(default_config)
            return config
    return default_config.copy()


def breakdown_by_package_name(path) -> Tuple[str, str, str]:
    pattern = "(%s)" % "|".join(rez_paths)
    pattern += "/?([^/]+)"
    pattern += "(/.*)"
    match = re.match(pattern, path)
    if match:
        return match.group(1), match.group(2), match.group(3)
    return "", os.path.basename(path), ""


def get_target_name(string):
    _, name, _ = breakdown_by_package_name(string)
    m = hashlib.sha256()
    m.update(string.encode("latin-1"))
    return name, m.hexdigest()[:6]


def localize_paths(target_dir, paths, do_symlinks=False):
    ensure_dir(target_dir)

    ignored = []
    target_paths = []
    for path in paths:
        if not os.path.exists(path):
            continue

        if any((fnmatch.fnmatch(path, ign) for ign in no_translate)):
            ignored.append(path)
            continue

        name, _h = get_target_name(path)
        _dir = os.path.join(target_dir, name)
        if not os.path.exists(_dir):
            os.makedirs(_dir)
        target_path = os.path.join(_dir, _h)

        try:
            if not os.path.exists(target_path):
                if do_symlinks:
                    os.symlink(path, target_path)
                else:
                    shutil.copytree(path, target_path)

            logging.info(f"{path} -> {target_path}")
            target_paths.append(target_path)

        except:
            pass

    return target_paths, ignored


def translate_to_repo_paths(paths: List[str], clone_dir=include_dir):
    translated, copied = [], []

    if not os.path.exists(clone_dir):
        os.makedirs(clone_dir)
    clones = get_clones(clone_dir)

    logging.info(f"number of clones: {len(clones)}")
    mapping = get_package_repo_mapping(clones if clones else None, clone_dir)

    for path in paths:
        if not os.path.exists(path):
            continue

        if any((fnmatch.fnmatch(path, ign) for ign in ignore_paths)):
            continue

        if any((fnmatch.fnmatch(path, ign) for ign in no_translate)):
            copied.append(path)
            continue

        package = breakdown_by_package_name(path)
        if package is None:
            copied.append(path)
            continue
        _, package_name, relpath = package

        repo = mapping.get(package_name)

        if repo is None:
            copied.append(path)
            continue

        workdir_rel = os.path.join(
            clone_dir,
            os.path.relpath(repo.working_dir, os.path.abspath(clone_dir)))

        found = False
        relpath = relpath.lstrip(os.sep)
        while relpath:
            fullpath = os.path.join(workdir_rel, relpath)
            if os.path.isdir(fullpath):
                translated.append(fullpath)
                logging.info(f"translating {package_name} to: {fullpath}")
                found = True
                break
            splits = relpath.split(os.sep, 1)
            if len(splits) <= 1:
                break
            relpath = splits[-1]

        if not found:
            copied.append(path)

    return translated, copied

def generate_pyright_conf(
    outfile: str = "./pyrightconfig.json",
    add_to: Sequence[str] = ("extraPaths",),
    method: Literal["repo", "localized"] = "repo"
):
    config = get_config()

    pythonpaths = get_paths()
    pythonpaths.extend(get_paths("BD_HOOKPATH"))

    if method == "localized":
        translated, ignored = localize_paths(include_dir, pythonpaths)
    else:
        translated, ignored = translate_to_repo_paths(pythonpaths)

    for field in add_to:
        config[field].extend(translated)
        config[field].extend(ignored)

    print("writing conf to %s ..." % outfile)
    with open(outfile, "w") as _fp:
        json.dump(config, _fp, indent=2)
