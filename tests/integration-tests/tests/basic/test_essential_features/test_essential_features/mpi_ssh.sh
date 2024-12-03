#!/bin/bash
set -e

_openmpi_module=$1
_remote_host=$2

module load ${_openmpi_module}
sudo -u pcluster-admin $(which mpirun) --host ${_remote_host} hostname
