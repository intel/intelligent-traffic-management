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

import common.util.publisher_manager as pub
import cv2
import json
import numpy as np
import os
import queue
import random
import string
import threading
from collections import deque
from common.util.logger import get_logger
from gi.repository import Gst
from gstgva.util import gst_buffer_data
from vaserving.vaserving import VAServing
from vaserving.gstreamer_app_destination import GStreamerAppDestination


def format_frame(input_queue, output_queue, log, cfg):
    while True:
        msg = input_queue.get()
        if not msg:
            continue
        meta_data = {'img_handle': ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))}  #nosec

        if msg.video_frame:
            for message in list(msg.video_frame.messages()):
                meta_data.update(json.loads(message))
            log.debug(meta_data)
            with gst_buffer_data(
                    msg.sample.get_buffer(),
                    Gst.MapFlags.READ) as data:
                meta_data['frame'] = cv2.imencode(".jpg", np.frombuffer(bytes(data), dtype=np.uint8).reshape((meta_data['resolution']['height'],
                                                                                                              meta_data['resolution']['width'],
                                                                                                              3)),
                                                  [cv2.IMWRITE_JPEG_QUALITY, cfg['encoding_level']])[1].tobytes()
                meta_data['encoding_type'] = "jpeg"
                meta_data['encoding_level'] = cfg['encoding_level']

            output_queue.append(meta_data)


class ITM:

    def __init__(self):

        self.log = get_logger(__name__)

        log.info('Getting app config')
        self.src = {"type": os.getenv("SOURCE_TYPE"), "uri": os.getenv("SOURCE_URI")}
        with open("/app/config.json") as fd:
            self.app_cfg = json.load(fd)
        print(f'ITM Serving Config: {self.app_cfg}')

        log.info('Starting Pipeline Server')
        VAServing.start({
            'log_level': os.getenv("PY_LOG_LEVEL", "INFO").upper(),
            'ignore_init_errors': True
        })

        log.info("App_cfg {}".format(self.app_cfg))
        self.output_queue = deque(maxlen=20)
        self.input_queue = queue.Queue(20)
        pub.configure(self.log, self.output_queue)
        threading.Thread(target=format_frame, args=(self.input_queue, self.output_queue, self.log, self.app_cfg)).start()
        self.dest = {
                'type': 'application',
                'class': 'GStreamerAppDestination',
                'output': self.input_queue,
                'mode': 'frames'
            }

        self.model_params = {}
        if 'params' in self.app_cfg:
            self.model_params.update(self.app_cfg['params'])
        self.pipeline_name = self.app_cfg['pipeline']
        self.pipeline_version = self.app_cfg['pipeline_version']
        log.info(f'Creating pipeline {self.pipeline_name}/{self.pipeline_version}')
        self.pipeline = VAServing.pipeline(self.pipeline_name, self.pipeline_version)
        if self.pipeline is None:
            raise RuntimeError('Failed to initialize  pipeline')

        log.info('Starting pipeline {} ---------- {}'.format(self.src, self.dest))
        self.pipeline.start(source=self.src,
                            destination=self.dest,
                            parameters=self.model_params)

    def stop(self):
        VAServing.stop()

    def run_forever(self):
        self.log.info('Running ...')
        while True:
            VAServing.wait()
            pipeline = VAServing.pipeline(self.pipeline_name, self.pipeline_version)
            pipeline.start(source=self.src,
                            destination=self.dest,
                            parameters=self.model_params)

if __name__ == '__main__':

    log = get_logger(__name__)
    itm = ITM()
    try:
        itm.run_forever()
    except Exception as e:
        log.exception('ITM', e)
        itm.stop()
