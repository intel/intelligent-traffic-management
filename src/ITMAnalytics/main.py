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
import influxdb
import json
import jsonschema
import math
import multiprocessing as mp
import numpy as np
import os
import psycopg2
import smartcity
import sys
import threading
import time
from common.util import subscriber_manager, publisher_manager
from common.util.logger import get_logger
from common.util.shared_deque import SharedDequeManager
from flask import Flask, Response

mp.set_start_method("spawn", force=True)

INFLUXDB_HOST = "influxdb.{}.svc.cluster.local".format(os.getenv("NAMESPACE", "default"))
INFLUXDB_PORT = "8086"
DASHBOARD_NAME = "ITM_" + os.getenv('DASHBOARD_NAME', '_')
HOST_IP = os.getenv("HOST_IP")
LOCAL_HOST = os.getenv("LOCAL_HOST")
SERVER_PORT = os.getenv("SERVER_PORT")
LOCAL_PORT = os.getenv("LOCAL_PORT")
PSQL_USER = os.getenv("PSQL_USER")
PSQL_PASS = os.getenv("PSQL_PASS")
INFLUX_USER = os.getenv("INFLUX_USER")
INFLUX_PASS = os.getenv("INFLUX_PASS")

app = Flask(__name__)

log = get_logger(__name__)

stream_list = []
queue_dict = {}
thread_list = []
queue_cons_list = []

class GlobalData:
    def __init__(self):
        self.num_channels = 0
        self.conf_data = None
        self.mutex = None
        self.q_data = None
        self.current_frames = None
        self.camera_active = None

_GData = GlobalData()


class PsqlConn:
    def __init__(self, username_, password_, host_="localhost", port_=32432, database_="itm_metadata"):
        retries = 5
        i = 0
        while i <= retries:
            time.sleep(2)
            try:
                self.conn = psycopg2.connect(user=username_,
                                             password=password_,
                                             host=host_,
                                             port=port_,
                                             database=database_,
                                             connect_timeout=3)
                command = """CREATE TABLE IF NOT EXISTS itm_camera(id SERIAL PRIMARY KEY, node_name TEXT, address TEXT, latitude TEXT, longitude TEXT, analytics TEXT, server_ip TEXT, cam_index TEXT);"""
                cursor = self.conn.cursor()
                cursor.execute(command)
                cursor.close()
                self.conn.commit()
                break
            except (Exception, psycopg2.Error) as error:
                log.error(error)
            i += 1
            if i == retries:
                sys.exit(-1)

    def insert_record(self, nname_, address_, latitude_, longitude_, analytics_, server_ip_, cam_index_):
        try:
            sql = """INSERT INTO itm_camera(node_name, address, latitude, longitude, analytics, server_ip, cam_index) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id;"""

            cursor = self.conn.cursor()
            cursor.execute(sql, (nname_, address_, latitude_, longitude_, analytics_, server_ip_, cam_index_,))
            iid = cursor.fetchone()[0]
            self.conn.commit()
            cursor.close()
            return iid
        except (Exception, psycopg2.Error) as error:
            log.error(error)
            return -1

    def drop_entries(self, nname_):
        try:
            sql = """DELETE FROM itm_camera WHERE node_name=%s"""

            cursor = self.conn.cursor()
            cursor.execute(sql, (nname_,))
            self.conn.commit()
            cursor.close()
        except (Exception, psycopg2.Error) as error:
            log.error(error)
            return -1

    def close_conn(self):
        self.conn.close()


def _get_all_streams(num_ch):
    """
    Generator.
    Combine and yield frames from all running video streams.
    """
    height, width = 320, 640
    num_rows = math.floor(math.sqrt(num_ch))
    num_cols = math.ceil(num_ch/num_rows)
    _GData.mutex.acquire()
    for i in range(num_ch):
        _GData.camera_active[i] = True
    _GData.mutex.release()
    empty_frame = np.zeros((height,width,3), np.uint8)
    try:
        while True:
            rows = []
            for r in range(0, num_rows):
                cols = []
                for c in range(0, num_cols):
                    if not _GData.q_data[r+c]:
                        if _GData.current_frames[r+c] is None:
                            cols.append(empty_frame.copy())
                        else:
                            cols.append(_GData.current_frames[r+c].copy())
                    else:
                        frame = _GData.q_data[r+c].popleft()
                        _GData.current_frames[r+c] = frame
                        cols.append(frame)
                rows.append(cols)
            base = cv2.vconcat([cv2.hconcat(h_list) for h_list in rows])
            ret, base_en = cv2.imencode('.jpg', base.copy())
            if not ret:
                continue
            yield (b' --frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' +
                   base_en.copy().tobytes() + b'\r\n\r\n')
    except Exception as err:
        log.error(f'Error: {err}')
    finally:
        for idx in range(num_ch):
            if _GData.current_frames[idx] is None:
                _GData.mutex.acquire()
                _GData.camera_active[idx] = False
                _GData.mutex.release()


