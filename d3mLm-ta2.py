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


class SessionManager:
    def __init__(self):
        self.sessions = {}
        self.next = 0

    def startSession(self):
        session = str(self.next)
        self.sessions[session] = None

        self.next += 1

        return session

    def endSession(self, session):
        del self.sessions[session]


sm = SessionManager()


class D3mLm(CoreServicer):
    def StartSession(self, request, context):
        session = sm.startSession()

        response = SessionResponse(response_info=Response(status=Status(code=StatusCode.Value('OK'),
                                                                        details='')),
                                   user_agent=request.user_agent,
                                   version=request.version,
                                   context=SessionContext(session_id=str(session)))

        print '[StartSession]'
        print 'response:'
        print response

        return response

    def EndSession(self, request, context):
        if request.session_id not in sm.sessions:
            return Response(status=Status(code=StatusCode.Value('SESSION_UNKNOWN'),
                                          details='session id %s is not valid' % (request.session_id)))

        del sm.sessions[request.session_id]

        response = Response(status=Status(code=StatusCode.Value('OK'),
                            details=''))

        print '[EndSession]'
        print 'response:'
        print response

        return response


def main():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    add_CoreServicer_to_server(D3mLm(), server)
    server.add_insecure_port('[::]:50001')
    server.start()

    print 'Server started, waiting for requests'

    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == '__main__':
    main()
