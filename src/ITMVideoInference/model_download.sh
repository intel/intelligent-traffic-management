#!/bin/bash -e

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

HOME=$1
MODEL="person-vehicle-bike-detection-2000"
EXTENSIONS=(".bin" ".xml")
PRECISIONS=("FP32" "FP16" "FP16-INT8")
BASE_URL="https://download.01.org/opencv/2021/openvinotoolkit/2021.2/open_model_zoo/models_bin/3"
TARGET_DIR="${HOME}/models/object_detection/${MODEL}"
for precision in ${PRECISIONS[@]}; do
  mkdir -p "${TARGET_DIR}/${precision}"
  for extension in ${EXTENSIONS[@]}; do
    curl "${BASE_URL}/${MODEL}/${precision}/${MODEL}${extension}" -o "${TARGET_DIR}/${precision}/${MODEL}${extension}"
  done
done