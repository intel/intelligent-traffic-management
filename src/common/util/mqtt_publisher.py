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

class MqttPublisher:

    def __init__(self, queue, topic, broker, port, log):
        self.mqtt_c = mqtt.Client()
        self.queue = queue
        self.topic = topic
        self.broker = broker
        self.port = port
        self.log = log

    def connect(self, broker, port):
        self.mqtt_c.connect(broker, int(port), 600)

    def on_log(self, client, userdata, level, buf):
        self.log.debug(f"{self.topic} MQTT on_log: {buf}")

    def get_publisher(self):
        return self.mqtt_c


def start(queue, topic, mqtt_broker, mqtt_port, log, state={"running": True}):
    mqtt_c = None

    try:
        log.info(f"{topic} Initializing publisher")
        mqtt_c = MqttPublisher(queue, topic, mqtt_broker, mqtt_port, log)
        mqtt_c.get_publisher().on_log = mqtt_c.on_log
        mqtt_c.connect(mqtt_broker, int(mqtt_port))
        mqtt_c.get_publisher().socket().setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2048)
        log.info(f"{topic} Running...")
        mqtt_c.get_publisher().loop_start()

        while state['running']:
            if queue:
                mqtt_c.get_publisher().publish(topic, zlib.compress(str(queue.popleft()).encode()), qos=0, retain=False).wait_for_publish()
            else:
                time.sleep(0.005)
    except KeyboardInterrupt:
        log.info(f"{topic} Quitting...")
    finally:
        if mqtt_c:
            mqtt_c.get_publisher().loop_stop()
            mqtt_c.get_publisher().disconnect()
        log.info(f"{topic} Finishing...")
