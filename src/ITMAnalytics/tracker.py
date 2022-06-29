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
import math
import collections
from threading import Thread
import cv2
import yolo_labels
from utils import Point, Rect
import logging
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s :: %(message)s")


class SingleTracker:

    # If detecting to many false collisions, try decreasing ACC_FACTOR
    ACC_FACTOR = 1000

    def __init__(self, id, rect, color, label, influx_client=None):
        self.id = id
        self.rect = rect
        self.color = color
        self.label = label
        self.c_q = collections.deque(maxlen=5)
        self.avg_pos = collections.deque(maxlen=50)
        self.center = self.rect.center()
        self.vel, self.acc = Point(0, 0), Point(0, 0)
        self.vel_x, self.vel_y = 0, 0
        self.acc_x, self.acc_y = 0, 0
        self.mod_vel, self.mod_acc = 0, 0
        self.v_x_q, self.v_y_q, self.v_q = collections.deque(maxlen=50), collections.deque(maxlen=50), collections.deque(maxlen=50)
        self.a_x_q, self.a_y_q, self.a_q = collections.deque(maxlen=50), collections.deque(maxlen=50), collections.deque(maxlen=50)
        self.no_update_counter = 0
        self.update = False
        self.to_delete = False
        self.near_miss = 0
        self.collision = 0
        self.rect_width = 0
        self.influx_client = influx_client

    def _set_vel(self, vel):
        self.vel = vel
        self.vel_x = self.vel.x - self.center.x
        self.vel_y = self.vel.y - self.center.y
        self.mod_vel = math.sqrt(self.vel_x**2 + self.vel_y**2)

    def _save_last_vel(self, vel_x, vel_y, mod_vel):
        self.v_x_q.appendleft(vel_x)
        self.v_y_q.appendleft(vel_y)
        self.v_q.appendleft(mod_vel)

    def _set_acc(self, acc):
        self.acc = acc
        self.acc_x = self.acc.x - self.center.x
        self.acc_y = self.acc.y - self.center.y
        self.mod_acc = math.sqrt(self.acc_x**2 + self.acc_y**2)

    def _save_last_acc(self, acc_x, acc_y, mod_acc):
        self.a_x_q.appendleft(acc_x)
        self.a_y_q.appendleft(acc_y)
        self.a_q.appendleft(mod_acc)

    def cal_avg_pos(self):
        """
        Calculate positions as an average of last n_frames positions.
        This reduces noise from detection stage.
        """
        full = 5
        if len(self.c_q) == full:
            avg = Point(0, 0)
            for i in range(0, full):
                avg += self.c_q[i]
            avg /= full
            self.avg_pos.appendleft(avg)

    def cal_vel(self):
        """
        Calculate velocity as an average of last n_frames frames (dX, dY).
        """
        full = 5
        delta_x, delta_y = 0, 0
        limit = min(full, len(self.avg_pos) -1)
        if limit > 1:
            for i in range(0, limit):
                delta_x += self.avg_pos[i].x - self.avg_pos[i+1].x
                delta_y += self.avg_pos[i].y - self.avg_pos[i+1].y
            delta_x /= limit
            delta_y /= limit
            avg_vel = Point(delta_x, delta_y)
            self._set_vel(self.center + avg_vel)
            self._save_last_vel(self.vel_x, self.vel_y, self.mod_vel)
        else:
            self._set_vel(self.center)

    def cal_acc(self):
        """
        Calculate acceleration as an average of last n_frames frames (dX, dY).
        """
        full = 5
        delta_x, delta_y = 0, 0
        limit = min(full, len(self.v_q) -1)
        if limit > 1:
            for i in range(0, limit):
                delta_x += (self.v_x_q[i]+1)*SingleTracker.ACC_FACTOR/(self.avg_pos[i].y+10) - \
                           (self.v_x_q[i+1]+1)*SingleTracker.ACC_FACTOR/(self.avg_pos[i].y+10)
                delta_y += (self.v_y_q[i]+1)*SingleTracker.ACC_FACTOR/(self.avg_pos[i].y+10) - \
                           (self.v_y_q[i+1]+1)*SingleTracker.ACC_FACTOR/(self.avg_pos[i].y+10)
            delta_x /= limit
            delta_y /= limit
            acc = Point(delta_x, delta_y)
            self._set_acc(self.center + acc)
            self._save_last_acc(self.acc_x, self.acc_y, self.mod_acc)
        else:
            self._set_acc(self.center)

    def is_target_in_frame(self, f_width, f_height):
        """
        Check the target is inside the frame.
        If the target is going out of the frame, need to SingleTracker stop that target.
        """
        curr_x, curr_y = self.center.x, self.center.y
        is_x_inside = (curr_x >= 0) and (curr_x < f_width)
        is_y_inside = (curr_y >= 0) and (curr_y < f_height)
        return (is_x_inside and is_y_inside)

    def mark_for_deletion(self):
        """
        Mark trackers to delete.
        """
        frames = 10
        min_vel = 0.01*self.rect.area()
        if self.no_update_counter >= frames and self.mod_vel < min_vel:
            self.to_delete = True
        return True

    def do_single_tracking(self):
        """
        Track 'one' target specified by SingleTracker.rect in a frame.
        """
        if not self.update:
            self.center = Point(self.vel.x, self.vel.y)
            self.rect.x += self.vel_x
            self.rect.y += self.vel_y
        self.update = False
        self.center = self.rect.center()
        self.c_q.appendleft(self.center)
        self.cal_avg_pos()
        self.cal_vel()
        self.cal_acc()
        self.no_update_counter += 1
        self.mark_for_deletion()
        return True


