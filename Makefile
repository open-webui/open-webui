PACKAGE_DIR := $(CURDIR)/package

### service
SERVICE_NAME := gpt-oi-web

### frontend static resource name
FRONTEND := web

ifeq ($(ENV), test)
BUILD_STAGE := stage
else
BUILD_STAGE := prod
endif

BUILD_CMD := build

.PHONY: install-deps clean pack

### build step
clean:
	rm -rf $(PACKAGE_DIR)
	rm -rf $(CURDIR)/build_tmp
	@echo "clean success"

install-deps:
	npm install --registry=https://registry.npmmirror.com

pack:
	npm run ${BUILD_CMD}
	mkdir -p $(CURDIR)/build_tmp/
	mv $(CURDIR)/build $(CURDIR)/build_tmp/${FRONTEND}
	# 仓库中的nginx配置仅对容器生效，对虚拟机和物理机部署时，仍需要手动调整nginx配置
	cp -r $(CURDIR)/nginx/${ENV}/$(SERVICE_NAME) $(CURDIR)/build_tmp/nginx
	mkdir -p $(PACKAGE_DIR)
	mv $(CURDIR)/build_tmp $(PACKAGE_DIR)/$(SERVICE_NAME)
	rm -rf $(CURDIR)/build_tmp
	@echo "build success"
