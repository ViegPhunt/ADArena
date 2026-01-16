import os
import shlex
import subprocess
from logging import Logger
from typing import List, Any, AnyStr, Optional, Tuple, Dict

from lib.models import Team, Task
from lib.models.types import TaskStatus, Action, CheckerVerdict


def run_command_gracefully(
        command: List[str],
        input: Optional[AnyStr] = None,
        capture_output: bool = False,
        timeout: float = 0,
        check: bool = False,
        terminate_timeout: float = 3,
        **kwargs: Any,
) -> Tuple[subprocess.CompletedProcess, bool]:
    if input is not None:
        kwargs['stdin'] = subprocess.PIPE

    if capture_output:
        kwargs['stdout'] = subprocess.PIPE
        kwargs['stderr'] = subprocess.PIPE

    killed = False
    with subprocess.Popen(command, **kwargs) as proc:
        try:
            stdout, stderr = proc.communicate(input, timeout=timeout)
        except subprocess.TimeoutExpired as timeout_exc:
            proc.terminate()
            try:
                stdout, stderr = proc.communicate(
                    input,
                    timeout=terminate_timeout,
                )
            except subprocess.TimeoutExpired:
                proc.kill()
                killed = True
                stdout, stderr = proc.communicate()
            except Exception:
                proc.kill()
                raise

            raise subprocess.TimeoutExpired(
                proc.args,
                timeout=timeout,
                output=stdout,
                stderr=stderr,
            ) from timeout_exc
        except Exception:
            proc.kill()
            raise

        retcode = proc.poll()

        if check and retcode:
            raise subprocess.CalledProcessError(
                retcode,
                proc.args,
                output=stdout,
                stderr=stderr,
            )

    res_proc: subprocess.CompletedProcess = subprocess.CompletedProcess(
        args=proc.args,
        returncode=retcode,
        stdout=stdout,
        stderr=stderr,
    )
    return res_proc, killed


def get_patched_environ(env_path: str) -> Dict[str, str]:
    env = os.environ.copy()
    env['PATH'] = f"{env_path}:{env['PATH']}"
    return env


def log_error(
        action: Action,
        team: Team,
        result: subprocess.CompletedProcess,
        logger: Logger):
    logger.warning(
        '%s for team %s failed with code %s.\nstdout: %s\nstderr: %s',
        action,
        team.id,
        result.returncode,
        result.stdout,
        result.stderr,
    )


def run_generic_command(
        command: List,
        action: Action,
        task: Task,
        team: Team,
        logger: Logger,
) -> CheckerVerdict:
    env = get_patched_environ(env_path=task.env_path)

    try:
        result, killed = run_command_gracefully(
            command,
            capture_output=True,
            timeout=task.checker_timeout,
            env=env,
        )

        if killed:
            logger.warning(
                'Process was forcefully killed during %s for team %s task %s',
                action,
                team.id,
                task.id,
            )

        try:
            status = TaskStatus(result.returncode)
            public_message = result.stdout[:1024].decode().strip()
            private_message = result.stderr[:1024].decode().strip()
            if status == TaskStatus.CHECK_FAILED:
                log_error(action, team, result, logger)
        except ValueError as e:
            status = TaskStatus.CHECK_FAILED
            public_message = 'Check failed'
            private_message = (
                f'Check failed with ValueError: {str(e)}\n'
                f'Return code: {result.returncode}\n'
                f'Stdout: {result.stdout}\n'
                f'Stderr: {result.stderr}'
            )
            log_error(action, team, result, logger)

    except subprocess.TimeoutExpired:
        status = TaskStatus.DOWN
        private_message = f'{action} timeout'
        public_message = 'Checker timed out'

    command_str = ' '.join(shlex.quote(x) for x in command)
    verdict = CheckerVerdict(
        public_message=public_message,
        private_message=private_message,
        command=command_str,
        action=action,
        status=status,
    )

    return verdict
