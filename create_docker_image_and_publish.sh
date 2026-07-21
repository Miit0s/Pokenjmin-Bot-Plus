#!/bin/bash

# Don't forget to add the execution right to the file : chmod +x create_docker_image_and_publish.sh

set -e

if [ -z "$1" ]; then
  echo "Erreur : Tu as oublié de spécifier la version."
  echo "Utilisation : ./build.sh 1.0.2"
  exit 1
fi

VERSION=$1
IMAGE_NAME="miitos/pokenjmin-bot"

echo "Début du build pour $IMAGE_NAME:$VERSION et latest..."

sudo docker build -t $IMAGE_NAME:$VERSION -t $IMAGE_NAME:latest .

echo "Envoi des images sur le hub..."
sudo docker push $IMAGE_NAME:$VERSION
sudo docker push $IMAGE_NAME:latest

echo "Terminé avec succès !"