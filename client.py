import grpc

from core_pb2 import Feature
from core_pb2 import PipelineCreateRequest
from core_pb2 import PipelineExecuteRequest
from core_pb2 import SessionRequest
from core_pb2 import SessionContext
from core_pb2 import TaskType
from core_pb2_grpc import CoreStub

import core_pb2
version = core_pb2.DESCRIPTOR.GetOptions().Extensions[core_pb2.protocol_version]


def start_session(stub):
    response = stub.StartSession(SessionRequest(user_agent='modsquad',
                                                version=version))

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
                              train_features=[Feature(feature_id='foo', data_uri='file:///o_185/Slugging_pct'),
                                              Feature(feature_id='foo', data_uri='file:///o_185/At_bats')],
                              task=TaskType.Value('REGRESSION'),
                              task_description='Super cool task!',
                              target_features=[Feature(feature_id='bam', data_uri='file:///o_185/Runs')])
    resp = stub.CreatePipelines(x)

    pipeline_id = None
    for r in resp:
        print r
        if r.pipeline_id:
            pipeline_id = r.pipeline_id

    resp = stub.ExecutePipeline(PipelineExecuteRequest(context=use.context,
                                                       pipeline_id=pipeline_id,
                                                       predict_features=[Feature(feature_id='foo', data_uri='file:///o_185/At_bats')]))
    for r in resp:
        print r


if __name__ == '__main__':
    main()
