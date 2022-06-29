#!/bin/bash

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

source /opt/intel/openvino/bin/setupvars.sh

# Adding path of libcpu_extension.so to LD_LIBRARY_PATH
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$GO_WORK_DIR/common/video/udfs/native/build/ie_cpu_extension

# Adding path of Generic Plugin
export GST_PLUGIN_PATH=$GST_PLUGIN_PATH:"/usr/local/lib/gstreamer-1.0"

python3 itm.py