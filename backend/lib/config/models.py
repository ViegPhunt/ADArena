from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict



class Arq(BaseModel):
    redis_url: str


class Database(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='postgres_')

    host: str
    port: int = 5432
    user: str
    password: str
    dbname: str = Field(validation_alias='postgres_db')
    
    @property
    def database(self) -> str:
        return self.dbname


class GameService(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='game_')
    
    service_name: str = "ADArena"
    debug: bool = False
    log_level: str = "INFO"


class Redis(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='redis_')

    host: str
    port: int
    password: str
    db: int = 0

    @property
    def url(self) -> str:
        return f'redis://:{self.password}@{self.host}:{self.port}/{self.db}'


class WebCredentials(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='admin_')

    username: str
    password: str