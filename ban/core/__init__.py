import os


class Config:
    """Minimal config helper.
    Fallback on os.environ if no value is set.
    """

    cache = {}
    defaults = {
        'DB_NAME': 'ban'
    }

    def __getattr__(self, name):
        try:
            return self.cache[name]
        except KeyError:
            try:
                fallback = os.environ[name]
            except KeyError:
                try:
                    fallback = self.defaults[name]
                except KeyError:
                    raise AttributeError('{} not set'.format(name))
            # We have a value, set it for next call.
            self.cache[name] = fallback
            return fallback

    def __setattr__(self, name, value):
        self.cache[name] = value

    def get(self, name, default=None):
        return getattr(self, name, default)

    def set(self, name, value):
        name = name.replace('-', '_').upper()
        setattr(self, name, value)


config = Config()
