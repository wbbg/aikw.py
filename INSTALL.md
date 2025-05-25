---
title: Install instructions for aiwt.py 
---

# run OLLAMA in docker
## docker nvidia support

on some installations it might be nessesary to start docker as `sudo docker ...`

### Arch Linux

1. be sure docker is o.k.:
```bash
docker run --rm hello-world
```

otherwise consult [archlinux docs](https://wiki.archlinux.org/title/Docker)

2. install NVIDIA container toolkit
```bash{.numberLines}
sudo pacman -S nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

3. check success with
```bash
docker run --rm --runtime=nvidia --gpus all nvidia/cuda:11.6.2-base-ubuntu20.04 nvidia-smi
```

should look like:

```text{.tight-code .wide .extra-wide}
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


### other distros

see [NVIDIA Installation guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)

# install Ollama without docker
see [ollama.com](https://ollama.com/download)

# install aikw.py in subdir with virtual environment

1. git clone into **SUBDIR**
    - `git clone https://github.com/wbbg/aikw.py.git`
2. cd **SUBDIR**
    - `cd aikw.py`
3. make a virtual environment in .venv/ and activate it
```bash
python3 -m venv .venv
source .venv/bin/activate
```
4. install requirements
```bash
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```
5. run ollama docker image:
```bash
docker compose -f docker/docker-compose-nvidia.yml up -d
```
or, without NVIDIA support
```bash
docker compose -f docker/docker-compose.yml up -d
```
- to see logs from docker ai run `docker logs -f ollama` in other terminal
- to check if docker container is running `docker ps`

**or, if you want to add the AI to your [tailnet](https://tailscale.com/):**

This is to access the OLLAMA container remotely, f.i. to load a different model 
with `ollama pull ...` without access to the docker host.
This way you can ask somebody with a powerful NVIDIA card to run your container and ssh into the container directly.

- create the file docker/.env:
```docker/.env
hostname=<the name of the container in your tailnet>
AUTHORIZED_KEYS_FILE=<path to a file with public keys for ssh>
```
then build and start the two containers (ollama attached to tailscale)
```bash
docker compose -f docker/nvidia-tailscale.yml up -d
```
see the logs of the tailscale container with `docker logs ts-ollama`
to see the URL you can use to add this container to your *tailnet*. 
Maybe disable key expiery for <hostname> in [Tailscale Machines](https://login.tailscale.com/admin/machines).

- The ${AUTHORIZED_KEYS_FILE} is copied into the container. If it is not valid, there will be no SSH access, 
because password is forbidden for root.

- after adding the container to your **tailnet** test with:
```bash
ssh root@<hostname> [-i id_file]
```

6. load ai model llava:v1.6
```bash
docker exec -it ollama ollama pull llava:v1.6
```

See [Ollama Library](https://ollama.com/library?sort=popular) for other models. 
All models with the "vision" tag are interesting. Try f.i. **gemma3**.

If you run OLLAMA on a different machine, make sure you can reach **`http://<remote-machine ip or name>:11434/`**.
Once the OLLAMA container is up and running continue with [README.md](./README.md)
