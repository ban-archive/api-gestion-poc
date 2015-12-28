import argparse
import inspect
import os
import sys
from itertools import zip_longest

from ban.core import config


NO_DEFAULT = object()

parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(title='Available commands', metavar='')


def report(name, item, level=1):
    if not Command.current:
        return
    Command.current.report(name, item, level=level)
report.ERROR = 1  # Shown when using --verbose or -v.
report.WARNING = 2  # Only shown when using -vv.
report.NOTICE = 3  # Only shown when using -vvv.


class Command:

    current = None
    _globals = {
        'db_port': None,
        'db_host': None,
        'db_user': None,
        'db_password': None,
        'db_name': None,
        'session_user': None,
        'workers': os.cpu_count(),
        'verbose': {'action': 'count', 'default': None},
    }

    def __init__(self, command):
        self.command = command
        self.inspect()
        self.init_parser()
        self.set_globals()
        self._reports = {}
        self._on_parse_args = []
        self._on_before_call = []
        self._on_after_call = []

    def __call__(self, *args, **kwargs):
        Command.current = self
        for func in self._on_before_call:
            func(self, args, kwargs)
        try:
            self.command(*args, **kwargs)
        except KeyboardInterrupt:
            pass
        else:
            for func in self._on_after_call:
                func(self, args, kwargs)
        finally:
            self.reporting()
            Command.current = None

    def invoke(self, parsed):
        kwargs = {'cmd': self}
        for name, _ in self.spec:
            kwargs[name] = getattr(parsed, name)
        for func in self._on_parse_args:
            func(self, parsed, kwargs)
        self.parse_globals(parsed, **kwargs)
        self(**kwargs)

    def on_parse_args(self, func):
        self._on_parse_args.append(func)

    def on_before_call(self, func):
        self._on_before_call.append(func)

    def on_after_call(self, func):
        self._on_after_call.append(func)

    def set_globals(self):
        for name, kwargs in self._globals.items():
            if not isinstance(kwargs, dict):
                kwargs = {'default': kwargs}
            self.add_argument(name, **kwargs)

    def parse_globals(self, parsed, **kwargs):
        for name in self._globals.keys():
            value = getattr(parsed, name, None)
            if value:
                config.set(name, value)

    @property
    def namespace(self):
        module = inspect.getmodule(self.command)
        return getattr(module, '__namespace__',
                       inspect.getmodulename(module.__file__))

    @property
    def name(self):
        return self.namespace + ':' + self.command.__name__

    @property
    def help(self):
        return self.command.__doc__ or ''

    @property
    def short_help(self):
        return self.help.split('\n\n')[0]

    def inspect(self):
        self.__doc__ = inspect.getdoc(self.command)
        spec = inspect.getargspec(self.command)
        arg_names = spec.args[:]
        matched_args = [reversed(x) for x in [spec.args, spec.defaults or []]]
        spec_dict = dict(zip_longest(*matched_args, fillvalue=NO_DEFAULT))
        self.spec = [(x, spec_dict[x]) for x in arg_names]

    def parse_parameter_help(self, name):
        try:
            return self.help.split(name, 1)[1].split('\n')[0].strip()
        except IndexError:
            return ''

    def init_parser(self):
        self.parser = subparsers.add_parser(self.name, help=self.short_help,
                                            conflict_handler='resolve')
        self.parser.set_defaults(func=self.invoke)
        for name, default in self.spec:
            self.add_argument(name, default)

    def add_argument(self, name, default=NO_DEFAULT, **kwargs):
            kwargs['help'] = self.parse_parameter_help(name)
            args = [name]
            if default != NO_DEFAULT:
                kwargs['dest'] = name
                if '_' not in name:
                    args.append('-{}'.format(name[0]))
                args[0] = '--{}'.format(name.replace('_', '-'))
                kwargs['default'] = default
                type_ = type(default)
                if type_ == bool:
                    action = 'store_false' if default else 'store_true'
                    kwargs['action'] = action
                elif type_ in (int, str):
                    kwargs['type'] = type_
                elif type_ in (list, tuple):
                    kwargs['nargs'] = '*'
                elif callable(default):
                    kwargs['type'] = type_
                    kwargs['default'] = ''
            self.parser.add_argument(*args, **kwargs)

    def set_defaults(self, **kwargs):
        self.parser.set_defaults(**kwargs)

    def report(self, name, item, level):
        if name not in self._reports:
            self._reports[name] = []
        self._reports[name].append((item, level))

    def reporting(self):
        if self._reports:
            sys.stdout.write('\n# Reports:')
            for name, items in self._reports.items():
                sys.stdout.write('\n- {}: {}'.format(name, len(items)))
                verbosity = config.get('VERBOSE')
                if verbosity:
                    for item, level in items:
                        if verbosity >= level:
                            sys.stdout.write('\n  . {}'.format(item))
        sys.stdout.write('\n')


def command(func):
    return Command(func)
