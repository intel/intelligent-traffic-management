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
import paho.mqtt.client as mqtt
import socket
import zlib
import time

def start(queue, topic, mqtt_broker, mqtt_port, log):
    mqtt_c = None

    def on_log(client, userdata, level, buf):
        log.debug(f"{topic} MQTT on_LOG : {buf}")


    try:
        log.info(f"{topic} Initializing publisher")
        mqtt_c = mqtt.Client()
        mqtt_c.on_log = on_log
        mqtt_c.connect(mqtt_broker, int(mqtt_port), 600)
        mqtt_c.socket().setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2048)
        log.info(f"{topic} Running...")
        mqtt_c.loop_start()

        while True:
            if queue:
                mqtt_c.publish(topic, zlib.compress(str(queue.popleft()).encode()), qos=0, retain=False).wait_for_publish()
            else:
                time.sleep(0.005)
    except KeyboardInterrupt:
        log.info(f"{topic} Quitting...")
    finally:
        if mqtt_c:
            mqtt_c.loop_stop()
            mqtt_c.disconnect()
        log.info(f"{topic} Finishing...")
