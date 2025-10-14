"""
Dual Image Fusion Workflow Template
2 imgs fusion
- img1：main ref(arichitecture and main body)
- img2：style ref
- use 2 LoRA + ControlNet style fusion
"""

WORKFLOW = {
    "1": {
        "inputs": {
            "image": "PLACEHOLDER_IMAGE_1"  # 🔑 main reference/architecture
        },
        "class_type": "LoadImage",
        "_meta": {
            "title": "Load Image 1 (Main Reference)"
        }
    },
    "2": {
        "inputs": {
            "lora_url": "https://huggingface.co/XLabs-AI/flux-RealismLora/resolve/main/lora.safetensors",
            "scale": 1.0
        },
        "class_type": "FalAPIFluxLoraConfigNode",
        "_meta": {
            "title": "LoRA 1 - Realism Style"
        }
    },
    "3": {
        "inputs": {
            "path": "InstantX/FLUX.1-dev-Controlnet-Canny",
            "conditioning_scale": 0.5,
            "config_url": "",
            "variant": "",
            "control_image": ["1", 0]
        },
        "class_type": "FalAPIFluxControlNetConfigNode",
        "_meta": {
            "title": "ControlNet - Structure Preservation"
        }
    },
    "4": {
        "inputs": {
            "prompt": "",  
            "width": 1024,
            "height": 1024,
            "num_inference_steps": 50,
            "guidance_scale": 3.5,
            "num_images": 1,
            "enable_safety_checker": True,
            "strength": 0.9,  
            "seed": 42,
            "image": ["1", 0],
            "lora_1": ["2", 0],
            "lora_2": ["9", 0],
            "controlnet": ["3", 0]
        },
        "class_type": "FalAPIFluxDevWithLoraAndControlNetImageToImageNode",
        "_meta": {
            "title": "Dual-Style Fusion Processing"
        }
    },
    "5": {
        "inputs": {
            "images": ["1", 0]
        },
        "class_type": "PreviewImage",
        "_meta": {
            "title": "Preview Image 1"
        }
    },
    "6": {
        "inputs": {
            "images": ["4", 0]
        },
        "class_type": "PreviewImage",
        "_meta": {
            "title": "Preview Fusion Result"
        }
    },
    "7": {
        "inputs": {
            "filename_prefix": "fal_flux_dual_style_fusion",
            "images": ["4", 0]
        },
        "class_type": "SaveImage",
        "_meta": {
            "title": "Save Fused Image"
        }
    },
    "8": {
        "inputs": {
            "image": "PLACEHOLDER_IMAGE_2"  # 🔑 style reference
        },
        "class_type": "LoadImage",
        "_meta": {
            "title": "Load Image 2 (Style Reference)"
        }
    },
    "9": {
        "inputs": {
            "lora_url": "https://huggingface.co/alvdansen/flux-koda/resolve/main/araminta_k_flux_koda.safetensors",
            "scale": 0.9
        },
        "class_type": "FalAPIFluxLoraConfigNode",
        "_meta": {
            "title": "LoRA 2 - Koda Artistic Style"
        }
    },
    "10": {
        "inputs": {
            "images": ["8", 0]
        },
        "class_type": "PreviewImage",
        "_meta": {
            "title": "Preview Image 2"
        }
    }
}

# main nodes id
MAIN_NODE_ID = "4"

# 2 imgs uploading
IMAGE_LOADER_NODES = ["1", "8"]  

# parameters matrix
PARAM_MAPPING = {
    "prompt": ("4", "prompt"),
    "width": ("4", "width"),
    "height": ("4", "height"),
    # strength fixed = 0.9
}

# default
DEFAULT_PARAMS = {
    "width": 1024,
    "height": 1024,
}