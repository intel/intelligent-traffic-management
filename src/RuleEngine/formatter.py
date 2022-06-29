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
import time
from common.util.logger import get_logger


def start(input_queue, output_queue):
    log = get_logger(__name__)

    try:
        log.info("Formatter thread started")
        while True:
            if input_queue:
                frame = input_queue.popleft()
            else:
                time.sleep(0.005)
                continue
            new_frame = {}
            title = 'cap_'
            if frame['event_type'] != 'none':
                title = title + frame['event_type'] + "_" + frame['location']
            else:
                title = title + "overcrowd_" + frame['location']
            title = title + "_" + frame['img_handle'] + "_" + frame['timestamp']
            new_frame['title'] = title
            log.debug(new_frame)
            new_frame['img'] = frame['img']
            output_queue.append(new_frame)
            del new_frame
            del frame
    except Exception as e:
        log.info(f"Exception: {e} Quitting...")
        log.error(e)
    finally:
        log.info("Finishing...")
