# Copyright 2022 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

ARG PIPELINE_SERVER_IMAGE
FROM ${PIPELINE_SERVER_IMAGE}

WORKDIR /app

USER root

COPY itm.py .
COPY run.sh .
COPY test_videos test_videos
COPY common common
COPY model_download.sh .
RUN chmod +x model_download.sh && ./model_download.sh /home/pipeline-server

RUN chmod +x /app/run.sh

ARG USER
USER $USER

ENTRYPOINT ["/app/run.sh"]
