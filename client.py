import argparse
import grpc
import os.path
import sys

import core_pb2 as cpb
from core_pb2_grpc import CoreStub

import core_pb2

version = core_pb2.DESCRIPTOR.GetOptions().Extensions[core_pb2.protocol_version]


def start_session(stub):
    response = stub.StartSession(cpb.SessionRequest(user_agent='modsquad',
                                                    version=version))

    print 'Server sent message: %s' % (response.context.session_id)
    return response


def end_session(stub, session_id):
    response = stub.EndSession(cpb.SessionContext(session_id=session_id))

    print 'Server sent message: %s' % (response)
    return response


def main():
    # Set up argument parsing.
    parser = argparse.ArgumentParser(description='Purdue team mock TA2 client')
    parser.add_argument('--datadir', type=str, required=True, help='Location of data files')

    # Parse command line arguments.
    args = parser.parse_args(sys.argv[1:])
    datadir = os.path.abspath(args.datadir)

    # Set up a connection to the server.
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
    datafile = os.path.join(datadir, 'o_185', 'data', 'trainData.csv.gz')
    data_uri = 'file://%s' % (datafile)
    x = cpb.PipelineCreateRequest(context=use.context,
                                  train_features=[cpb.Feature(feature_id='Slugging_pct', data_uri=data_uri),
                                                  cpb.Feature(feature_id='At_bats', data_uri=data_uri)],
                                  task=cpb.TaskType.Value('REGRESSION'),
                                  task_description='Super cool task!',
                                  target_features=[cpb.Feature(feature_id='Runs', data_uri=data_uri)])
    resp = stub.CreatePipelines(x)

    pipeline_id = None
    for r in resp:
        print r
        if r.pipeline_id:
            pipeline_id = r.pipeline_id

    resp = stub.ExecutePipeline(cpb.PipelineExecuteRequest(context=use.context,
                                                           pipeline_id=pipeline_id,
                                                           predict_features=[cpb.Feature(feature_id='At_bats', data_uri=data_uri)]))
    for r in resp:
        print r


if __name__ == '__main__':
    main()
