import os
import json
import shutil
import hashlib
import fnmatch
import re


# TODO:


include_dir = "./includes"


rez_paths = [
    "/Volumes/rnd/oa_pipeline.v2/packages/int/",
    "/Volumes/rnd/oa_pipeline.v2/packages/ext/",
    "/Volumes/rnd/toolbox/system",
]


default_config = {
    "include": [
        "./python",
        "./maya",
        "./",
    ],
    "extraPaths": [
        "/Volumes/profiles/tahmed/Repos/sapper_excludes/completion/maya/2018/py",
    ],
    "venvPath": "/Volumes/profiles/tahmed/.virtualenvs",
    "venv": "devenv39",
    "pythonVersion": 3.9,
    "pythonPlatform": "Linux",
    "typeCheckingMode": "on",
}


ignore_paths = [
    "/Volumes/rnd/oa_pipeline.v2/packages/ext/*",
    "/Volumes/rnd/toolbox/*",
    "/Volumes/profiles/tahmed/.oa-packages-v2/*",
    "/opt/*",
    "/Volumes/rnd/oa_pipeline.v2/packages/dev/talha.ahmed/*",
]


def ensure_dir(directory=include_dir, empty=True):
    if empty:
        if os.path.exists(directory):
            shutil.rmtree(directory)
    if not os.path.exists(directory):
        os.makedirs(directory)
    return directory


def get_paths(var="PYTHONPATH"):
    paths = os.environ[var]
    paths = paths.split(os.pathsep)
    return paths


def get_config(infile="./pyrightconfig.json"):
    if os.path.isfile(infile):
        with open(infile) as _fp:
            config = json.load(_fp)
            config.update(default_config)
            return config
    return default_config.copy()


def generate_pyright_conf(outfile="./pyrightconfig.json",
                          add_to=("extraPaths", )):
    config = get_config()
    pythonpaths = get_paths()
    localized, ignored = localize_paths(include_dir, pythonpaths)
    for field in add_to:
        config[field].extend(localized)
        config[field].extend(ignored)
    print("writing conf to %s ..." % outfile)
    with open(outfile, "w") as _fp:
        json.dump(config, _fp, indent=2)


def extract_package_name(path):
    pattern = '(%s)' % '|'.join(rez_paths)
    pattern += '/?([^/]+)'
    pattern += '/.*'
    match = re.match(pattern, path)
    if match:
        return match.group(2)
    return os.path.basename(path)


def get_target_name(string):
    name = extract_package_name(string)
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

        if any((fnmatch.fnmatch(path, ign) for ign in ignore_paths)):
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

            print(path, "->", target_path)
            target_paths.append(target_path)
        except:
            pass

    return target_paths, ignored


if __name__ == "__main__":
    generate_pyright_conf()
