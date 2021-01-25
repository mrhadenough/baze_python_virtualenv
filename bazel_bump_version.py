from subprocess import Popen, PIPE
from iterfzf import iterfzf


def find_versions():
    p = Popen(['bash', '-c', 'find . -name version.bzl'], stdout=PIPE)
    return p.communicate()[0].decode().split('\n')


def run():
    versions = find_versions()
    print(iterfzf(versions))


if __name__ == '__main__':
    run()
