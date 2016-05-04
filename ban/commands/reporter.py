"""
Reporter module.
Reporter must be:
- thread safe (we need it to output command reporting from API calls)
- reference chain free (no need to pass "reported" from command to helpers)
- batch compliant: we use concurrences.future helpers, and we want the
  reporting to be centralized all for one batch.
- able to output in various format (string for stdout, json for API)
- able to output only on demand (when command is finished, not on the fly)
- able to group reports by level and message
"""
from ban.core import context


ERROR = 1
WARNING = 2
NOTICE = 3


class Reporter:
    """Store reports and render them on demand."""

    LEVEL_LABEL = {
        ERROR: 'error',
        WARNING: 'warning',
        NOTICE: 'notice',
    }

    def __init__(self, verbosity):
        self.verbosity = verbosity
        self.clear()

    def __str__(self):
        lines = []

        if self._reports:
            lines.append('# Reports')
            for level, reports in self._reports.items():
                if reports:
                    lines.append(self.LEVEL_LABEL[level].title())
                for msg, data in reports.items():
                    total = len(data) if self.verbosity else data
                    lines.append('\t- {} ({})'.format(msg, total))
                    if self.verbosity:
                        for item in data:
                            if self.verbosity >= level:
                                lines.append('\t\t. {}'.format(item))
        return '\n'.join(lines)

    def __json__(self):
        out = {}

        for level, reports in self._reports.items():
            if reports:
                out[self.LEVEL_LABEL[level]] = []
                for msg, data in reports.items():
                    total = len(data) if self.verbosity else data
                    current = {
                        'total': total,
                        'msg': msg
                    }
                    if self.verbosity and self.verbosity >= level:
                        current['data'] = data
                    out[self.LEVEL_LABEL[level]].append(current)
        return out

    def __call__(self, msg, data, level):
        if self.verbosity:
            self._reports[level].setdefault(msg, [])
            self._reports[level][msg].append(data)
        else:
            # Do not consume memory and only track counts.
            self._reports[level].setdefault(msg, 0)
            self._reports[level][msg] += 1

    def merge(self, reports):
        for level, msgs in reports.items():
            for msg, data in msgs.items():
                if self.verbosity:
                    self._reports[level].setdefault(msg, [])
                    self._reports[level][msg].extend(data)
                else:
                    self._reports[level].setdefault(msg, 0)
                    self._reports[level][msg] += data

    def clear(self):
        self._reports = {
            ERROR: {},
            WARNING: {},
            NOTICE: {}
        }


def report(name, item, level=1):
    reporter = context.get('reporter')
    if not reporter:
        print("Reporter not set!")
        return
    reporter(name, item, level=level)


def error(name, item):
    report(name, item, level=ERROR)


def warning(msg, data):
    report(msg, data, level=WARNING)


def notice(msg, data):
    report(msg, data, level=NOTICE)
