import subprocess
import os
import threading
from modules.config import setup_global_vars

global_config = setup_global_vars()
logger = global_config["logger"]

def _reader_thread(stream, log_fn):
    """Reads lines from the given stream and logs them using the provided log function."""
    for line in iter(stream.readline, ''):
        log_fn(line.rstrip())
    stream.close()


def _start_subprocess(cmd, env=None):
    """Starts a subprocess with the given command and environment variables."""
    env = env or os.environ.copy()
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env
    )
    return proc


def run_ps_stream_logged(ps_script, env_vars, pwsh="pwsh"):
    """Runs a PowerShell script as a subprocess, streaming stdout/stderr to the logger in real time."""
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)   

    cmd = [
        pwsh,
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", ps_script
    ]

    proc = _start_subprocess(cmd, env)
    t_out = threading.Thread(
        target=_reader_thread,
        args=(proc.stdout, logger.info)
    )
    t_out.daemon = True
    t_out.start()

    rc = proc.wait()
    t_out.join(timeout=1.0)
    logger.debug(f"Return code: {rc}")
    return rc


def run_py_stream_logged(py_script, env_vars=None, python_exe="python"):
    """Runs a Python script as a subprocess, streaming stdout/stderr to the logger in real time."""
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)

    # Force unbuffered output from the child python process
    env["PYTHONUNBUFFERED"] = "1"

    cmd = [
        str(python_exe), "-u",
        str(py_script)
    ]

    proc = _start_subprocess(cmd, env)
    t_out = threading.Thread(
        target=_reader_thread,
        args=(proc.stdout, logger.info)
    )
    t_out.daemon = True
    t_out.start()

    rc = proc.wait()
    t_out.join(timeout=1.0)
    logger.debug(f"Return code: {rc}")
    return rc