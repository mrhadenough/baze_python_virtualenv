from setuptools import setup
setup(
    name='bazel_utils',
    version='0.0.1',
    install_requires=['iterfzf'],
    entry_points={
        'console_scripts': [
            'bazel_python_venv=bazel_python_venv:run',
            'bazel_bump_version=bazel_bump_version:run',
        ],
    }
)
