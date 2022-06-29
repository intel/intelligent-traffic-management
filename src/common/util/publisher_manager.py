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
import common.util.mqtt_publisher as mqtt
import threading
import os

pub_threads = []


def get_env_values(logger):
    topic = os.getenv("PUBLISHER_TOPIC", None)
    if not topic:
        logger.error("PUBLISHER_TOPIC undefined")
        return None, None, None
    mqtt_port = os.getenv("MQTT_PORT", None)
    if not mqtt_port:
        logger.error("MQTT_PORT undefined")
        return None, None, None
    mqtt_broker = os.getenv("MQTT_BROKER", None)
    if not mqtt_broker:
        logger.error("MQTT_BROKER undefined")
        return None, None, None
    return topic, mqtt_port, mqtt_broker


def configure(logger, out_queue, queue_module=None, queue_len=0):
    topic, mqtt_port, mqtt_broker = get_env_values(logger)
    if not topic:
        return False
    for topic in topic.split():
        o_queue = out_queue
        if isinstance(out_queue, dict):
            out_queue[topic] = queue_module.deque(maxlen=queue_len)
            o_queue = out_queue[topic]
        t = threading.Thread(
            target=mqtt.start,
            args=(o_queue, topic, mqtt_broker, mqtt_port, logger)
        )
        pub_threads.append(t)
        t.start()
    return True


def join():
    for thread in pub_threads:
        thread.join()