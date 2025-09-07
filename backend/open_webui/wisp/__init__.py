import os
import sys
import grpc
from typing import Optional

grpc_channel: Optional[grpc.Channel] = None
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)


def setup_protobuf():
    global grpc_channel
    current_dir = os.path.dirname(os.path.abspath(__file__))
    protobuf_path = os.path.join(current_dir, 'protobuf')
    if protobuf_path not in sys.path:
        sys.path.insert(0, protobuf_path)

    grpc_channel = grpc.insecure_channel('localhost:9090')


def shutdown_protobuf():
    global grpc_channel
    ch = grpc_channel
    if ch is None:
        return
    ch.close()
    grpc_channel = None


setup_protobuf()
