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
set the "tag" you find in step 2 to `kubernetes\helmvalues.yaml`
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
```
## 4. install and update
if you change some configures in helm, also use this command to upload the changes, no need to uninstall it.
```bash
helm upgrade --install myopenui kubernetes/helm/ --namespace hrwebui
```
## 5. uninstall
```bash
helm uninstall myopenui -n hrwebui
```
## 6. check pod and service
```bash
kubectl get pod -n hrwebui
kubectl get svc -n hrwebui
```
## 7. access service
[HR service](https://hr.ciai-mbzuai.ac.ae/)