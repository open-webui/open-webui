from wisp import grpc_channel
from wisp.protobuf import service_pb2_grpc


class BaseWisp:

    def __init__(self):
        self.stub = service_pb2_grpc.ServiceStub(grpc_channel)
