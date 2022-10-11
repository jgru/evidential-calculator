# This container provides all necessary dependencies to run the
# evidential calculator
#
# Author: jgru

FROM debian:bullseye-slim

ENV DEBIAN_FRONTEND=noninteractive
RUN echo 'APT::Get::Assume-Yes "true";' >> /etc/apt/apt.conf

RUN apt-get update

# Required to build NuSMV
RUN apt-get install build-essential
RUN apt-get install zip
RUN apt-get install flex bison
RUN apt-get install zlib1g-dev
RUN apt-get install libexpat-dev

# Required for PyNuSMV
RUN apt-get install python3 python3-dev libpython3-dev
RUN apt-get install python3-pip
RUN apt-get install swig
RUN apt-get install patchelf

RUN pip3 install --upgrade pip
RUN pip3 install setuptools

# # To clone the repo
# RUN apt-get install git

WORKDIR /usr/local/src

# # Copy dependencies
# RUN git clone https://github.com/LouvainVerificationLab/pynusmv /usr/local/src/pynusmv

# Copy and install additional requirements
COPY requirements.txt .
COPY . evidential-calculator

# Install evidential-calculator
RUN cd evidential-calculator && pip3 install .

WORKDIR /data
CMD ["calc_evidence.py"]
