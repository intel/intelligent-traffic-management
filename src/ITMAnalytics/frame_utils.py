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
import datetime
import numpy as np
import cv2

class Frame:
    def __init__(self, frame):
        self.in_frame = frame

    @property
    def width(self):
        return int(self.in_frame['resolution']['width'])

    @property
    def height(self):
        return int(self.in_frame['resolution']['height'])

    @property
    def channels(self):
        try:
            return int(self.in_frame['resolution']['channels'])
        except KeyError:
            return 3

    @property
    def blob(self):
        return self.in_frame['frame']

    @property
    def encoding_type(self):
        try:
            return self.in_frame['encoding_type']
        except KeyError:
            return None

    @property
    def encoding_level(self):
        try:
            return self.in_frame['encoding_level']
        except KeyError:
            return None

    @property
    def roi(self):
        try:
            return self.in_frame['objects']
        except KeyError:
            return []

    @staticmethod
    def confidence_level(roi):
        return roi['detection']['confidence']

    @staticmethod
    def label_id(roi):
        return roi['detection']['label_id']

    def __delete_raw_blob(self):
        self.in_frame.pop('frame', None)

    def decode_frame(self, log):
        encoding = None
        if self.encoding_type and self.encoding_level:
            encoding = {"type": self.encoding_type,
                        "level": self.encoding_level}
        blob = self.blob
        self.__delete_raw_blob()
        if isinstance(blob, list):
            blob = blob[0]
        frame = np.frombuffer(blob, dtype=np.uint8)
        del blob
        if encoding is not None:
            frame = np.reshape(frame, (frame.shape))
            try:
                frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)
            except cv2.error as ex:
                log.error("frame: {}, exception: {}".format(frame, ex))
        else:
            log.debug("Encoding not enabled...")
            frame = np.reshape(frame, (self.height, self.width, self.channels))

        return frame

    def format_pub_frame(self, event, ch_id, address, objects):
        self.in_frame['event_type'] = event
        self.in_frame['camera_id'] = ch_id + 1
        self.in_frame['location'] = address.replace(" ", "-")
        self.in_frame['num_cars'] = objects['car']
        self.in_frame['num_pedestrians'] = objects['ped']
        self.in_frame['num_bikes'] = objects['bike']
        self.in_frame['timestamp'] = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S_%f")
        return self.in_frame
