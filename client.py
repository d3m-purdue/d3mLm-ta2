import grpc

from core_pb2 import Feature
from core_pb2 import PipelineCreateRequest
from core_pb2 import SessionRequest
from core_pb2 import SessionContext
from core_pb2 import TaskType
from core_pb2_grpc import CoreStub


def start_session(stub):
    response = stub.StartSession(SessionRequest(user_agent='roni',
                                                version='0.0.1'))

    print 'Server sent message: %s' % (response.context.session_id)
    return response


def end_session(stub, session_id):
    response = stub.EndSession(SessionContext(session_id=session_id))

    print 'Server sent message: %s' % (response)
    return response


def main():
    channel = grpc.insecure_channel('localhost:50001')
    stub = CoreStub(channel)

    # Start three sessions.
    start_session(stub)
    response = start_session(stub)
    use = start_session(stub)

    # End the second session.
    end_session(stub, response.context.session_id)

    # End a non-existent session.
    end_session(stub, '10')

    # Construct a pipeline create request.
    x = PipelineCreateRequest(context=use.context,
                              train_features=[Feature(feature_id='foo', data_uri='foo'),
                                              Feature(feature_id='bar', data_uri='foo'),
                                              Feature(feature_id='baz', data_uri='foo')],
                              task=TaskType.Value('REGRESSION'),
                              task_description='Super cool task!',
                              target_features=[Feature(feature_id='bam', data_uri='bam')])
    resp = stub.CreatePipelines(x)
    for r in resp:
        print r


if __name__ == '__main__':
    main()