class TrackingManager:

    total_vehicle_count = 0
    total_bicycle_count = 0
    total_people_count = 0

    def __init__(self, channel_id=None, influx_client=None):
        self.channel_id = channel_id
        self.tracker_vec = []
        self.id_list = 0
        self.people_count = 0
        self.vehicle_count = 0
        self.bicycle_count = 0
        self.influx_client = influx_client

    def insert_tracker_by_id(self, _init_rect, _color, _target_id, _label, update):
        """
        Create new SingleTracker object and insert it to the tracker_vec.
        If you are about to track new object, need to use this function.
        """
        if _init_rect.area() == 0:
            return False
        result_idx = self.find_tracker_by_id(_target_id)
        if result_idx is not False:
            if update is False:
                return False
            else:
                self.tracker_vec[result_idx].center = _init_rect.center()
                self.tracker_vec[result_idx].rect = _init_rect
                self.tracker_vec[result_idx].update = update
                self.tracker_vec[result_idx].no_update_counter = 0
                if self.tracker_vec[result_idx].label is None:
                    self.tracker_vec[result_idx].label = _label
                    self.tracker_vec[result_idx].color = _color
        else:
            new_tracker = SingleTracker(_target_id, _init_rect, _color, _label, self.influx_client)
            self.tracker_vec.append(new_tracker)
            self.id_list = _target_id + 1
            if _label == 1:
                self.people_count += 1
                TrackingManager.total_people_count += 1
            elif _label == 0:
                self.vehicle_count += 1
                TrackingManager.total_vehicle_count += 1
            elif _label == 2:
                self.bicycle_count += 1
                TrackingManager.total_bicycle_count += 1
            return [self.people_count, self.vehicle_count, self.bicycle_count]
        return []

    def find_tracker_by_id(self, _target_id):
        """
        Find SingleTracker object which has ID : _target_id in the TrackerManager.tracker_vec
        If success to find return that iterator, else return False
        """
        for i, tracker in enumerate(self.tracker_vec):
            if tracker.id == _target_id:
                return i
        return False

    def find_tracker(self, rect, label):
        """
        Find SingleTracker object in the TrackerManager.tracker_vec
        If success to find return that index, or return new index if no coincidence
        """
        dist_thresh = (rect.height * rect.width)/2
        selection = []
        best = None
        min_distance = (rect.height * rect.width) + 10
        index = -1
        new_object = True
        for tracker in self.tracker_vec:
            in_area = tracker.rect.intersect(rect).area()
            max_per_area = max(in_area/tracker.rect.area(), in_area/rect.area())
            if max_per_area > 0.2:
                new_object = False
            if tracker.label == label or tracker.label == None:
                selection.append(tracker)
                diff = tracker.center - rect.center()
                distance = diff.x**2 + diff.y**2
                if (best is None and distance < dist_thresh) or (best is not None and distance < min_distance):
                    min_distance = distance
                    best = tracker
        if best is None and new_object:
            index = self.id_list
        elif best is not None:
            index = best.id
        return index

    def delete_tracker(self, _target_id):
        """
        Delete SingleTracker object which has ID : _target_id in the TrackerManager.tracker_vec
        """
        result_idx = self.find_tracker_by_id(_target_id)
        if result_idx is False:
            return False
        else:
            tr = self.tracker_vec.pop(result_idx)
        return True

    def get_total_counts(self):
        """
        Return total counts
        """
        return [TrackingManager.total_people_count,
                TrackingManager.total_vehicle_count,
                TrackingManager.total_bicycle_count]


