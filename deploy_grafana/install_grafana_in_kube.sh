#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR

ITM_PERSISTENT_DIR="/opt/intel/itm"
NFS_KERNEL_EXPORTS_FILE="/etc/exports"
GRAFANA_USER_ID="472"
WORKER_IP=""
HTTPS_PROXY=""
CONTROLLER_IP=""

while getopts "c:n:p:h" option; do
   case $option in
      c)
         CONTROLLER_IP=$OPTARG
         ;;
      n)
         WORKER_IP=$OPTARG
         ;;
      p)
         HTTPS_PROXY=${OPTARG}
         ;;
      h) # display Help
         echo "c - kube controller ip - REQUIRED"
         echo "n - kube worker ip is the kubertenes worker node ip - REQUIRED"
         echo "s - https_proxy setting - if you are not behind a proxy this is optional"
         echo "h - helper"
         exit;;
     \?) # Invalid option
         echo "Error: Invalid option"
         exit;;
   esac
done

if [[ -z $WORKER_IP ]]; then
   echo "ERROR: Kube Worker IP is necesarry. Use -h flag to check the required arguments"
   exit 1
fi

if [[ -z $CONTROLLER_IP ]]; then
   echo "ERROR: Kube Controller IP is necessary. Use -h flag to check the required arguments"
   exit 1
fi

echo "Install nfs kernel server and openssl to enable Grafana on your KubeCluster"
echo "Nfs Kernel server will be used for persistent sotrage"
echo "OpenSSL will be used for creating self signed certificates to enable https proxy service for Grafana"
sudo -A apt-get update -y
sudo -A apt-get install nfs-kernel-server openssl -y


# Check Controller Ip
ping -c4 -t1 $CONTROLLER_IP > /dev/null 2>&1
if ! [[ $? -eq 0 ]]; then
    echo "Kubernetes Controller IP not reachable"
    exit 1
fi
# Check Kubernetes worker ip
ping -c4 -t1 $WORKER_IP > /dev/null 2>&1
if ! [[ $? -eq 0 ]]; then
    echo "Kubernetes Worker IP not reachable"
    exit 1
fi

if ! [[ -d $ITM_PERSISTENT_DIR ]]; then
    echo "Create persistent volume dir for itm";
    sudo -A mkdir -p /opt/intel/itm;
fi

if ! [[ $(sudo -A grep "$ITM_PERSISTENT_DIR.*$WORKER_IP" $NFS_KERNEL_EXPORTS_FILE) ]]; then
    echo "Update nfs server exports to add itm"
    sudo -A exportfs -o rw $WORKER_IP:$ITM_PERSISTENT_DIR
fi

echo "Create certs to enable https proxy service for Grafana"
if ! [[ -d $ITM_PERSISTENT_DIR/certs/ ]]; then
    sudo -A mkdir $ITM_PERSISTENT_DIR/certs/
fi
sudo -A openssl genrsa -out $ITM_PERSISTENT_DIR/certs/tls_key.pem 2048 > /dev/null
sudo -A openssl req -new -key $ITM_PERSISTENT_DIR/certs/tls_key.pem -out $ITM_PERSISTENT_DIR/certs/tls_csr.csr -subj "/C=US/ST=CA/L=SmartCity/O=Intel/OU=IT/CN=intel.com/emailAddress=intel@intel.com" > /dev/null
sudo -A openssl x509 -req -days 365 -in $ITM_PERSISTENT_DIR/certs/tls_csr.csr -signkey $ITM_PERSISTENT_DIR/certs/tls_key.pem -out $ITM_PERSISTENT_DIR/certs/tls_cert.pem > /dev/null

echo "Change ITM dir permissions"
sudo -A chown $GRAFANA_USER_ID:$GRAFANA_USER_ID $ITM_PERSISTENT_DIR
sudo -A chmod 755 $ITM_PERSISTENT_DIR
sudo -A chown -R $GRAFANA_USER_ID:$GRAFANA_USER_ID $ITM_PERSISTENT_DIR/*
sudo -A chmod -R 755 $ITM_PERSISTENT_DIR/*
sync

echo "Check certs"
sudo -A openssl x509 -in $ITM_PERSISTENT_DIR/certs/tls_cert.pem -text -noout > /dev/null
if ! [[ $? -eq 0 ]]; then
    echo "Failed to generate certificates"
fi


echo "Install grafana"
if [[ -z $HTTPS_PROXY ]]; then
    echo "Https proxy not required"
    helm install --wait --timeout 10m grafana ./grafana --set setup_config.controllerIP=$CONTROLLER_IP
else
    echo "Install with https proxy applied"
    helm install --wait --timeout 10m grafana ./grafana --set setup_config.controllerIP=$CONTROLLER_IP --set setup_config.https_proxy=$HTTPS_PROXY
fi