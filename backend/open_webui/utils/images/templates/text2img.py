"""
Text-to-Image Workflow Template

"""

WORKFLOW = {
    "1": {
        "inputs": {
            "prompt": "",  # dynamic filling
            "width": 512,
            "height": 512,
            "num_inference_steps": 15,
            "guidance_scale": 3.5,
            "enable_safety_checker": True,
            "seed": 42,
            "num_images": 1,
            "sync_mode": "fixed"
        },
        "class_type": "FalAPIFluxDevNode",
        "_meta": {
            "title": "Fal API Flux Dev - Main Generator"
        }
    },
    "2": {
        "inputs": {
            "images": ["1", 0]
        },
        "class_type": "PreviewImage",
        "_meta": {
            "title": "Preview Output"
        }
    },
    "3": {
        "inputs": {
            "filename_prefix": "fal_flux_simple",
            "images": ["1", 0]
        },
        "class_type": "SaveImage",
        "_meta": {
            "title": "Save Image"
        }
    }
}

# nodes ID
MAIN_NODE_ID = "1"

# projection
PARAM_MAPPING = {
    "prompt": ("1", "prompt"),
    "width": ("1", "width"),
    "height": ("1", "height"),
}

DEFAULT_PARAMS = {
    "width": 512,
    "height": 512,
}