"""
Image-to-Image Workflow Template
(LoRA)
"""

WORKFLOW = {
    "1": {
        "inputs": {
            "image": "PLACEHOLDER_WILL_BE_REPLACED"  
        },
        "class_type": "LoadImage",
        "_meta": {
            "title": "Load Input Image"
        }
    },
    "2": {
        "inputs": {
            "lora_url": "https://huggingface.co/alvdansen/flux-koda/resolve/main/araminta_flux_koda.safetensors",
            "scale": 1.8
        },
        "class_type": "FalAPIFluxLoraConfigNode",
        "_meta": {
            "title": "LoRA Configuration"
        }
    },
    "3": {
        "inputs": {
            "prompt": "",  
            "width": 1024,
            "height": 1024,
            "num_inference_steps": 40,
            "guidance_scale": 3.5,
            "num_images": 1,
            "enable_safety_checker": True,
            "strength": 0.9,  
            "seed": 42,
            "sync_mode": "fixed",
            "image": ["1", 0],  
            "lora": ["2", 0]    
        },
        "class_type": "FalAPIFluxDevWithLoraImageToImageNode",
        "_meta": {
            "title": "Fal API Flux Image-to-Image with LoRA"
        }
    },
    "4": {
        "inputs": {
            "images": ["1", 0]
        },
        "class_type": "PreviewImage",
        "_meta": {
            "title": "Preview Original"
        }
    },
    "5": {
        "inputs": {
            "images": ["3", 0]
        },
        "class_type": "PreviewImage",
        "_meta": {
            "title": "Preview Result"
        }
    },
    "6": {
        "inputs": {
            "filename_prefix": "fal_flux_img2img",
            "images": ["3", 0]
        },
        "class_type": "SaveImage",
        "_meta": {
            "title": "Save Image"
        }
    }
}

# node id
MAIN_NODE_ID = "3"

# node for image
IMAGE_LOADER_NODES = ["1"]  

# param projection
PARAM_MAPPING = {
    "prompt": ("3", "prompt"),
    "width": ("3", "width"),
    "height": ("3", "height"),
}

# default
DEFAULT_PARAMS = {
    "width": 1024,
    "height": 1024,
}