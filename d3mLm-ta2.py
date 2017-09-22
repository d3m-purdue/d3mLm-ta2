import argparse
from concurrent import futures
import csv
from google.protobuf import text_format
import grpc
import gzip
import json
import os
import rpy2.robjects
import sys
import time
import urlparse

from core_pb2_grpc import CoreServicer
from core_pb2_grpc import add_CoreServicer_to_server

import core_pb2 as cpb

outdir = None

# Load the d3mLm R library and extract the modeling functions from it.
rpy2.robjects.r('library("d3mLm")')
run_lm = rpy2.robjects.r['run_lm']
run_quadratic = rpy2.robjects.r['run_quadratic']
run_loess = rpy2.robjects.r['run_loess']
predict_model = rpy2.robjects.r['predict_model']


def pretty_format(msg):
    return text_format.MessageToString(msg, indent=2)


def make_frame(data):
    for k in data:
        data[k] = rpy2.robjects.FloatVector(data[k])

    return rpy2.robjects.DataFrame(data)


def make_filename(tag):
    return os.path.abspath(os.path.join(outdir, '%s-%f.csv' % (tag, time.time())))


def transpose(mat):
    return map(list, zip(*mat))


def promote(value):
    try:
        value = int(value)
    except ValueError:
        try:
            value = float(value)
        except ValueError:
            pass

    return value


# A helper function to load data columns from the appropriate files.
def load_data(dataset, column, table={}):
    # Insert the dataset into the memoization table if it's not there.
    if dataset not in table:
        table[dataset] = get_dataset(dataset)

    # Extract the columnar values from the dataset
    if column not in table[dataset]:
        raise RuntimeError('dataset %s has no column %s' % (dataset, column))
    return table[dataset][column]


def dump_column(outfile, column, data):
    with open(outfile, 'wb') as f:
        writer = csv.writer(f)
        outdata = map(lambda x: [x], [column] + data)
        writer.writerows(outdata)


# Parse the train_features specs.
def parse_feature(feat):
    comp = urlparse.urlparse(feat.data_uri)

    if comp.scheme != 'file':
        raise RuntimeError('uri scheme must be file!')

    filename = comp.path
    column = feat.feature_id

    return (filename, column)


def get_dataset(datafile):
    try:
        reader = csv.reader(gzip.GzipFile(datafile))
    except IOError:
        try:
            datafile = datafile[0:-3]
            reader = csv.reader(open(datafile))
        except IOError:
            raise RuntimeError('could not open datafile for dataset %s' % (datafile))

    rows = list(reader)

    return {k: map(promote, v) for k, v in zip(rows[0], transpose(rows[1:]))}


class SessionManager:
    def __init__(self):
        self.sessions = {}
        self.next = 0

    def startSession(self):
        session = str(self.next)
        self.sessions[session] = {}

        self.next += 1

        return session

    def endSession(self, session):
        del self.sessions[session]

    def addPipeline(self, session, id):
        self.sessions[session][id] = None

sm = SessionManager()


class D3mLm(CoreServicer):
    def StartSession(self, request, context):
        session = sm.startSession()

        response = cpb.SessionResponse(response_info=cpb.Response(status=cpb.Status(code=cpb.StatusCode.Value('OK'),
                                                                                    details='')),
                                       user_agent=request.user_agent,
                                       version=request.version,
                                       context=cpb.SessionContext(session_id=str(session)))

        print '[StartSession]'
        print 'request:'
        print pretty_format(request)
        print 'response:'
        print pretty_format(response)

        return response

    def EndSession(self, request, context):
        if request.session_id not in sm.sessions:
            return cpb.Response(status=cpb.Status(code=cpb.StatusCode.Value('SESSION_UNKNOWN'),
                                                  details='session id %s is not valid' % (request.session_id)))

        del sm.sessions[request.session_id]

        response = cpb.Response(status=cpb.Status(code=cpb.StatusCode.Value('OK'),
                                details=''))

        print '[EndSession]'
        print 'response:'
        print pretty_format(response)

        return response

    def CreatePipelines(self, req, ctx):
        print '[CreatePipelines]'
        print 'request:'
        print pretty_format(req)

        prog = cpb.PipelineCreateResult(response_info=cpb.Response(status=cpb.Status(code=cpb.StatusCode.Value('OK'))),
                                        progress_info=cpb.Progress.Value('SUBMITTED'),
                                        pipeline_id=None,
                                        pipeline_info=None)

        print 'progress:'
        print pretty_format(prog)

        yield prog

        # Gather up the columns used for training.
        train_features = map(lambda x: parse_feature(x), req.train_features)
        train_data = {k: v for k, v in map(lambda x: (x[1], load_data(*x)), train_features)}
        train_data_cols = train_data.keys()

        # Extract the column used for prediction.
        pred_feature = parse_feature(req.target_features[0])
        if pred_feature[1] not in train_data:
            pred_data = load_data(*pred_feature)
            train_data[pred_feature[1]] = pred_data

        # Run the linear model and parse the result.
        result = json.loads(str(run_lm(make_frame(train_data), pred_feature[1], rpy2.robjects.StrVector(train_data_cols))))

        # Grab the pipeline id and store it in the session table.
        pipeline_id = result['id']
        sm.addPipeline(req.context.session_id, pipeline_id)

        # Extract the results of running the model on the training data and save
        # to disk.
        fitted = result['diag_data']['.fitted']
        outfile = make_filename(pipeline_id)
        dump_column(outfile, pred_feature[1], fitted)

        response = cpb.PipelineCreateResult(response_info=cpb.Response(status=cpb.Status(code=cpb.StatusCode.Value('OK'))),
                                            progress_info=cpb.Progress.Value('COMPLETED'),
                                            pipeline_id=pipeline_id,
                                            pipeline_info=cpb.Pipeline(predict_result_uris=['file://%s' % (outfile)],
                                                                       output=cpb.OutputType.Value('REAL'),
                                                                       scores=[cpb.Score(metric=cpb.Metric.Value('R_SQUARED'),
                                                                                         value=result['diag_model']['r.squared'])]))

        print 'response:'
        print pretty_format(response)

        yield response


    def ExecutePipeline(self, req, ctx):
        print '[ExecutePipeline]'
        print 'request:'
        print pretty_format(req)

        # Check for valid session/pipeline.
        session_id = req.context.session_id
        if session_id not in sm.sessions or req.pipeline_id not in sm.sessions[session_id]:
            # TODO return failure message
            pass

        # Prepare the input data.
        data = {column: load_data(filename, column) for filename, column in map(lambda x: parse_feature(x), req.predict_features)}
        column_names = data.keys()

        # Run the model.
        results = json.loads(str(predict_model(req.pipeline_id, make_frame(data), rpy2.robjects.StrVector(column_names))))
        outfile = make_filename(req.pipeline_id)
        dump_column(outfile, 'predicted', results['fitted'])

        response = cpb.PipelineExecuteResult(response_info=cpb.Response(status=cpb.Status(code=cpb.StatusCode.Value('OK'))),
                                             progress_info=cpb.Progress.Value('COMPLETED'),
                                             pipeline_id=req.pipeline_id,
                                             result_uris=['file://%s' % (outfile)])
        print 'response:'
        print pretty_format(response)

        yield response


def main():
    # Set up argument parsing.
    parser = argparse.ArgumentParser(description='Purdue team mock TA2 server')
    parser.add_argument('--outdir', type=str, required=True, help='Location to write output files')

    # Parse command line arguments.
    args = parser.parse_args(sys.argv[1:])
    global outdir
    outdir = os.path.abspath(args.outdir)

    # Set up and launch the server process.
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
