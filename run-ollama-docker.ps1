$host_port = 11434
$container_port = 11434

$use_gpu = Read-Host "Do you want ollama in Docker with GPU support? (y/n)"

docker rm -f ollama 2>$null
docker pull ollama/ollama:latest

$docker_args = "-d -v ollama:/root/.ollama -p $host_port:$container_port --name ollama ollama/ollama"

if ($use_gpu -eq "y") {
    $docker_args = "--gpus=all $docker_args"
}

docker run $docker_args

docker image prune -f