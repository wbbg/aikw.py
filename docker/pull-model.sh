#! env zsh

DEFAULT_MODEL=llava:v1.6
CONTAINER=ollama

if [[ "$1" == "" ]]; then
	MODEL=$DEFAULT_MODEL
else
	MODEL=$1
fi

docker exec -it $CONTAINER ollama pull $MODEL
