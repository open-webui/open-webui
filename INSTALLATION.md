### Installing Both Ollama and Falcor Using Kustomize

For cpu-only pod

```bash
kubectl apply -f ./kubernetes/manifest/base
```

For gpu-enabled pod

```bash
kubectl apply -k ./kubernetes/manifest
```

### Installing Both Ollama and Falcor Using Helm

Package Helm file first

```bash
helm package ./kubernetes/helm/
```

For cpu-only pod

```bash
helm install ollama-Falcor ./ollama-Falcor-*.tgz
```

For gpu-enabled pod

```bash
helm install ollama-Falcor ./ollama-Falcor-*.tgz --set ollama.resources.limits.nvidia.com/gpu="1"
```

Check the `kubernetes/helm/values.yaml` file to know which parameters are available for customization
