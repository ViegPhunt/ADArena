from logging import Logger
from typing import Optional

from lib.models import Team, Task, Flag
from lib.utils.commands import run_generic_command
from lib.models.types import Action, CheckerVerdict


class CheckerRunner:
    team: Team
    task: Task
    flag: Optional[Flag]

    def __init__(
            self,
            team: Team,
            task: Task,
            logger: Logger,
            flag: Optional[Flag] = None,
    ):
        self.team = team
        self.task = task
        self.logger = logger
        self.flag = flag

    def check(self) -> CheckerVerdict:
        return self._check_as_process()

    def put(self) -> CheckerVerdict:
        return self._put_as_process()

    def get(self) -> CheckerVerdict:
        return self._get_as_process()

    def _check_as_process(self) -> CheckerVerdict:
        check_command = [
            self.task.checker,
            'check',
            self.team.ip,
        ]

        return run_generic_command(
            command=check_command,
            action=Action.CHECK,
            task=self.task,
            team=self.team,
            logger=self.logger,
        )

    def _put_as_process(self) -> CheckerVerdict:
        assert self.flag is not None, 'Can only be called when flag is passed'

        put_command = [
            self.task.checker,
            'put',
            self.team.ip,
            self.flag.private_flag_data,
            self.flag.flag,
            str(self.flag.vuln_number),
        ]

        return run_generic_command(
            command=put_command,
            action=Action.PUT,
            task=self.task,
            team=self.team,
            logger=self.logger,
        )

    def _get_as_process(self) -> CheckerVerdict:
        assert self.flag is not None, 'Can only be called when flag is passed'

        get_command = [
            self.task.checker,
            'get',
            self.team.ip,
            self.flag.private_flag_data,
            self.flag.flag,
            str(self.flag.vuln_number),
        ]

        return run_generic_command(
            command=get_command,
            action=Action.GET,
            task=self.task,
            team=self.team,
            logger=self.logger,
        )