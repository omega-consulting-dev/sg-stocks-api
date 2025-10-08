import environ
import os

env = environ.Env()
environ.Env.read_env(os.path.join(os.path.dirname(__file__), '../.env'))

def get_env(key, default=None):
    return env(key, default=default)