"""Shared subprocess helper for all backend controllers."""

from __future__ import annotations

import subprocess
import logging
import os
import signal

logger = logging.getLogger(__name__)


def run_command(
    cmd: list[str],
    timeout: int = 10,
    input_data: str | None = None,
    env: dict[str, str] | None = None,
    start_new_session: bool = True,
) -> tuple[bool, str]:
    """Run a subprocess command safely.

    Returns (success, output_or_error). The child process is killed on timeout
    by subprocess.run.
    """
    process: subprocess.Popen[str] | None = None
    try:
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE if input_data is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            start_new_session=start_new_session,
        )
        stdout, stderr = process.communicate(input=input_data, timeout=timeout)
    except FileNotFoundError:
        return False, f"command not found: {cmd[0]}"
    except PermissionError as exc:
        return False, str(exc)
    except subprocess.TimeoutExpired:
        if process is not None:
            _terminate_process(process, start_new_session)
            try:
                process.communicate(timeout=1)
            except subprocess.TimeoutExpired:
                _kill_process(process, start_new_session)
                process.communicate()
        return False, f"command timed out after {timeout}s"
    except OSError as exc:
        return False, str(exc)

    output = (stdout or "") + (stderr or "")
    if process.returncode != 0:
        cleaned = output.strip() or f"exit code {process.returncode}"
        logger.debug("Command failed: %s -> %s", cmd, cleaned)
        return False, cleaned

    return True, output


def _terminate_process(process: subprocess.Popen[str], started_new_session: bool) -> None:
    try:
        if started_new_session:
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
    except ProcessLookupError:
        return


def _kill_process(process: subprocess.Popen[str], started_new_session: bool) -> None:
    try:
        if started_new_session:
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
    except ProcessLookupError:
        return
