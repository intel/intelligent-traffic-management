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
import ast
import zlib


class MqttSubscriber:

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

    def on_message(self, client, userdata, msg):
        self.queue.append(ast.literal_eval(zlib.decompress(msg.payload).decode()))

    def get_subscriber(self):
        return self.mqtt_c

def start(queue, topic, broker, port, log):
    mqtt_c = None

    try:
        log.debug(f"{topic} Initializing subscriber")
        mqtt_c = MqttSubscriber(queue, topic, broker, port, log)
        mqtt_c.get_subscriber().on_message = mqtt_c.on_message
        mqtt_c.get_subscriber().on_log = mqtt_c.on_log
        mqtt_c.connect(broker, int(port))
        mqtt_c.get_subscriber().subscribe(topic)
        log.info(f"{topic} Running...")
        mqtt_c.get_subscriber().loop_forever()
    except KeyboardInterrupt:
        log.info(f"{topic} Quitting...")
    finally:
        if mqtt_c:
            mqtt_c.get_subscriber().loop_stop()
            mqtt_c.get_subscriber().unsubscribe(topic)
            mqtt_c.get_subscriber().disconnect()
        log.info(f"{topic} Finishing...")
