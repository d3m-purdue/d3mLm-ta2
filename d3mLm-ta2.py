from concurrent import futures
import grpc
import time

from core_pb2_grpc import CoreServicer
from core_pb2_grpc import add_CoreServicer_to_server

from core_pb2 import SessionContext
from core_pb2 import SessionResponse
from core_pb2 import Response
from core_pb2 import Status
from core_pb2 import StatusCode


sessions = {}


class D3mLm(CoreServicer):
    def StartSession(self, request, context):
        print request
        return SessionResponse(response_info=Response(status=Status(code=StatusCode.Value('OK'),
                                                                    details='Everything\'s cool')),
                               user_agent=request.user_agent,
                               version=request.version,
                               context=SessionContext(session_id='hello'))


def main():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    add_CoreServicer_to_server(D3mLm(), server)
    server.add_insecure_port('[::]:50001')
    server.start()

    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == '__main__':
    main()
