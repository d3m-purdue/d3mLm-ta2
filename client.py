import grpc

from core_pb2 import SessionRequest
from core_pb2_grpc import CoreStub


def main():
    channel = grpc.insecure_channel('localhost:50001')
    stub = CoreStub(channel)
    response = stub.StartSession(SessionRequest(user_agent='roni',
                                                version='0.0.1'))

    print 'Server sent message: %s' % (response.context.session_id)


if __name__ == '__main__':
    main()
