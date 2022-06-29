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


import filter
import formatter
import threading
import json
import jsonschema
from common.util import publisher_manager, subscriber_manager
from common.util.logger import get_logger
from collections import deque

log = get_logger(__name__)


def main():
    input_queue = deque(maxlen=20)
    filter_queue = deque(maxlen=20)
    formatted_queue = deque(maxlen=20)
    publisher_manager.configure(log, formatted_queue)
    subscriber_manager.configure(log, input_queue)
    with open("/app/config.json") as fd:
        json_config = json.load(fd)
    with open("/app/schema.json") as fd:
        json_schema = json.load(fd)
    jsonschema.validate(instance=json_config, schema=json_schema)
    filter_thread = threading.Thread(
        target=filter.start,
        args=(input_queue, filter_queue, json_config)
    )
    formatter_thread = threading.Thread(
        target=formatter.start,
        args=(filter_queue, formatted_queue)
    )
    filter_thread.start()
    formatter_thread.start()
    subscriber_manager.join()
    publisher_manager.join()
    filter_thread.join()
    formatter_thread.join()

if __name__ == "__main__":
    main()
