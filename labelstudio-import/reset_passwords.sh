#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="labelstudio_app"

docker exec "$CONTAINER_NAME" label-studio reset_password --username ana.silva@example.com --password 'ChangeMe123!'
docker exec "$CONTAINER_NAME" label-studio reset_password --username bruno.costa@example.com --password 'ChangeMe123!'
docker exec "$CONTAINER_NAME" label-studio reset_password --username carla.rocha@example.com --password 'ChangeMe123!'
docker exec "$CONTAINER_NAME" label-studio reset_password --username daniel.lima@example.com --password 'ChangeMe123!'
docker exec "$CONTAINER_NAME" label-studio reset_password --username elisa.mendes@example.com --password 'ChangeMe123!'
docker exec "$CONTAINER_NAME" label-studio reset_password --username felipe.alves@example.com --password 'ChangeMe123!'
docker exec "$CONTAINER_NAME" label-studio reset_password --username gabriela.sousa@example.com --password 'ChangeMe123!'
docker exec "$CONTAINER_NAME" label-studio reset_password --username henrique.pires@example.com --password 'ChangeMe123!'
docker exec "$CONTAINER_NAME" label-studio reset_password --username isabela.fernandes@example.com --password 'ChangeMe123!'
