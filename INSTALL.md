## Installation instructions

### docker nvidia support

on some installations it might be nessesary to start docker as `sudo docker ...`

#### Arch Linux

1. be sure docker is o.k.:
```bash
    docker run --rm hello-world
```

otherwise consult [archlinux docs](https://wiki.archlinux.org/title/Docker)

2. install NVIDIA container toolkit
```bash
    sudo pacman -S nvidia-container-toolkit
    sudo nvidia-ctk runtime configure --runtime=docker
    sudo systemctl restart docker
```

3. check success with
```bash
    docker run --rm --runtime=nvidia --gpus all nvidia/cuda:11.6.2-base-ubuntu20.04 nvidia-smi
```

should look like:
```text
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 570.124.04             Driver Version: 570.124.04     CUDA Version: 12.8     |
|-----------------------------------------+------------------------+----------------------+
| GPU  Name                 Persistence-M | Bus-Id          Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
|                                         |                        |               MIG M. |
|=========================================+========================+======================|
|   0  NVIDIA GeForce GTX 1650        Off |   00000000:07:00.0  On |                  N/A |
| 35%   32C    P8            N/A  /   75W |     539MiB /   4096MiB |     28%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+
                                                                                         
+-----------------------------------------------------------------------------------------+
| Processes:                                                                              |
|  GPU   GI   CI              PID   Type   Process name                        GPU Memory |
|        ID   ID                                                               Usage      |
|=========================================================================================|
+-----------------------------------------------------------------------------------------+
```
#### other distros

see [NVIDIA Installation guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)

### install in subdir with virtual environment

1. unpack/ clone git into <subdir>
2. cd <subdir>
3. make a virtual environment in .venv/ and activate
```bash
    python3 -m venv .venv
    source .venv/bin/activate
```
4. install requirements
```bash
    python3 -m pip install --upgrade pip
    python3 -m pip install -r requirements.txt
5. run ollama docker image:
```bash
    docker compose up -f docker/docker-compose.yml -d
```
    to see logs from docker ai run without -d or start `docker logs -f ollama` in other terminal
6. load ai model llava:v1.6
```bash
    docker exec -it ollama ollama pull llava:v1.6
```
7. run aikw.py with verbosity 3 on local ai server with jpg files in subdir:
```bash
    python3 ./aikw.py -vvv -r "r'(?i)\.jpg$' <file or dirs>:
```
