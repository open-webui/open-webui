#!/bin/bash
echo "Warning: This will remove all containers and volumes, including persistent data. Do you want to continue? [Y/N]"
read ans
if [ "$ans" == "Y" ] || [ "$ans" == "y" ]; then
  docker-compose down -v
else
  echo "Operation cancelled."
fi
