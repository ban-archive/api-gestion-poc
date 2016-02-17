import csv
import getpass
import os
import pkgutil
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from importlib import import_module
from pathlib import Path

import decorator

from ban.auth.models import Session, User
from ban.core import context, config
from ban.core.versioning import Diff


def load_commands():
    from ban import commands
    prefix = commands.__name__ + "."
    for importer, modname, ispkg in pkgutil.iter_modules(commands.__path__,
                                                         prefix):
        if ispkg or modname == __name__:
            continue
        import_module(modname, package=commands.__name__)


def load_csv(path, encoding='utf-8'):
    path = Path(path)
    if not path.exists():
        abort('Path does not exist: {}'.format(path))
    with path.open(encoding=encoding) as f:
        extract = f.read(4096)
        try:
            dialect = csv.Sniffer().sniff(extract)
        except csv.Error:
            dialect = csv.unix_dialect()
        f.seek(0)
        content = f.read()
        return csv.DictReader(content.splitlines(), dialect=dialect)


def iter_file(path, formatter=lambda x: x):
    path = Path(path)
    if not path.exists():
        abort('Path does not exist: {}'.format(path))
    with path.open() as f:
        for l in f:
            yield formatter(l)


def abort(msg):
    sys.stderr.write("\n" + msg)
    sys.exit(1)


class Bar:
    # TODO: release as light separate module.

    def __init__(self, total=None, prefix='Progress'):
        self.columns = self.compute_columns()
        self.total = total or 1000
        self.template = '\r{prefix}: {progress} {percent}%'
        self.done = 0
        self.prefix = prefix
        self.fill = '█'

    def compute_columns(self):
        return shutil.get_terminal_size((80, 20)).columns

    def __call__(self, step=1, done=None):
        if done is not None:
            self.done = done
        else:
            self.done += step

        percent = self.done / self.total

        if percent > 1.0:
            percent = 1.0

        percent_str = str(int(percent * 1000) / 10)
        length = self.columns - len(self.prefix) - 4 - len(percent_str)
        done_chars = int(percent * length)
        remain_chars = length - done_chars
        progress = self.fill * done_chars + " " * remain_chars

        p = self.template.format(prefix=self.prefix, progress=progress,
                                 percent=percent_str)
        sys.stdout.write(p)

        if percent == 100.0:
            sys.stdout.write('\n')

        sys.stdout.flush()


def batch(func, iterable, chunksize=1000, total=None):
    bar = Bar(total=total)
    workers = int(config.get('WORKERS', os.cpu_count()))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        count = 0
        chunk = []
        for item in iterable:
            if not item:
                continue
            chunk.append(item)
            count += 1
            if count % 10000 == 0:
                for r in executor.map(func, chunk):
                    bar()
                chunk = []
        if chunk:
            for r in executor.map(func, chunk):
                bar()


def prompt(text, default=None, confirmation=False, coerce=None, hidden=False):
    """Prompts a user for input.  This is a convenience function that can
    be used to prompt a user for input later.

    :param text: the text to show for the prompt.
    :param default: the default value to use if no input happens.  If this
                    is not given it will prompt until it's aborted.
    :param confirmation_prompt: asks for confirmation for the value.
    :param type: the type to use to check the value against.
    """
    result = None
    func = getpass.getpass if hidden else input

    while 1:
        while 1:
            try:
                result = func('{}: '.format(text))
            except (KeyboardInterrupt, EOFError):
                abort('Bye.')
            if result:
                break
            elif default is not None:
                return default
        if coerce:
            try:
                result = coerce(result)
            except ValueError:
                sys.stderr.write('Wrong value for type {}'.format(type))
                continue
        if not confirmation:
            return result
        while 1:
            try:
                confirm = func('{} (again): '.format(text))
            except (KeyboardInterrupt, EOFError):
                abort('Bye.')
            if confirm:
                break
        if result == confirm:
            return result
        sys.stderr.write('Error: the two entered values do not match')


def confirm(text, default=None):
    """Ask for confirmation."""
    value = None
    if default:
        default_text = 'Yn'
    elif default is False:
        default_text = 'yN'
    else:
        default_text = 'yn'
    while 1:
        try:
            value = input('{} [{}]: '.format(text, default_text))
        except (KeyboardInterrupt, EOFError):
            abort('Aborted.')
        if value.lower() in ('y', 'yes'):
            return True
        if value.lower() in ('n', 'no'):
            return False
        if value == '' and default is not None:
            return default


@decorator.decorator
def session(func, *args, **kwargs):
    # TODO make configurable from command line
    qs = User.select().select(User.is_staff == True)
    username = config.get('SESSION_USER')
    if username:
        qs = qs.where(User.username == username)
    try:
        user = qs.get()
    except User.DoesNotExist:
        abort('Admin user not found {}'.format(username or ''))
    session = Session.create(user=user)
    context.set('session', session)
    return func(*args, **kwargs)


@decorator.decorator
def nodiff(func, *args, **kwargs):
    Diff.ACTIVE = False
    res = func(*args, **kwargs)
    Diff.ACTIVE = True
    return res


def file_len(f):
    l = sum(1 for line in f)
    f.seek(0)
    return l
