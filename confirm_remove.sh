#!/bin/bash
echo "Warning: This will remove all containers and volumes, including persistent data. Do you want to continue? [Y/N]"
read ans
if [ "$ans" == "Y" ] || [ "$ans" == "y" ]; then
  command docker-compose 2>/dev/null
  if [ "$?" == "0" ]; then
    docker-compose down -v
  else
    docker compose down -v
  fi
else
  echo "Operation cancelled."
fi
