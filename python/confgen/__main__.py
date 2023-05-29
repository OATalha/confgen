from .confgen import generate_pyright_conf

import logging
import sys


logging.basicConfig(level=logging.INFO)


if __name__ == "__main__":
    generate_pyright_conf()
