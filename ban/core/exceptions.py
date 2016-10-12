class RedirectError(ValueError):

    def __init__(self, from_identifier, from_value, redirect):
        self.from_identifier = from_identifier
        self.from_value = from_value
        self.redirect = redirect
        self.to_identifier = redirect[0]
        self.to_value = redirect[1]

    def __str__(self):
        msg = ('Identifier {from_identifier} with value {from_value} is now '
               'pointing on {to_identifier} with value {to_value}')
        return msg.format(**self.__dict__)


class MultipleRedirectsError(ValueError):

    def __init__(self, identifier, value, redirects):
        self.from_identifier = identifier
        self.from_value = value
        self.redirects = redirects

    def __str__(self):
        redirects = ', '.join('{}:{}'.format(k, v) for k, v in self.redirects)
        msg = ('Identifier {identifier} with value {value} is now pointing to '
               'multiple resources: {redirects}')
        return msg.format(identifier=self.identifier, value=self.value,
                          redirects=redirects)
