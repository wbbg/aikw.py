#! env zsh

MODEL=llava:v1.6
CONTAINER=ollama

docker exec -it $CONTAINER ollama pull $MODEL
