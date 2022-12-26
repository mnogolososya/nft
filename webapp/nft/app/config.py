from os.path import abspath, dirname

from dynaconf import Dynaconf

cwd: str = abspath(dirname(__file__))

settings = Dynaconf(
    envvar_prefix=False,
    environments=True,
    settings_files=[f'{cwd}/settings.toml', f'{cwd}/.secrets.toml']
)
