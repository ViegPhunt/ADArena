from typing import Union


class CacheKeys:
    """
    Centralized Redis key naming conventions.
    
    All Redis keys are namespaced to avoid collisions.
    Key patterns:
    - Simple values: 'real_round', 'game_state'
    - Namespaced: 'team:token:{token}', 'flag:str:{flag}'
    - Round-specific: 'round:{N}:start_time', 'teams:round:{N}'
    
    Using this class ensures consistent naming across the codebase.
    """
    @staticmethod
    def round_start(r: int) -> str:
        return f'round:{r}:start_time'

    @staticmethod
    def current_round() -> str:
        return 'real_round'

    @staticmethod
    def game_config() -> str:
        return 'game_config'

    @staticmethod
    def game_state() -> str:
        return 'game_state'

    @staticmethod
    def teams(round_num: int = None) -> str:
        if round_num is not None:
            return f'teams:round:{round_num}'
        return 'teams'

    @staticmethod
    def team_by_token(token: str) -> str:
        return f'team:token:{token}'

    @staticmethod
    def tasks(round_num: int = None) -> str:
        if round_num is not None:
            return f'tasks:round:{round_num}'
        return 'tasks'

    @classmethod
    def flag_by_str(cls, flag_str: str) -> str:
        """Key for flag lookup by string.
        
        Critical for flag submission performance - O(1) lookup.
        Each flag string is unique, so no collisions possible.
        """
        return f'flag:str:{flag_str}'

    @staticmethod
    def attack_data() -> str:
        return 'attack_data'

    @staticmethod
    def session(session_key: str) -> str:
        return f'session:{session_key}'