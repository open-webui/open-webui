############################
# INFRASTRUCTURE
############################

.PHONY: infra/terraform/init
infra/terraform/init:
	@cd $(WORKSPACE)/infra/terraform && terraform init

.PHONY: infra/terraform/apply
infra/terraform/apply:
	@cd $(WORKSPACE)/infra/terraform && terraform apply -auto-approve

.PHONY: infra/terraform/destroy
infra/terraform/destroy:
	@cd $(WORKSPACE)/infra/terraform && terraform destroy -auto-approve

.PHONY: infra/packer/build
infra/packer/build:
	@cd $(WORKSPACE)/infra/packer && packer build packer/ami-template.hcl

.PHONY: infra/ansible/run
infra/ansible/run:
	@cd $(WORKSPACE)/infra/ansible && ansible-playbook packer/ansible/playbook.yml -i packer/ansible/inventory.ini
