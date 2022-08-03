# This container provides all necessary dependencies to run the
# evidential calculator
#
# Author: jgru

FROM python:3.9.13-slim-bullseye

# Just for the convenience of it
RUN apt-get -y update

# Required to build NuSMV
RUN apt-get -y install build-essential
RUN apt-get -y install zip
RUN apt-get -y install flex bison
RUN apt-get -y install zlib1g-dev
RUN apt-get -y install libexpat-dev

# Required for PyNuSMV
RUN apt-get -y install python3 python3-dev libpython3-dev
RUN apt-get -y install python3-pip
RUN apt-get -y install swig
RUN apt-get -y install patchelf

RUN pip3 install --upgrade pip
RUN pip3 install setuptools

# # To clone the repo
# RUN apt-get -y install git

WORKDIR /usr/local/src

# # Copy dependencies
# RUN git clone https://github.com/LouvainVerificationLab/pynusmv /usr/local/src/pynusmv

# Copy and install additional requirements
COPY requirements.txt .
COPY . evidential-calculator

# Install evidential-calculator
RUN cd evidential-calculator && pip3 install .

WORKDIR /data
ENTRYPOINT ["calc-evidence"]
