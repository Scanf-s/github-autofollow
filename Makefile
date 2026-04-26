SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

AWS_REGION := ap-northeast-2
.PHONY: build

build:
	@echo "Build application"
	@rm -rf build/ deploy.zip
	@mkdir -p build
	@uv pip install \
	 --target build \
	 --python-version 3.12 \
	 --python-platform x86_64-manylinux2014 \
	 --no-installer-metadata \
	 --no-compile-bytecode \
	 -r <(uv export --no-dev --no-emit-project --format requirements.txt)
	@cp lambda_function.py build/
	@cp -R service build/
	@cd build && zip -r9 ../deploy.zip . -x "*.pyc" "*__pycache__*" && cd ..
	@echo "Build completed"
