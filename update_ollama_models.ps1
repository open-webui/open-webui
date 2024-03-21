# update_llm.ps1

# Retrieves the list of LLMs installed in the Docker container
$llm_list = docker exec ollama ollama list | Select-Object -Skip 1 | ForEach-Object { $_.Split()[0] }

# Loop over each LLM to update it
foreach ($llm in $llm_list) {
    docker exec ollama ollama pull $llm
}