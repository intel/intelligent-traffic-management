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

import cv2
import sys
import threading
import time
import yolo_labels
from common.util.logger import get_logger
from frame_utils import Frame
from tracker import TrackingSystem, InfluxDB
from utils import Rect

log = get_logger(__name__)

tracking_system = []
TRACKING = True
COLLISION = True


class FpsManager:
    """
    Class to calculate FPS for each stream
    """
    def __init__(self, num_ch):
        self.num_ch = num_ch
        self.st_time = [0]*num_ch
        self.frame_counts = [0]*num_ch

    def update_ch(self, ch_id):
        """
        Update and return average FPS for channel <ch_id>
        Average FPS is used because it is stable and don't fluctuate.
        """
        if self.st_time[ch_id] == 0:
            self.st_time[ch_id] = time.monotonic()

        self.frame_counts[ch_id] += 1
        t = time.monotonic()
        fps = round(self.frame_counts[ch_id]/(t - self.st_time[ch_id]), 2)
        return fps

import timeit

def frame_callback(frame, conf_data, fps_manager, ch_id, q_data, running, cam_config, publish_queue):
    #log.info(repr(frame['metadata']))
    #log.info(ch_id)
    t0 = timeit.default_timer()
    fps = fps_manager.update_ch(ch_id)
    scale, thickness, font = 0.6, 2, cv2.FONT_HERSHEY_SIMPLEX
    first_results = []
    frame_obj = Frame(frame)
    width = frame_obj.width
    height = frame_obj.height
    mat = frame_obj.decode_frame(log)
    # TODO: add CPU/GPU to text ?
    text = "E2E FPS: {0}".format(fps)
    (text_width, text_height) = cv2.getTextSize(text, font, scale, thickness)[0]
    offset_x, offset_y = 10, 20
    box_coords = ((offset_x, offset_y), (offset_x + text_width + 2, offset_y - text_height - 2))
    cv2.rectangle(mat, box_coords[0], box_coords[1], (255, 255, 255), cv2.FILLED)
    cv2.putText(mat, text, (offset_x, offset_y), font, scale, (0, 0, 0), 1)
    objects = {'ped': 0, 'bike': 0, 'car': 0}
    t1 = timeit.default_timer()
    for roi in frame_obj.roi:
        if frame_obj.confidence_level(roi) < 0.5:
            continue
        rect = Rect(roi['x'], roi['y'], roi['w'], roi['h'])
        label = frame_obj.label_id(roi)
        if label == 1 and 'pedestrian' in conf_data[ch_id]['analytics']:
            label = yolo_labels.LABEL_PERSON
            objects['ped'] += 1
        elif label == 0 and 'vehicle' in conf_data[ch_id]['analytics']:
            label = yolo_labels.LABEL_CAR
            objects['car'] += 1
        elif label == 2 and 'bike' in conf_data[ch_id]['analytics']:
            label = yolo_labels.LABEL_BICYCLE
            objects['bike'] += 1
        else:
            continue

        if TRACKING:
            first_results.append((rect, label))
        else:
            cv2.rectangle(mat, (int(rect.x), int(rect.y)),
                          (int(rect.x + rect.width), int(rect.y + rect.height)),
                          (0, 255, 255), 2)
            text = yolo_labels.get_label_str(label)
            (text_width, text_height) = cv2.getTextSize(text, font, scale, thickness)[0]
            box_coords = ((rect.x, rect.y), (rect.x + text_width + 2, rect.y - text_height - 2))
            cv2.rectangle(mat, box_coords[0], box_coords[1], (0, 255, 255), cv2.FILLED)
            cv2.putText(mat, text, (rect.x, rect.y), font, scale, (0, 0, 0), 1)
    t3 = timeit.default_timer()
    event = None
    if TRACKING:
        if not tracking_system[ch_id].is_initialized:
            tracking_system[ch_id].init_tracker_system(width, height, first_results, len(conf_data))
        tracking_system[ch_id].update_tracking_system(first_results)
        tracking_success = tracking_system[ch_id].start_tracking()
        if not tracking_success:
            log.error('Tracking failed')
            sys.exit(-1)
        if tracking_system[ch_id].manager.tracker_vec != 0:
            if COLLISION and ('vehicle' in conf_data[ch_id]['analytics'] or 'bike' in conf_data[ch_id]['analytics']):
                tracking_system[ch_id].detect_collision()
            _, event = tracking_system[ch_id].draw_tracking_results(mat)
    t4 = timeit.default_timer()
    if not event:
        event = "none"
    frame = frame_obj.format_pub_frame(event, ch_id, cam_config[ch_id]['address'], objects)
    t41 = timeit.default_timer()

    log.debug(f"publish frame {frame}")
    frame['img'] = cv2.imencode('.jpg', mat)[1].tobytes()
    t42 = timeit.default_timer()

    #publish_queue.put(frame)
    publish_queue.append(frame)
    t43 = timeit.default_timer()

    try:
        if running[ch_id]:
            # if not q_data[ch_id].full():
            #     q_data[ch_id].put(mat, False)
            # else:
            #     _ = q_data[ch_id].get(False)
            #     q_data[ch_id].put(mat, False)
            q_data[ch_id].append(mat)
    except Exception:
        sys.exit()
    # t44 = timeit.default_timer()
    # log.info(f"camera{ch_id} ... {t41 - t4} format frame")
    # log.info(f"camera{ch_id} ... {t42 - t41} encode frame")
    # log.info(f"camera{ch_id} ... {t43 - t42} publish 1")
    # log.info(f"camera{ch_id} ... {t44 - t43} publish2")
    #
    #
    #
    # t5 = timeit.default_timer()
    # log.info(f"camera{ch_id} ... {t1 - t0} for frame init + text")
    # log.info(f"camera{ch_id} ... {t3 - t1} for roi parse")
    # log.info(f"camera{ch_id} ... {t4 - t3} for obj draw")
    # log.info(f"camera{ch_id} ... {t5 - t4} for frame publish")


def start_app(config_data, tracking, collision,
              client, q_data, running, queue_dict, publish_queue):
    """
    Main function to start smart city.
    """
    global TRACKING, COLLISION
    log.info("Starting SmartCity")
    TRACKING, COLLISION = tracking, collision
    num_ch = len(queue_dict.keys())
    log.info(f"{num_ch} channels")
    log.info(f" tracking: {tracking}, collision: {collision}")
    client = InfluxDB(client, num_ch, config_data)
    client.start()
    for i in range(num_ch):
        tracking_system.append(TrackingSystem(i, client, config_data[i]))
    log.info("Tracking system initialized")
    fps_manager = FpsManager(num_ch)
    def get_frame(queue, fps_manager, ch_id, q_data, running, config_data, publish_queue):
        try:
            while True:
                if queue:
                    #log.info(f"frame.....camera{ch_id} ..." + str(queue.qsize()))
                    frame_callback(queue.popleft(), config_data, fps_manager, ch_id, q_data, running,  config_data, publish_queue)
                else:
                    time.sleep(0.005)
        except KeyboardInterrupt:
            log.info('Quitting...')
            client.stop()
        except Exception:
            log.exception('Error during execution:')
            client.stop()

    analytics_threads = []
    for i in range(0, num_ch):
        log.info("Preparing analytics thread for topic: " + list(queue_dict.keys())[i])
        analytics_threads.append(threading.Thread(target=get_frame,
                                                  args=(queue_dict[list(queue_dict.keys())[i]], fps_manager, i, q_data, running, config_data, publish_queue)))
        log.info("Starting thread")
        analytics_threads[i].start()

    for i in range(0, num_ch):
        analytics_threads[i].join()
    client.stop()
