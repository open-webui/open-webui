############################
# INFRASTRUCTURE
############################

.PHONY: infra/terraform/init
infra/terraform/init:
	@cd $(WORKSPACE)/infra/terraform && terraform init

.PHONY: infra/terraform/plan
infra/terraform/plan:
	@cd $(WORKSPACE)/infra/terraform && terraform plan

.PHONY: infra/terraform/apply
infra/terraform/apply:
	@cd $(WORKSPACE)/infra/terraform && terraform apply -auto-approve

.PHONY: infra/terraform/destroy
infra/terraform/destroy:
	@cd $(WORKSPACE)/infra/terraform && terraform destroy -auto-approve

.PHONY: infra/packer/init
infra/packer/init:
	@cd $(WORKSPACE)/infra/packer/ && packer init imagine.pkr.hcl
	@cd $(WORKSPACE)/infra/packer/ && ansible-galaxy collection install amazon.aws
	@ansible-galaxy role install git+https://github.com/morgangraphics/ansible-role-nvm.git,bf24174


.PHONY: infra/packer/build
infra/packer/build:
	@cd $(WORKSPACE)/infra/packer/ && packer build imagine.pkr.hcl

.PHONY: infra/ansible/run
infra/ansible/run:
	@ansible-playbook -i $(IP), -u ubuntu --private-key $(WORKSPACE)/infra/terraform/secrets/miai-dev-imagine.pem $(WORKSPACE)/infra/packer/ansible/playbook.yml

.PHONY: infra/ec2/ssh
infra/ec2/ssh:
	@ssh -i $(WORKSPACE)/infra/terraform/secrets/miai-dev-imagine.pem ubuntu@$(IP)