@app.route('/get_all_streams')
def get_all_streams():
    """
    Route to show all running video streams
    """
    return Response(_get_all_streams(_GData.num_channels),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


def _stream_channel(cam_id):
    """
    Generator.
    Yield frames that belongs to <cam_id>.
    """
    log.info("==============")
    log.info(cam_id)
    log.info("==============")
    _GData.mutex.acquire()
    _GData.camera_active[cam_id] = True
    _GData.mutex.release()
    queue = _GData.q_data[cam_id]
    max_try = 40000
    try:
        while True:
            if not queue and max_try > 0:
                max_try -= 1
                time.sleep(0.001)
                continue
            elif not queue and max_try <= 0:
                log.error('Unable to receive frames from pipeline, Unknown error.')
                break
            max_try = 40000
            if queue:
                try:
                    frame = queue.popleft()
                except Exception:  #nosec
                    continue
            else:
                continue
            _GData.current_frames[cam_id] = frame
            ret, frame = cv2.imencode('.jpg', frame)
            if not ret:
                continue
            yield (b' --frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' +
                   frame.tobytes() + b'\r\n\r\n')
    except Exception as err:
        log.error(f'Error: {err}')
    finally:
        _GData.mutex.acquire()
        _GData.camera_active[cam_id] = False
        _GData.mutex.release()
        _GData.current_frames[cam_id] = None

@app.route('/camera/<cam_id>')
def open_stream(cam_id):
    """
    Route to individual video stream identified by <cam_id>.
    If <cam_id> is 'all' render HTML that shows all video streams.
    Calls _stream_channel(cam_id) function.
    """
    try:
        if not cam_id.isnumeric():
            return Response("The URL does not exist", 401)
        cam_id = int(cam_id)
        if cam_id >= _GData.num_channels:
            return Response("The URL does not exist", 401)
        return Response(_stream_channel(cam_id),
                        mimetype='multipart/x-mixed-replace; boundary=frame')
    except Exception as err:
        log.error(f'Error: {err}')


@app.after_request
def add_headers(response):
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy']  =  "frame-ancestors 'none' https://*:32000 https://*:30300;" \
                                                "media-src 'none' ; " \
                                                "object-src 'none' ; " \
                                                "connect-src 'none' ; " \
                                                "plugin-src 'none' ; " \
                                                "frame-src 'none' ; " \
                                                "img-src 'self' https://openlayers.org http://a.tile.openstreetmap.org http://b.tile.openstreetmap.org http://c.tile.openstreetmap.org https://*:30303  ; "
    return response


def start_flask():
    app.run(host=LOCAL_HOST, port=LOCAL_PORT,
        threaded=True, ssl_context=('/app/itm.pem', '/app/itm-key.pem'))

def insert_entries():
    server_ip = f'{HOST_IP}:{SERVER_PORT}'
    psqlDB = PsqlConn(PSQL_USER, PSQL_PASS, HOST_IP)
    psqlDB.drop_entries(DASHBOARD_NAME)

    for i in range(0, _GData.num_channels):
        camera_info = _GData.conf_data[i]
        psqlDB.insert_record(DASHBOARD_NAME, camera_info['address'], camera_info['latitude'],
                             camera_info['longitude'], camera_info['analytics'], server_ip, i)

    psqlDB.close_conn()

def main():
    with open("/app/config.json") as fd:
        json_config = json.load(fd)
    with open("/app/schema.json") as fd:
        json_schema = json.load(fd)
    jsonschema.validate(instance=json_config, schema=json_schema)
    frames_queue_size = json_config["frames_queue_size"]
    _GData.num_channels = len(os.getenv("SUBSCRIBER_TOPIC").split())
    _GData.conf_data = list(json_config['cameras'])

    collision = json_config['detect_collision']
    tracking = json_config['tracking'] or collision

    _GData.mutex = mp.Lock()
    manager = mp.Manager()
    mgr = SharedDequeManager()
    mgr.start()
    publish_queue = mgr.deque(maxlen=frames_queue_size)
    _GData.camera_active = manager.list([False] * _GData.num_channels)
    _GData.q_data = {key:mgr.deque(maxlen=frames_queue_size) for key in range(0, _GData.num_channels)}
    _GData.current_frames = [None] * _GData.num_channels
    try:
        client = influxdb.InfluxDBClient(host=INFLUXDB_HOST, port=INFLUXDB_PORT,
                                         username=INFLUX_USER,
                                         password=INFLUX_PASS,
                                         database="itm_metadata")
        # test and retry connecting influxdb
        i = -1
        while i<=20:
            i += 1
            try:
                client.drop_database("itm_metadata")
                break
            except:
                log.info('Retrying...')
                time.sleep(1)
        client.drop_database("itm_metadata")
        client.create_database("itm_metadata")
        log.info("INFLUXDB CONNECTED")
    except influxdb.exceptions.InfluxDBClientError as err:
        log.error(f'Can\'t connect to InluxDB. \n{err}')
        sys.exit(-1)
    except influxdb.exceptions.InfluxDBServerError as err:
        log.error(f'InfluxDB Server Error.\n{err}')
        sys.exit(-1)
    except Exception as err:
        log.error(f'Error: Failed to connect to Influxdb container.\nDebug Info: {err}')
        sys.exit(-1)
    insert_entries()

    try:
       threading.Thread(target=start_flask).start()
       subscriber_manager.configure(log, queue_dict, mgr, frames_queue_size)
       publisher_manager.configure(log, publish_queue, mgr, frames_queue_size)
       process = mp.Process(target=smartcity.start_app, args=(_GData.conf_data, tracking, collision,
                                                              client, _GData.q_data, _GData.camera_active, queue_dict,
                                                              publish_queue))
       process.start()
       while mp.active_children():
           time.sleep(1)
       process.join()

    except KeyboardInterrupt:
       process.join()
       process.terminate()

if __name__ == "__main__":
    main()
