from concurrent import futures
import grpc
import random
import rpy2.robjects
import time

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

    def CreatePipelines(self, req, ctx):
        print req.context.session_id

        print TaskType.Name(req.task)
        print req.task_description

        print req.train_features
        print req.target_features

        yield PipelineCreateResult(response_info=None,
                                   progress_info=Progress.Value('SUBMITTED'),
                                   pipeline_id='hello',
                                   pipeline_info=None)

        time.sleep(random.random() * 3)

        yield PipelineCreateResult(response_info=Response(status=Status(code=StatusCode.Value('OK'))),
                                   progress_info=Progress.Value('COMPLETED'),
                                   pipeline_id='hello',
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
