"""
ComfyUI Workflow Selector

"""

import copy
import logging
from typing import Optional, Tuple, Dict, Any

log = logging.getLogger(__name__)

# Import workflow
from open_webui.utils.images.templates import (
    TEXT2IMG_WORKFLOW,
    TEXT2IMG_PARAM_MAPPING,
    TEXT2IMG_DEFAULT_PARAMS,
    IMG2IMG_WORKFLOW,
    IMG2IMG_IMAGE_LOADER_NODES,
    IMG2IMG_PARAM_MAPPING,
    IMG2IMG_DEFAULT_PARAMS,
    FUSION2IMGS_WORKFLOW,
    FUSION2IMGS_IMAGE_LOADER_NODES,
    FUSION2IMGS_PARAM_MAPPING,
    FUSION2IMGS_DEFAULT_PARAMS,
)


def select_workflow(input_images: Optional[list] = None) -> Tuple[dict, str, dict]:
    """
    according imgae num workflow
    
    Args:
        input_images: input imgs file_id list
    
    Returns:
        (workflow_dict, workflow_type, metadata)
        - workflow_dict: workflow copy
        - workflow_type: "text2img" | "img2img" | "fusion"
        - metadata: include PARAM_MAPPING, DEFAULT_PARAMS, IMAGE_LOADER_NODES...
    """
    if not input_images or len(input_images) == 0:
        # 0 img --> text2img
        log.info("Selected workflow: TEXT2IMG (no input images)")
        return (
            copy.deepcopy(TEXT2IMG_WORKFLOW),
            "text2img",
            {
                "param_mapping": TEXT2IMG_PARAM_MAPPING,
                "default_params": TEXT2IMG_DEFAULT_PARAMS,
                "image_loader_nodes": [],  
            }
        )
    
    elif len(input_images) == 1:
        # 1 img --> img2img
        log.info("Selected workflow: IMG2IMG (1 input image)")
        return (
            copy.deepcopy(IMG2IMG_WORKFLOW),
            "img2img",
            {
                "param_mapping": IMG2IMG_PARAM_MAPPING,
                "default_params": IMG2IMG_DEFAULT_PARAMS,
                "image_loader_nodes": IMG2IMG_IMAGE_LOADER_NODES,
            }
        )
    
    else:  # 2 img --> fusion
        log.info(f"Selected workflow: FUSION (using first 2 of {len(input_images)} images)")
        return (
            copy.deepcopy(FUSION2IMGS_WORKFLOW),
            "fusion",
            {
                "param_mapping": FUSION2IMGS_PARAM_MAPPING,
                "default_params": FUSION2IMGS_DEFAULT_PARAMS,
                "image_loader_nodes": FUSION2IMGS_IMAGE_LOADER_NODES,
            }
        )


def fill_workflow_params(
    workflow: dict,
    metadata: dict,
    params: Dict[str, Any],
    uploaded_filenames: Optional[list] = None
) -> dict:
    param_mapping = metadata["param_mapping"]
    default_params = metadata["default_params"]
    image_loader_nodes = metadata["image_loader_nodes"]
    
    # 1. default and user setting combination
    final_params = {**default_params, **params}
    
    
    for param_key, (node_id, field_name) in param_mapping.items():
        if param_key in final_params and final_params[param_key] is not None:
            value = final_params[param_key]
            workflow[node_id]["inputs"][field_name] = value
            log.debug(f"Filled: workflow[{node_id}][inputs][{field_name}] = {value}")
    # 2. image file name
    if image_loader_nodes and uploaded_filenames:
        for i, node_id in enumerate(image_loader_nodes):
            if i < len(uploaded_filenames):
                filename = uploaded_filenames[i]
                workflow[node_id]["inputs"]["image"] = filename
                log.info(f"Filled image: workflow[{node_id}][inputs][image] = {filename}")
            else:
                log.warning(f"Not enough uploaded images for node {node_id}")
    
    return workflow


def prepare_workflow(
    input_images: Optional[list] = None,
    prompt: str = "",
    width: Optional[int] = None,
    height: Optional[int] = None,
    uploaded_filenames: Optional[list] = None
) -> Tuple[dict, str]:

    # 1. select workflow
    workflow, workflow_type, metadata = select_workflow(input_images)
    
    # 2. param preparation
    params = {"prompt": prompt}
    if width is not None:
        params["width"] = width
    if height is not None:
        params["height"] = height
    
    # 3. fill param
    workflow = fill_workflow_params(
        workflow,
        metadata,
        params,
        uploaded_filenames
    )
    
    log.info(f"0v< Workflow prepared: {workflow_type}")
    return workflow, workflow_type