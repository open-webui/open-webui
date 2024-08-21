.PHONY: ansible/install
ansible/install:
	@sudo apt update
	@sudo apt install -y software-properties-common
	@sudo add-apt-repository --yes --update ppa:ansible/ansible
	@sudo apt install -y ansible