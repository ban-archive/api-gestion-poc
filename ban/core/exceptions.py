class ValidationError(ValueError):
    ...


class ResourceLinkedError(ValidationError):
    ...


class IsDeletedError(ValidationError):

    def __init__(self, instance):
        self.instance = instance

    def __str__(self):
        msg = 'Resource `{}` with id `{}` is deleted'
        return msg.format(self.instance.resource, self.instance.id)


class RedirectError(ValueError):

    def __init__(self, identifier, value, redirect):
        self.identifier = identifier
        self.value = value
        self.redirect = redirect

    def __str__(self):
        msg = ('Identifier {identifier} with value {value} is now '
               'pointing on resource with id {redirect}')
        return msg.format(**self.__dict__)


class MultipleRedirectsError(ValueError):

    def __init__(self, identifier, value, redirects):
        self.identifier = identifier
        self.value = value
        self.redirects = redirects

    def __str__(self):
        redirects = ', '.join('{}:{}'.format(k, v) for k, v in self.redirects)
        msg = ('Identifier {identifier} with value {value} is now pointing to '
               'multiple resources: {redirects}')
        return msg.format(identifier=self.identifier, value=self.value,
                          redirects=redirects)
