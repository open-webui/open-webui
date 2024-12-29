from setuptools import setup, find_packages

setup(
    name="open-webui-comfyui-agent",
    version="1.0.0",
    description="ComfyUI Agent Plugin for Open WebUI",
    author="OpenHands",
    author_email="openhands@all-hands.dev",
    packages=find_packages(),
    install_requires=[
        "Pillow>=11.0.0",
        "requests>=2.31.0",
        "torch>=2.0.0",
        "transformers>=4.36.0",
        "numpy>=1.24.0",
        "tqdm>=4.66.0",
        "huggingface-hub>=0.19.0"
    ],
    entry_points={
        "open_webui_plugins": [
            "comfyui_agent = comfyui_agent:plugin"
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
)