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

def start(queue, topic, broker, port, log):
    mqtt_c = None
    def on_log(client, userdata, level, buf):
        log.debug(f"{topic} MQTT on_log: {buf}")

    def on_message(_, __, msg):
        queue.append(ast.literal_eval(zlib.decompress(msg.payload).decode()))

    try:
        log.debug(f"{topic} Initializing subscriber")
        mqtt_c = mqtt.Client()
        mqtt_c.on_message = on_message
        mqtt_c.on_log = on_log
        mqtt_c.connect(broker, int(port), 600)
        mqtt_c.subscribe(topic)
        log.info(f"{topic} Running...")
        mqtt_c.loop_forever()
    except KeyboardInterrupt:
        log.info(f"{topic} Quitting...")
    finally:
        if mqtt_c:
            mqtt_c.loop_stop()
            mqtt_c.unsubscribe(topic)
            mqtt_c.disconnect()
        log.info(f"{topic} Finishing...")
