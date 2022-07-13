
This repository contains a prototypical implementation of a tool that calculates the evidence sets of different classes of evidence.

# Table of Contents
- [Dependencies](#org824e92e)
- [Installation](#org1a97ec1)
- [Usage](#org47135c5)


<a id="org824e92e"></a>

# Dependencies

The code in this depends on [PyNuSMV](https://github.com/LouvainVerificationLab/pynusmv), which is included as a submodule. In order to compile it, ensure that you have the following prerequisites installed.

```shell
apt install build-essential zip zlib1g-dev libexpat-dev flex bison swig patchelf
apt install python3 python3-dev libpython3-dev python3-pip
```

If you want to try the tool, it is best to create a virtual environment named `venv` and install the requirements:

```shell
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```


<a id="org1a97ec1"></a>

# Installation

In case you want to install the module named `evidential_calculator`, you could run

```shell
pip3 install .
```

which will install the module as well as the script `calc_evidence`.


<a id="org47135c5"></a>

# Usage

Using the provided tool is straightforward, just supply a model, which is defined in NuSMV's input specification language either by piping it into `stdin` or as a positional argument. In addition to that, specify the class of evidence that should be calculated via `-t` (either "sufficient" or "necessary" evidence).

```shell
cat ../../examples/acme-model.smv | python3 calc_evidence.py -t "sufficient"
```

If you are only interested in a specific action, you could restrict the calculation to that action by supplying `-a`, like it is illustrated below:

```shell
cd src/evidential_calculator
python3 calc_evidence.py -a "add_job_b" -t "sufficient" ../../examples/acme-model.smv
```

For a full reference of the CLI, see the manual page below, or run `calc_evidence.py` with `--help`.

    
    usage: calc_evidence.py [-h] [-a ACTION] [-t {sufficient,necessary}] [-o {org,csv,raw}] [model]
    
    positional arguments:
      model                 Model specified in NuSMV's input language
    
    optional arguments:
      -h, --help            show this help message and exit
      -a ACTION, --action ACTION
                            Name of the action of interest
      -t {sufficient,necessary}, --etype {sufficient,necessary}
                            Type of evidence to calculate
      -o {org,csv,raw}, --output-format {org,csv,raw}
                            Output format of the calculated sets
