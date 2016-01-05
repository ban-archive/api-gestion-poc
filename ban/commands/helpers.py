import csv
import getpass
import os
import pkgutil
import sys
from concurrent.futures import ThreadPoolExecutor
from importlib import import_module
from pathlib import Path

import decorator
import progressbar

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


class Bar(progressbar.ProgressBar):

    def __init__(self, *args, **kwargs):
        kwargs['redirect_stdout'] = True
        super().__init__(*args, **kwargs)

    def default_widgets(self):
        widgets = super().default_widgets()
        if self.max_value:
            # Simpler option to override the bar fill char…
            widgets[5] = progressbar.widgets.Bar('█')
        return widgets


def bar(iterable, *args, **kwargs):
    return Bar(*args, **kwargs)(iterable)


def batch(func, iterable, chunksize=1000, max_value=None):
    bar = Bar(max_value=max_value).start()
    workers = int(config.get('WORKERS', os.cpu_count()))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for i, res in enumerate(executor.map(func, iterable)):
            bar.update(i)
        bar.finish()


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


def count(iterable):
    return sum(1 for line in iterable)
