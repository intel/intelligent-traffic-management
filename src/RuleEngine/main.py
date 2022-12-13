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


import collections
import json
import signal
import threading
from collections import deque
import jsonschema

import formatter
import filter
from common.util import publisher_manager, subscriber_manager
from common.util.logger import get_logger

log = get_logger(__name__)
queue_dict = {}
input_queue = {}
state = {"running": True}


def sig_handler(_signal, _frame):
    global state
    state["running"] = False


def main():
    filter_queue = deque(maxlen=20)
    formatted_queue = deque(maxlen=20)
    publisher_manager.configure(log, formatted_queue)
    subscriber_manager.configure(log, input_queue, collections, 20)
    with open("/app/config.json") as fd:
        json_config = json.load(fd)
    with open("/app/schema.json") as fd:
        json_schema = json.load(fd)
    jsonschema.validate(instance=json_config, schema=json_schema)
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)
    f_threads = []
    for in_key in input_queue:
        filter_thread = threading.Thread(
            target=filter.start,
            args=(input_queue[in_key], filter_queue, json_config, state)
        )
        filter_thread.start()
        f_threads.append(filter_thread)
    formatter_thread = threading.Thread(
        target=formatter.start,
        args=(filter_queue, formatted_queue, state)
    )
    formatter_thread.start()
    subscriber_manager.join()
    publisher_manager.join()
    for th in f_threads:
        th.join()
    formatter_thread.join()


if __name__ == "__main__":
    main()
