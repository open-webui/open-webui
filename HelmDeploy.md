### Install with Helm
## 1. clone the code
use  ssh or https to clone the code
```bash
git clone git@github.com:ciai-engineering/open-webui.git
```
or 
```bash
git clone https://github.com/ciai-engineering/open-webui.git
```
## 2. Find the package
check [Github packages](https://github.com/ciai-engineering/open-webui/pkgs/container/open-webui) to find the package list, we only need the one like git-xxx, without suffix like -cude or -ollama, because we only need install the frontend and related backend service.

## 3. Change the package
set the `tag` you find in step 2 to `kubernetes\helmvalues.yaml` and check the `nodePort`, make sure it is the one you want.
```yaml
hrwebui:
    enabled: true
    annotations: {}
    podAnnotations: {}
    replicaCount: 1
    image:
        repository: ghcr.io/ciai-engineering/open-webui
        tag: ""
        pullPolicy: Always
    ...
    service:
        type: NodePort
        annotations: {}
        port: 80
        containerPort: 8080
        nodePort: 31031
        labels: {}
        loadBalancerClass: "" 
```
## 4. check the ollama service you plan to use 
for our case, we deploy the ollama service and web service in different kubernetes cluster, so we need to set the `externalHost` in `kubernetes\helmvalues.yaml`. we can just left it as empty if we start both services in the same cluster under the same namespace. 
```yaml
ollama:
  externalHost: "http://192.168.100.14:31774"
  # externalHost: "http://192.168.100.14:32383"
  annotations: {}
```
## 5. install and update
if you change some configures in helm, also use this command to upload the changes, no need to uninstall it.
```bash
helm upgrade --install myopenui kubernetes/helm/ --namespace hrwebui
```
## 6. uninstall
```bash
helm uninstall myopenui -n hrwebui
```
## 7. check pod and service
```bash
kubectl get pod -n hrwebui
kubectl get svc -n hrwebui
```
## 9. access service
[HR service](https://hr.ciai-mbzuai.ac.ae/)