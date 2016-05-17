import string
import random


def generate_secret(size=55, chars=string.ascii_letters + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))