class InfluxDB:
    """
    Class to push data to InfluxDB periodically
    """
    def __init__(self, influxdb, num_ch, config_data):
        self.influxdb = influxdb
        self.data = [0]*num_ch
        self.total_counts = []
        self.total_collision_count = 0
        self.near_miss_count = [0]*num_ch
        self.collision_count = [0]*num_ch
        self.collision_events = []
        self.num_ch = num_ch
        self.config_data = config_data
        self.running = False

    def start(self):
        """
        Start Thread
        """
        self.th = Thread(target=self.update_db, args=())
        self.running = True
        self.th.daemon = True
        self.th.start()

    def stop(self):
        """
        Stop Thread
        """
        self.running = False
        self.th.join()

    def update_db(self):
        """
        Push data InfluxDB in every 1 second
        """
        while self.running:
            time.sleep(1)
            json_body = []
            for ch_id, ch_data in enumerate(self.data):
                # log.info(self.config_data)
                if ch_data != 0:
                    json_body.append({'measurement': f'channel{ch_id}',
                                      'fields': {'people_count': ch_data[0],
                                                 'car_count': ch_data[1],
                                                 'bicycle_count': ch_data[2]}
                                     })
                if self.near_miss_count[ch_id] != 0 or self.collision_count[ch_id] != 0:
                    json_body.append({'measurement': "collisions_data",
                                      'fields': {f'channel{ch_id}near miss': self.near_miss_count[ch_id],
                                                 f'channel{ch_id}collision': self.collision_count[ch_id]}
                                    })


            if self.total_counts:
                json_body.append({'measurement': 'total_count',
                                  'fields': {'total_people_count': self.total_counts[0],
                                             'total_car_count': self.total_counts[1],
                                             'total_bicycle_count': self.total_counts[2]}
                                })

            self.total_collision_count = sum(self.collision_count)
            if self.total_collision_count:
                json_body.append({'measurement': 'total_count',
                                  'fields': {'total_collision_count': self.total_collision_count}
                                })

            while self.collision_events:
                event = self.collision_events.pop(0)
                json_body.append({'measurement': "collisions_event",
                                  'fields': {f'details': event}
                                })
            #print(repr(json_body))
            if json_body:
               self.influxdb.write_points(json_body)


