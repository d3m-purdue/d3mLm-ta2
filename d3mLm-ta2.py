from concurrent import futures
import csv
import grpc
import gzip
import itertools
import json
import os
import rpy2.robjects
import string
import time
import urlparse

from core_pb2_grpc import CoreServicer
from core_pb2_grpc import add_CoreServicer_to_server

from core_pb2 import SessionContext
from core_pb2 import SessionResponse
from core_pb2 import PipelineCreateResult
from core_pb2 import Pipeline
from core_pb2 import OutputType
from core_pb2 import Score
from core_pb2 import Metric
from core_pb2 import Response
from core_pb2 import Progress
from core_pb2 import Status
from core_pb2 import StatusCode
from core_pb2 import TaskType


# Load the d3mLm R library and extract the modeling functions from it.
rpy2.robjects.r('library("d3mLm")')
run_lm = rpy2.robjects.r['run_lm']
run_quadratic = rpy2.robjects.r['run_quadratic']
run_loess = rpy2.robjects.r['run_loess']


def make_frame(data):
    for k in data:
        data[k] = rpy2.robjects.FloatVector(data[k])

    return rpy2.robjects.DataFrame(data)


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


def get_dataset(name):
    datafile = os.path.abspath(os.path.join(os.environ.get('TA2_DATA_DIR', './'), name, 'data', 'trainData.csv.gz'))

    try:
        reader = csv.reader(gzip.GzipFile(datafile))
    except IOError:
        try:
            datafile = datafile[0:-3]
            reader = csv.reader(open(datafile))
        except IOError:
            raise RuntimeError('could not open datafile for dataset %s' % (name))

    rows = list(reader)

    return {k: map(promote, v) for k, v in zip(rows[0], transpose(rows[1:]))}


def all_strings():
    for i in itertools.count(1):
        for s in map(lambda x: ''.join(list(x)), itertools.product(string.ascii_lowercase, repeat=i)):
            yield s


class SessionManager:
    def __init__(self):
        self.sessions = {}
        self.next = 0
        self.names = all_strings()

    def startSession(self):
        session = str(self.next)
        self.sessions[session] = {}

        self.next += 1

        return session

    def endSession(self, session):
        del self.sessions[session]

    def createPipeline(self, session):
        name = next(self.names)
        self.sessions[session][name] = None

        return name

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

    def CreatePipelines(self, req, ctx):
        print req.context.session_id

        print TaskType.Name(req.task)
        print req.task_description

        print req.train_features
        print req.target_features

        yield PipelineCreateResult(response_info=None,
                                   progress_info=Progress.Value('SUBMITTED'),
                                   pipeline_id=None,
                                   pipeline_info=None)

        # Parse the train_features specs.
        def parse_feature(feat):
            comp = urlparse.urlparse(feat)

            if comp.scheme != 'file':
                raise RuntimeError('uri scheme must be file!')

            # Interpret the path as a filepath (from some base directory
            # containing data files), with the final component referring to a
            # column name within the data file.
            (filename, column) = os.path.split(comp.path)

            # Strip any leading slash.
            if filename and filename[0] == '/':
                filename = filename[1:]

            return (filename, column)

        # A helper function to load data columns from the appropriate files.
        def load_data(dataset, column, table={}):
            # Insert the dataset into the memoization table if it's not there.
            if dataset not in table:
                table[dataset] = get_dataset(dataset)

            # Extract the columnar values from the dataset
            if column not in table[dataset]:
                raise RuntimeError('dataset %s has no column %s' % (dataset, column))
            return table[dataset][column]

        # Gather up the columns used for training.
        train_features = map(lambda x: parse_feature(x.data_uri), req.train_features)
        train_data = {k: v for k, v in map(lambda x: (x[1], load_data(*x)), train_features)}
        train_data_cols = train_data.keys()

        # Extract the column used for prediction.
        pred_feature = parse_feature(req.target_features[0].data_uri)
        if pred_feature[1] not in train_data:
            pred_data = load_data(*pred_feature)
            train_data[pred_feature[1]] = pred_data

        data_frame = make_frame(train_data)
        result = json.loads(str(run_lm(data_frame, pred_feature[1], rpy2.robjects.StrVector(train_data_cols))))
        print result['diag_model']['r.squared']

        name = sm.createPipeline(req.context.session_id)

        print sm.sessions

        yield PipelineCreateResult(response_info=Response(status=Status(code=StatusCode.Value('OK'))),
                                   progress_info=Progress.Value('COMPLETED'),
                                   pipeline_id=name,
                                   pipeline_info=Pipeline(predict_result_uris=['baf'],
                                                          output=OutputType.Value('REAL'),
                                                          scores=[Score(metric=Metric.Value('R_SQUARED'),
                                                                        value=3.8)]))

    def ExecutePipeline(self, req, ctx):
        pass


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
