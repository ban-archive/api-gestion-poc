import argparse
import inspect
import os
import sys
from itertools import zip_longest

from ban.core import config


NO_DEFAULT = object()

parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(title='Available commands', metavar='')


def report(name, item):
    if not Command.current:
        return
    Command.current.report(name, item)


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
        'verbose': False,
        'filter': False,
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
        for name, default in self._globals.items():
            self.add_argument(name, default)

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
        self.parser = subparsers.add_parser(self.name, help=self.short_help)
        self.parser.set_defaults(func=self.invoke)
        for name, default in self.spec:
            self.add_argument(name, default)

    def add_argument(self, name, default, **kwargs):
            kwargs['help'] = self.parse_parameter_help(name)
            if default != NO_DEFAULT:
                kwargs['dest'] = name
                name = '--{}'.format(name.replace('_', '-'))
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
            args = [name]
            self.parser.add_argument(*args, **kwargs)

    def set_defaults(self, **kwargs):
        self.parser.set_defaults(**kwargs)

    def report(self, name, item):
        if name not in self._reports:
            self._reports[name] = []
        self._reports[name].append(item)

    def reporting(self):
        if self._reports:
            sys.stdout.write('\n# Reports:')
            for name, items in self._reports.items():
                sys.stdout.write('\n- {}: {}'.format(name, len(items)))
                if config.get('VERBOSE'):
                    for item in items:
                        sys.stdout.write('\n  . {}'.format(item))
        sys.stdout.write('\n')


def command(func):
    return Command(func)