class TrackingSystem:

    total_collision_count = 0

    def __init__(self, channel_id=None, influx_client=None, cam_config=[]):
        self.channel_id = channel_id
        self.frame_width = None
        self.frame_height = None
        self.current_frame = None
        self.init_target = {Rect(0, 0, 0, 0), 0}
        self.updated_target = {Rect(0, 0, 0, 0), 0}
        self.cam_config = cam_config
        self.manager = TrackingManager(channel_id, influx_client)
        self.is_initialized = False
        self.total_frames = 0
        self.influx_client = influx_client
        self.near_miss = 0
        self.collision_count = 0
        self.buffer_events = []
        self.buffer_collisions = []
        self.buffer_tracker = []
        self.n_obj1 = 0
        self.n_obj2 = 0
        self.collision_couples = []


    def init_tracker_system(self, frame_width, frame_height, init_target, num_channels):
        """
        Insert multiple SingleTracker objects to the manager.tracker_vec in once.
        If you want multi-object tracking, call this function just for once like.
        """
        if self.is_initialized:
            return True
        self.is_initialized = True
        self.frame_width, self.frame_height = frame_width, frame_height
        self.init_target = init_target
        index, label, color = 0, None, None
        for target in self.init_target:
            label = target[1]
            color = yolo_labels.get_label_color(label)
            if target[0].area()/(self.frame_width*self.frame_height) < 0.009 and label == yolo_labels.LABEL_CAR:
                continue
            counts = self.manager.insert_tracker_by_id(target[0], color, index, label, False)
            if counts and self.influx_client:
                self.influx_client.data[self.channel_id] = counts
                self.influx_client.total_counts = self.manager.get_total_counts()
            elif counts is False:
                return False
            index += 1
        return True

    def update_tracking_system(self, updated_results):
        """
        Insert new multiple SingleTracker objects to the manager.tracker_vec.
        If you want multi-object tracking, call this function just for once like.
        """
        label, color = None, None
        for target in updated_results:
            label = target[1]
            color = yolo_labels.get_label_color(label)
            if target[0].area()/(self.frame_width*self.frame_height) < 0.009 and label == yolo_labels.LABEL_CAR:
                continue
            index = self.manager.find_tracker(target[0], label)
            if index != -1:
                counts = self.manager.insert_tracker_by_id(target[0], color, index, label, True)
                if counts and self.influx_client:
                    self.influx_client.data[self.channel_id] = counts
                    self.influx_client.total_counts = self.manager.get_total_counts()
                elif counts is False:
                    return False
        return True

    def start_tracking(self):
        """
        Track all targets.
        You don't need to give target id for tracking.
        This function will track all targets.
        """
        thread_pool = []
        for ptr in self.manager.tracker_vec:
            thread = Thread(target=ptr.do_single_tracking,
                            args=())
            thread_pool.append(thread)
            thread.start()
        for thread in thread_pool:
            thread.join()
        tracker_erase = []
        for tracker in self.manager.tracker_vec:
            if not tracker.is_target_in_frame(self.frame_width, self.frame_height) or tracker.to_delete:
                tracker_erase.append(tracker.id)
        for tr in tracker_erase:
            self.manager.delete_tracker(tr)
        return True

    def draw_tracking_results(self, mat):
        """
        Draw tracking results on frame and put target id on rectangle.
        :param mat: frame
        """
        event = None
        if not self.manager.tracker_vec:
            return False, None
        for tracker in self.manager.tracker_vec:
            st = (int(tracker.rect.x), int(tracker.rect.y))
            end = (int(tracker.rect.width + tracker.rect.x), int(tracker.rect.height + tracker.rect.y))
            cv2.rectangle(mat, st, end, tracker.color, 2)
            if len(tracker.c_q) == 5:
                vel_draw = (tracker.vel - tracker.center) * 20
                st = (int(tracker.center.x), int(tracker.center.y))
                end = (int((tracker.center + vel_draw).x), int((tracker.center + vel_draw).y))
                cv2.arrowedLine(mat, st, end, (0, 0, 255), 1)
                if len(tracker.a_q) > 1:
                    acc_draw = (tracker.acc - tracker.center) * 20
                    end = (int((tracker.center + acc_draw).x), int((tracker.center + acc_draw).y))
                    cv2.arrowedLine(mat, st, end, (255, 0, 0), 1)
                for i in range(0, len(tracker.avg_pos)):
                    st = (int(tracker.avg_pos[i].x), int(tracker.avg_pos[i].y))
                    end = (int(tracker.avg_pos[i-1].x), int(tracker.avg_pos[i-1].y))
                    cv2.line(mat, st, end, tracker.color, 1)
            text = str(tracker.id) + " " + yolo_labels.get_label_str(tracker.label)
            pos = (int(tracker.rect.x + 2), int(tracker.rect.y - 5))
            (text_width, text_height), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(mat, (int(pos[0]), int(pos[1])),
                          (int(pos[0] + text_width), int(pos[1] - text_height)),
                          tracker.color, cv2.FILLED)
            cv2.putText(mat, text, pos, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
            if tracker.collision or tracker.near_miss:
                pos = (int(tracker.rect.x + 2), int(tracker.rect.y + tracker.rect.height + 12))
                if tracker.collision:
                    text = "Collision"
                    event = "collision"
                else:
                    text = "Near Miss"
                    event = "near_miss"
                (text_width, text_height), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.rectangle(mat, (pos[0], pos[1]),
                              (int(pos[0] + text_width), int(pos[1] - text_height)),
                              tracker.color, cv2.FILLED)
                cv2.putText(mat, text, pos, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
        return True, event

    def detect_collision(self):
        """
        Detect collision and near miss between all trackers
        """
        if not self.manager.tracker_vec:
            return False
        to_del = []
        for couple in self.collision_couples:
            to_find = int(couple.split(":")[0])
            found = False
            for tracker in self.manager.tracker_vec:
                if to_find == tracker.id:
                    found = True
            if not found:
                to_del.append(couple)
        for del_couple in to_del:
            self.collision_couples.remove(del_couple)

        for tracker in self.manager.tracker_vec:
            if tracker.label == yolo_labels.LABEL_PERSON:
                continue
            v_x_q = tracker.v_x_q.copy()
            v_y_q = tracker.v_y_q.copy()
            a_x_q = tracker.a_x_q.copy()
            a_y_q = tracker.a_y_q.copy()
            avg_acc_x = 0
            avg_acc_y = 0
            try:
                same_sign_x = ((a_x_q[0] > 0) - (a_x_q[0] < 0)) == ((v_x_q[0] > 0) - (v_x_q[0] < 0))
                same_sign_y = ((a_y_q[0] > 0) - (a_y_q[0] < 0)) == ((v_y_q[0] > 0) - (v_y_q[0] < 0))
            except IndexError:
                same_sign_x, same_sign_y = True, True
            sign_x = 1 if same_sign_x else -1
            sign_y = 1 if same_sign_y else -1

            if len(a_x_q) > 1:
                lim = min(len(a_x_q), 3)
                for i in range(1, lim):
                    try:
                        same_sign_x_i = ((a_x_q[i] > 0) - (a_x_q[i] < 0)) == ((v_x_q[i] > 0) - (v_x_q[i] < 0))
                        same_sign_y_i = ((a_y_q[i] > 0) - (a_y_q[i] < 0)) == ((v_y_q[i] > 0) - (v_y_q[i] < 0))
                    except IndexError:
                        same_sign_x_i, same_sign_y_i = True, True
                    sign_x_i = 1 if same_sign_x_i else -1
                    sign_y_i = 1 if same_sign_y_i else -1
                    avg_acc_x += sign_x_i*abs(a_x_q[i])
                    avg_acc_y += sign_y_i*abs(a_y_q[i])
                avg_acc_x = avg_acc_x / lim
                avg_acc_y = avg_acc_y / lim
            threshold_x = abs(sign_x*abs(tracker.acc_x) - (avg_acc_x))
            threshold_y = abs(sign_y*abs(tracker.acc_y) - (avg_acc_y))

            if threshold_x > 4 or threshold_y >= 3:
                if self.influx_client is not None and not tracker.near_miss:
                    pass
                tracker.near_miss =  True
                for other_tracker in self.manager.tracker_vec:
                    if tracker.id == other_tracker.id:
                        continue
                    if tracker.rect.intersect(other_tracker.rect).area() > 0:
                        tracker.rect_width = 2
                        other_tracker.rect_width = 2
                        if tracker.id < other_tracker.id:
                            obj1, obj2 = tracker.id, other_tracker.id
                        else:
                            obj2, obj1 = tracker.id, other_tracker.id
                        couple = str(obj1) + ":" + str(obj2)
                        if other_tracker.near_miss and not couple in self.collision_couples:
                            self.collision_count += 1
                            TrackingSystem.total_collision_count += 1
                            if self.influx_client:
                                self.influx_client.collision_count[self.channel_id] = self.collision_count
                                self.influx_client.total_collision_count = TrackingSystem.total_collision_count
                                self.influx_client.collision_events.append(f'Collision detected at - {self.cam_config["address"]}')
                            self.collision_couples.append(couple)
                        if (not other_tracker.near_miss) and (self.n_obj1 != obj1 or self.n_obj2 != obj2):
                            self.near_miss += 1
                            if self.influx_client:
                                self.influx_client.near_miss_count[self.channel_id] = self.near_miss
                            self.n_obj1, self.n_obj2 = obj1, obj2
                        if other_tracker.near_miss:
                            other_tracker.collision, other_tracker.color = True, (0, 0, 225)
                            tracker.collision, tracker.color = True, (0, 0, 225)
                        else:
                            other_tracker.color = (0, 165, 255)
                            tracker.color = (0, 165, 255)
        self.total_frames += 1
        return True

    def terminate_system(self):
        """
        Deallocate all memory and close the program.
        """
        self.manager.tracker_vec = []
        return True

