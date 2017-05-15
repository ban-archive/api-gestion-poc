import os


class Config(dict):
    """Minimal config helper.
    Fallback on os.environ if no value is set.
    """

    defaults = {
        'DB_NAME': 'ban'
    }

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            try:
                fallback = os.environ[name]
            except KeyError:
                try:
                    fallback = self.defaults[name]
                except KeyError:
                    raise AttributeError('{} not set'.format(name))
            # We have a value, set it for next call.
            self[name] = fallback
            return fallback

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        del self[name]

    def get(self, name, default=None):
        return getattr(self, name, default)

    def set(self, name, value):
        name = name.replace('-', '_').upper()
        setattr(self, name, value)


config = Config()
