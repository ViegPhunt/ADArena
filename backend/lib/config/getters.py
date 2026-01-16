from . import models



def get_arq_config() -> models.Arq:
    redis_config = get_redis_config()
    return models.Arq(
        redis_url=redis_config.url,
    )


def get_db_config() -> models.Database:
    return models.Database()


def get_game_config() -> models.GameService:
    return models.GameService()


def get_redis_config() -> models.Redis:
    return models.Redis()


def get_web_credentials() -> models.WebCredentials:
    return models.WebCredentials()