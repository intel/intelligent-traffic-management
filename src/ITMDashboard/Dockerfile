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

LABEL description="ITMDashboard image"


USER root
RUN apt-get update && apt-get install --no-install-recommends -y python3.10 python3-pip && rm -rf /var/lib/apt/lists/*


WORKDIR /app

COPY . .
RUN pip3 install -r requirements.txt
RUN chmod 666 itm*pem

ARG USER
USER ${USER}

CMD python3 server.py

