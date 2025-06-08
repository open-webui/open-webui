# Open WebUI (OWUI) Deployment Project

This directory contains the infrastructure-as-code (CDK) and operational resources for deploying our instance of the Open WebUI application.

## Getting Started & Local Development

Before building or deploying, please familiarize yourself with the standard operating procedure for this service.

**Key Documentation:**

* **[SOP: Building and Testing the Open WebUI Docker Image](../../Documents/SOPs/engineering/proposed/SOP-01 (proposed) Building and Testing the Open WebUI Docker Image.md)**: This document contains essential instructions for updating the source code from the original repository, building the `arm64` Docker image locally, and troubleshooting common Docker Desktop issues. **All developers should read this before working on this service.**

## Deployment

Deployment is managed via CDK stacks. See the `owui-cdk` readme for details on deploying the service stacks (e.g., `owui-stack`, `ecr-stack`, etc.).

---

# Project workflow

[![](https://mermaid.ink/img/pako:eNq1k01rAjEQhv_KkFNLFe1N9iAUevFSRVl6Cci4Gd1ANtlmsmtF_O_N7iqtHxR76ClhMu87zwyZvcicIpEIpo-KbEavGjceC2lL9EFnukQbIGXygNye5y9TY7DAZTpZLsjXXVYXg3dapRM4hh9mu5A7-3hTfSXtAtJK21Tsj8dPl3USmJZkGVbebWNKD2rNOjAYl6HJHYdkNBwNpb3U9aNZvzFNYE6h8tFiSyZzBUGJG4K1dwVwTSYQrCptlLRvLt5dA5i2la5Ruk51Ux0VKQjuxPVbAwuyiuFlNgHfzJ5DoxtgqQf1813gnZRLZ5lAYcD7WT1lpGtiQKug9C4jZrrp-Fd-1-Y1bdzo4dvnZDLz7lPHyj8sOgfg4x84E7RTuEaZt8yRZqtDfgT_rwG2u3Dv_ERPFOQL1Cqu2F5aAClCTgVJkcSrojVWJkgh7SGmYhXcYmczkQRfUU9UZfQ4baRI1miYDl_QqlPg?type=png)](https://mermaid.live/edit#pako:eNq1k01rAjEQhv_KkFNLFe1N9iAUevFSRVl6Cci4Gd1ANtlmsmtF_O_N7iqtHxR76ClhMu87zwyZvcicIpEIpo-KbEavGjceC2lL9EFnukQbIGXygNye5y9TY7DAZTpZLsjXXVYXg3dapRM4hh9mu5A7-3hTfSXtAtJK21Tsj8dPl3USmJZkGVbebWNKD2rNOjAYl6HJHYdkNBwNpb3U9aNZvzFNYE6h8tFiSyZzBUGJG4K1dwVwTSYQrCptlLRvLt5dA5i2la5Ruk51Ux0VKQjuxPVbAwuyiuFlNgHfzJ5DoxtgqQf1813gnZRLZ5lAYcD7WT1lpGtiQKug9C4jZrrp-Fd-1-Y1bdzo4dvnZDLz7lPHyj8sOgfg4x84E7RTuEaZt8yRZqtDfgT_rwG2u3Dv_ERPFOQL1Cqu2F5aAClCTgVJkcSrojVWJkgh7SGmYhXcYmczkQRfUU9UZfQ4baRI1miYDl_QqlPg)

