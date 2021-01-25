#!/usr/bin/env python

import argparse
import json
import logging
import os
from hashlib import sha256
from os.path import expanduser
from pathlib import Path
from subprocess import PIPE, Popen

log = logging.getLogger('bazel_python_venv')

# python virtual enviroment would be created in:
# and symlinked into ~/.virtualenvs (this needed for VSCode, it searches in this path)

LOCAL_PATH = Path(os.getcwd()) / '.local'
PYTHON_VENV_PATH = Path(LOCAL_PATH / 'python_venv')
SITE_PACKAGES_PATH = Path(PYTHON_VENV_PATH / 'lib/python3.7/site-packages/')


def get_conf():
    parser = argparse.ArgumentParser(description='Verbose')
    parser.add_argument(
        '-v', dest='verbose', action='store_true', help='verbose mode'
    )
    parser.add_argument(
        '--lib',
        dest='include_libraries',
        action='store_true',
        help='include libraries',
    )
    parser.add_argument(
        '--vscode-workspace',
        nargs=1,
        help='vscode workspace',
    )
    return parser.parse_args()


def create_path(path):
    if not os.path.isdir(path):
        os.mkdir(path)


def get_bazel_conf():
    create_path(LOCAL_PATH)
    p = Popen(['bash', '-c', 'bazel info'], stdout=PIPE)
    text = p.communicate()[0]
    return dict([i.split(': ') for i in text.decode().split('\n') if i])


bazel_conf = get_bazel_conf()
bazel_lib_path = Path(bazel_conf['output_base']) / 'external'
execution_root = bazel_conf['execution_root']
bazel_workspace = bazel_conf['workspace']
project_name = Path(execution_root).name
app_config = get_conf()


LOG_LEVEL = logging.DEBUG if app_config.verbose else logging.INFO
log.setLevel(LOG_LEVEL)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
ch = logging.StreamHandler()
ch.setLevel(LOG_LEVEL)
ch.setFormatter(formatter)
log.addHandler(ch)


def create_python_venv():
    if not os.path.isdir(PYTHON_VENV_PATH):
        p = Popen(
            ['python', '-m', 'venv', str(PYTHON_VENV_PATH)],
            stdout=PIPE,
        )
        _, stderr = p.communicate()
        if stderr:
            log.error(stderr)
            exit()
    virtualenvs_path = Path(expanduser('~')) / '.virtualenvs'
    if not os.path.isdir(virtualenvs_path):
        create_path(virtualenvs_path)
    venv_path = virtualenvs_path / '{}-{}'.format(
        Path(execution_root).name,
        sha256(os.getcwd().encode()).hexdigest()[-6:],
    )
    print('venv path', venv_path)
    if not os.path.isdir(venv_path):
        os.symlink(
            src=PYTHON_VENV_PATH, dst=venv_path, target_is_directory=True
        )


# copy folder to virtualenv
def copy_to_pip(directory, copy_from_src=False):
    if directory.name in {'__pycache__', 'setuptools', 'pkg_resources'}:
        return
    if os.path.exists(directory / 'BUILD') and not copy_from_src:
        return

    dst = Path(SITE_PACKAGES_PATH) / directory.name
    log.debug('%s %s %s', directory, '--->', dst)

    if os.path.lexists(dst):
        os.remove(dst)
    try:
        os.symlink(src=directory, dst=dst, target_is_directory=True)
    except Exception as e:
        log.warning(e)


def link_packages_into_python_venv():
    # search for python libraries and copy them to virtualenv
    for directory1 in (
        bazel_lib_path / i
        for i in os.listdir(bazel_lib_path)
        if os.path.isdir(bazel_lib_path / i)
    ):
        if '_pip_' not in str(directory1):
            continue
        for directory2 in (
            directory1 / i
            for i in os.listdir(directory1)
            if os.path.isdir(directory1 / i)
        ):
            for directory3 in (
                directory2 / i
                for i in os.listdir(directory2)
                if os.path.isdir(directory2 / i)
            ):
                copy_to_pip(directory3)


def link_libs():
    # add libraries folder to python virtualenv
    libraries_path = Path(execution_root) / 'python/libraries'
    for directory1 in os.listdir(libraries_path):
        directory2 = libraries_path / directory1 / 'src'
        if not os.path.isdir(directory2):
            continue
        for directory3 in (
            directory2 / i
            for i in os.listdir(directory2)
            if os.path.isdir(directory2 / i)
        ):
            copy_to_pip(directory3, copy_from_src=True)


def vscode_analysis_extra_path():
    current_dir = Path(bazel_workspace)
    p = Popen(
        ['bash', '-c', f'find "{bazel_workspace}/python" -type d -name "src"'],
        stdout=PIPE,
    )
    text = p.communicate()[0]
    paths = [
        str(Path(current_dir) / i) for i in text.decode().split('\n') if i
    ]

    if app_config.vscode_workspace:
        vscode_settings_path = Path(app_config.vscode_workspace[0])
    else:
        vscode_settings_path = os.getcwd() / '.vscode/settings.json'

    if not os.path.exists(vscode_settings_path):
        return
    with open(vscode_settings_path, 'r') as f:
        data = json.load(f)
        if app_config.vscode_workspace:
            data['settings']['python.analysis.extraPaths'] = paths
        else:
            data['python.analysis.extraPaths'] = paths
    with open(vscode_settings_path, 'w') as f:
        json.dump(data, f, indent=4)


def run():
    create_python_venv()
    vscode_analysis_extra_path()
    link_packages_into_python_venv()

    if app_config.include_libraries:
        link_libs()


if __name__ == '__main__':
    run()
