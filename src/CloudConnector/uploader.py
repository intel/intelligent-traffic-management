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

import boto3
import botocore
import os
import re
import time
from common.util.logger import get_logger

log = get_logger(__name__)
s3_client_created = False

def get_session():
    regex = re.compile('[a-zA-Z0-9]+')
    access_key = f"{os.getenv('AWS_KEY')}"
    secret_key = f"{os.getenv('AWS_SECRET')}"
    if not regex.match(access_key) or not regex.match(secret_key):
        raise ValueError("Empty/wrong format id or key")
    return boto3.Session(
        aws_access_key_id=regex.match(access_key).group(0),
        aws_secret_access_key=regex.match(secret_key).group(0),
    )


def get_bucket():
    regex = re.compile('[a-zA-Z0-9_-]+')
    bucket = f"{os.getenv('AWS_BUCKET')}"
    if not regex.match(bucket):
        raise ValueError("Empty/wrong format bucket")
    return regex.match(bucket).group(0)


def get_region():
    regex = re.compile('[a-zA-Z0-9_-]+')
    bucket_region = f"{os.getenv('AWS_BUCKET_REGION')}"
    if not regex.match(bucket_region):
        raise ValueError("Empty/wrong format bucket")
    return regex.match(bucket_region).group(0)


def start(input_queue, state):

    try:

        s3 = None
        global s3_client_created
        while (not s3_client_created and state['running']):
            try:
                log.info("Creating boto3 session")
                session = get_session()
                log.info("Getting s3 resource")
                s3 = session.resource("s3")
                bucket = get_bucket()
                log.info("Creating Bucket " + str(bucket))
                bucket_region = get_region()
                if (bucket_region == "us-east-1"):
                    s3.create_bucket(Bucket=bucket)
                else:
                    s3.meta.client.head_bucket(Bucket=bucket)
                log.info("S3 client created")
                s3_client_created = True
            except (Exception, botocore.exceptions.ClientError, botocore.exceptions.NoCredentialsError, botocore.exceptions.HTTPClientError) as error:
                log.info("Wrong credentials: waiting for AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_BUCKET_REGION and ACCESS_TOKEN configuration.")
                log.error(error)
                time.sleep(5)

        while state['running']:
            if input_queue:
                message = input_queue.popleft()
                log.debug(f"message = {message}")

                try:
                    log.info(f'uploaded {message["title"]}')
                    s3.Bucket(bucket).put_object(Key=message['title'] + ".jpeg", Body=message['img'])
                except Exception as e:
                    log.error(str(e))
            else:
                time.sleep(0.005)
                continue
    except KeyboardInterrupt:
        log.info("Quitting...")
    finally:
        log.info("Finishing...")

