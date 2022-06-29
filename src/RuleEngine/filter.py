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
import rule_engine
import time
from common.util.logger import get_logger

log = get_logger(__name__)

last_frame = {}


def validate_rule(rule, target):
    if rule.matches(target):
        log.debug(f"rule matches: {target} {rule}")
        return True
    else:
        log.debug(f"rule does not match: {target} {rule}")
        return False


def filter_by_frequency(frame, app_config_dict):
    new_ts = datetime.datetime.strptime(frame['timestamp'], "%Y_%m_%d_%H_%M_%S_%f")
    dict_key = f"{frame['location']}_{frame['event_type']}"
    if dict_key not in last_frame:
        last_frame[dict_key] = new_ts
        return False
    old_ts = last_frame[dict_key]

    if (new_ts - old_ts).seconds > app_config_dict['event_frequency_alert']:
        last_frame[dict_key] = new_ts
        log.debug(f"{frame['location']}_{frame['event_type']} passed the freq filter")
        return False
    log.debug(f"{frame['location']}_{frame['event_type']} did not pass the freq filter")
    return True


def filter_message(frame, rules):
    target = {}
    target['event_type'] = frame['event_type']
    target['num_cars'] = frame['num_cars']
    target['num_pedestrians'] = frame['num_pedestrians']
    target['num_bikes'] = frame['num_bikes']
    for rule in rules:
        if validate_rule(rule, target):
            del target
            return False
    del target
    return True


def start(input_queue, output_queue, json_config):
    log = get_logger(__name__)
    log.info("Starting filter....")

    try:
        cfg_rules = dict(json_config["rules"])
        rules = []
        for cfg_rule in cfg_rules:
            rules.append(rule_engine.Rule(cfg_rules[cfg_rule]))
        while True:
            if input_queue:
                frame = input_queue.popleft()
            else:
                time.sleep(0.005)
                continue
            if filter_message(frame, rules):
                continue
            if filter_by_frequency(frame, json_config):
                continue
            output_queue.append(frame)
            del frame
    except KeyboardInterrupt:
        log.info("Quitting...")
    finally:
        log.info("Finishing...")
