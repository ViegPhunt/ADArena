class FlagSubmitException(Exception):
    def __str__(self):
        return super().__str__()


class FlagExceptionEnum:
    GAME_NOT_AVAILABLE = FlagSubmitException('Game is not available.')
    GAME_FINISHED = FlagSubmitException('Game has finished. No more flags accepted.')
    FLAG_INVALID = FlagSubmitException('Flag is invalid or too old.')
    FLAG_TOO_OLD = FlagSubmitException('Flag is too old')
    FLAG_YOUR_OWN = FlagSubmitException('Flag is your own')
    FLAG_ALREADY_STOLEN = FlagSubmitException('Flag already stolen')
    SERVICE_IS_DOWN = FlagSubmitException('Cannot submit flags while service is down')