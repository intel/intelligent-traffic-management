"""
Copyright 2022 Intel Corporation
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
    http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import os
import logging
import logging.handlers
import sys


LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'ERROR': logging.ERROR,
    'WARN': logging.WARN
}


def configure_logging(log_level, module_name, ):
    if log_level not in LOG_LEVELS:
        raise Exception('Unknown log level: {}'.format(log_level))

    fmt_str = ('%(asctime)s : %(levelname)s : %(name)s : ' +
               '[%(filename)s] :' +
               '%(funcName)s : in line : [%(lineno)d] : %(message)s')

    log_lvl = LOG_LEVELS[log_level]
    logging.basicConfig(format=fmt_str, level=log_lvl)
    logger = logging.getLogger(module_name)
    logger.setLevel(log_lvl)

    # Do basic configuration of logging (just for stdout config)
    logging.basicConfig(format=fmt_str, level=log_lvl)

    logger = logging.getLogger()
    logger.setLevel(log_lvl)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(fmt_str)
    handler.setFormatter(formatter)

    # Removing the default handler added by getLogger to avoid duplicate logs
    if logger.hasHandlers():
        logger.handlers.clear()
    logger.addHandler(handler)

    return logger

def get_logger(module_name):
    log_level = os.getenv("PY_LOG_LEVEL", "INFO").upper()

    logger = configure_logging(log_level, module_name)
    return logger
