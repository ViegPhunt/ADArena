"""Setup ADArena configuration from config.yml."""
import yaml
import click

from scripts import config_constants, config_models, config_utils


@click.command(help='Initialize ADArena configuration')
@click.option(
    '--database',
    metavar='ADDR',
    help='External Postgres address (disables built-in postgres container)',
)
@click.option(
    '--redis',
    metavar='ADDR',
    help='External redis address (disables built-in redis container)',
)
def setup(database, redis):
    """Generate environment files and docker-compose config from config.yml."""
    config_utils.backup_config()

    basic_cfg = config_utils.load_config(basic=True)
    config = config_utils.build_full_config(basic_cfg)
    config_utils.override_config(config, database=database, redis=redis)

    config_utils.dump_config(config)

    setup_db(config.storages.db)
    setup_redis(config.storages.redis)
    setup_admin_api(config.admin)

    prepare_compose(database, redis)


def write_file(name, path, data: dict):
    lines = ["# THIS FILE IS MANAGED BY 'control.py'"]
    lines.extend([f'{k}={v}' for k, v in data.items()])
    
    config_utils.print_status('INFO', f'Writing {name} env to {path}')
    path.write_text('\n'.join(lines))


def setup_db(c: config_models.DatabaseConfig):
    write_file('database', config_constants.POSTGRES_ENV_PATH, {
        'POSTGRES_HOST': c.host,
        'POSTGRES_PORT': c.port,
        'POSTGRES_USER': c.user,
        'POSTGRES_PASSWORD': c.password,
        'POSTGRES_DB': c.dbname,
    })


def setup_redis(c: config_models.RedisConfig):
    write_file('redis', config_constants.REDIS_ENV_PATH, {
        'REDIS_HOST': c.host,
        'REDIS_PORT': c.port,
        'REDIS_PASSWORD': c.password,
    })


def setup_admin_api(c: config_models.AdminConfig):
    write_file('admin', config_constants.ADMIN_ENV_PATH, {
        'ADMIN_USERNAME': c.username,
        'ADMIN_PASSWORD': c.password,
    })


def prepare_compose(database: str, redis: str):
    with config_constants.FULL_COMPOSE_PATH.open(mode='r') as f:
        conf = yaml.safe_load(f)

    removals = [
        (database, 'postgres'),
        (redis, 'redis')
    ]
    for is_external, service_name in removals:
        if is_external:
            conf['services'].pop(service_name, None)

    res_path = config_constants.BASE_DIR / config_constants.EXTERNAL_COMPOSE_FILE
    config_utils.print_status('INFO', f'Writing generated compose base to {res_path}')
    with res_path.open(mode='w') as f:
        yaml.dump(conf, f)