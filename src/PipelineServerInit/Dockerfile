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

ARG UBUNTU_IMAGE
FROM ${UBUNTU_IMAGE}
LABEL description="DLStreamer Initialization Image"

USER root
RUN apt-get update && apt-get install --no-install-recommends -y \
                              curl \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /res

RUN mkdir models
COPY test_videos test_videos
COPY model_download.sh .
COPY run.sh .
COPY common common
COPY itm.py .
COPY itm.sh .
RUN chmod 755 model_download.sh && ./model_download.sh /res/models/
RUN chmod 755 run.sh itm.sh

RUN apt-get autoremove -y curl

ARG USER
USER ${USER}

ENTRYPOINT ["./run.sh"]