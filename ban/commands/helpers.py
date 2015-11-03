import csv
import pkgutil
import sys
from importlib import import_module
from multiprocessing import Pool
from pathlib import Path

from progressbar import ProgressBar


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


def bar(iterable, *args, **kwargs):
    return ProgressBar(*args, **kwargs)(iterable)


def batch(func, iterable, chunksize=1000):
    pool = Pool()
    count = 0
    chunk = []
    for item in bar(iterable):
        if not item:
            continue
        chunk.append(item)
        count += 1
        if count % chunksize == 0:
            pool.map(func, chunk)
            chunk = []
    if chunk:
        pool.map(func, chunk)
    pool.close()
    pool.join()
