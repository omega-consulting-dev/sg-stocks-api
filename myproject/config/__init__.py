import os

env_type = os.getenv("ENV_NAME", "dev")

if env_type == "prod":
    from .prod import *
else:
    from .dev import *
