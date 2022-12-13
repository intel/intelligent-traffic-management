#!/bin/bash
set -x

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

cp test_videos/* /home/pipeline-server/resources/
cp -r models/* /home/pipeline-server/models/
cp -pr common /home/pipeline-server/resources/
cp itm.py /home/pipeline-server/resources/
cp itm.sh /home/pipeline-server/resources/
echo "Init complete"