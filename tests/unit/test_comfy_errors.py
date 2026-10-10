from creator_studio.adapters.image.comfy_errors import ComfyErrorCode, classify_comfy_message


def test_classify_comfy_messages() -> None:
    assert classify_comfy_message("Connection refused") == ComfyErrorCode.COMFY_UNREACHABLE
    assert classify_comfy_message("job timed out after 300s") == ComfyErrorCode.TIMEOUT
    assert classify_comfy_message("custom node missing: LLLiteLoader") == ComfyErrorCode.CUSTOM_NODE_MISSING
    assert classify_comfy_message("missing_node_type Node 'TextEncode' not found") == ComfyErrorCode.CUSTOM_NODE_MISSING
    assert classify_comfy_message("node type 'Foo' not found") == ComfyErrorCode.CUSTOM_NODE_MISSING
    assert classify_comfy_message("model checkpoint not found") == ComfyErrorCode.MODEL_NOT_FOUND
    assert classify_comfy_message("prompt_outputs_failed_validation") == ComfyErrorCode.WORKFLOW_INVALID
    assert classify_comfy_message("workflow invalid graph") == ComfyErrorCode.WORKFLOW_INVALID
    assert classify_comfy_message("prompt submit rejected") == ComfyErrorCode.SUBMIT_FAILED
    assert classify_comfy_message("output images empty") == ComfyErrorCode.OUTPUT_NOT_FOUND
    assert classify_comfy_message("execution_error: inflate returned error") == ComfyErrorCode.GENERATION_FAILED
    assert classify_comfy_message("sampler crashed") == ComfyErrorCode.GENERATION_FAILED
