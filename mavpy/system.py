import os
import platform
from contextlib import contextmanager
from subprocess import Popen, PIPE, STDOUT


PLATFORM_NAME = platform.system()


def get_maven_name():
    return 'mvn.cmd' if PLATFORM_NAME == 'Windows' else 'mvn'


def which(file_name):
    if PLATFORM_NAME == 'Linux':
        exit_code, file_path = run(['which', file_name])
        if exit_code != 0:
            raise FileNotFoundError()
        file_path = file_path.strip()
    elif PLATFORM_NAME == 'Windows':
        _, file_path = run(['where.exe', file_name])
        file_path = file_path.strip()
        if len(file_path) == 0:
            raise FileNotFoundError
    else:
        raise NotImplementedError
    return file_path


def run(cmd_parts, **popen_kwargs):
    process = Popen(cmd_parts, stdout=PIPE, stderr=STDOUT, env=os.environ.copy(), **popen_kwargs)
    output, _ = process.communicate()
    exit_code = process.wait()
    return exit_code, output.decode("utf-8")


@contextmanager
def env_var(name, value):
    previous_env_state = os.environ.copy()
    os.environ[name] = value
    yield
    os.environ.clear()
    os.environ.update(previous_env_state)