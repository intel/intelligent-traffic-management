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

import threading
import uploader
import signal
from collections import deque
from common.util import subscriber_manager
from common.util.logger import get_logger

state = {"running": True}


def sig_handler(_signal, _frame):
    global state
    state["running"] = False


def main():
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    input_queue = deque(maxlen=20)
    subscriber_manager.configure(get_logger(__name__), input_queue)
    uploader_thread = threading.Thread(
        target=uploader.start, args=(input_queue, state,)
    )

    uploader_thread.start()
    uploader_thread.join()
    subscriber_manager.join()

if __name__ == "__main__":
    main()

