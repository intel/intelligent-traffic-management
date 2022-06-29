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

UBUNTU_IMAGE="ubuntu:22.04"
PIPELINE_SERVER_IMAGE="intel/dlstreamer-pipeline-server:0.7.1"
CONTROLLER_IP=""

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

USER="nobody"
INFERENCE_USER="openvino"
TAG="5.0"

while getopts "c:h" option; do
   case $option in
      c)
         CONTROLLER_IP=$OPTARG
         ;;
      h) # display Help
         echo "c - kube controller ip - REQUIRED"
         echo "h - helper"
         exit;;
     \?) # Invalid option
         echo "Error: Invalid option"
         exit;;
   esac
done
REGISTRY=$CONTROLLER_IP:30003/library


if [[ -z $CONTROLLER_IP ]]; then
   echo "ERROR: Failed to acquire controller ip"
   exit 1
fi

openssl genrsa -out itm-key.pem 2048
openssl req -new -key itm-key.pem -out itm-csr.csr -subj "/C=US/ST=CA/L=SmartCity/O=Intel/OU=IT/CN=intel.com/emailAddress=intel@intel.com"
openssl x509 -req -days 365 -in itm-csr.csr -signkey itm-key.pem -out itm.pem

cp $SCRIPT_DIR/itm-key.pem $SCRIPT_DIR/ITMAnalytics/
cp $SCRIPT_DIR/itm.pem $SCRIPT_DIR/ITMAnalytics/
cp $SCRIPT_DIR/itm-key.pem $SCRIPT_DIR/ITMDashboard/
cp $SCRIPT_DIR/itm.pem $SCRIPT_DIR/ITMDashboard/

cp -r $SCRIPT_DIR/common/ $SCRIPT_DIR/ITMAnalytics/
cp -r $SCRIPT_DIR/common/ $SCRIPT_DIR/ITMVideoInference/
cp -r $SCRIPT_DIR/common/ $SCRIPT_DIR/CloudConnector/
cp -r $SCRIPT_DIR/common/ $SCRIPT_DIR/RuleEngine/

cd $SCRIPT_DIR/CloudConnector
docker build \
    --build-arg UBUNTU_IMAGE=$UBUNTU_IMAGE \
    --build-arg USER=$USER \
    -t $REGISTRY/cloud_connector:$TAG .
docker push $REGISTRY/cloud_connector:$TAG

cd $SCRIPT_DIR/ITMAnalytics
docker build \
    --build-arg UBUNTU_IMAGE=$UBUNTU_IMAGE \
    --build-arg USER=$USER \
    -t $REGISTRY/itm_analytics:$TAG .
docker push $REGISTRY/itm_analytics:$TAG

cd $SCRIPT_DIR/ITMDashboard
docker build \
    --build-arg UBUNTU_IMAGE=$UBUNTU_IMAGE \
    --build-arg USER=$USER \
    -t $REGISTRY/itm_dashboard:$TAG .
docker push $REGISTRY/itm_dashboard:$TAG

cd $SCRIPT_DIR/RuleEngine
docker build \
    --build-arg UBUNTU_IMAGE=$UBUNTU_IMAGE \
    --build-arg USER=$USER \
    -t $REGISTRY/rule_engine:$TAG .
docker push $REGISTRY/rule_engine:$TAG

cd $SCRIPT_DIR/ITMVideoInference
docker build \
    --build-arg PIPELINE_SERVER_IMAGE=$PIPELINE_SERVER_IMAGE \
    --build-arg USER=$INFERENCE_USER \
    -t $REGISTRY/itm_video_inference:$TAG .
docker push $REGISTRY/itm_video_inference:$TAG
