# d3mLm-ta2
A mock TA2 module that creates linear, quadratic, and loess models of input data

## Setup instructions

1. Create a virtual environment: `virtualenv venv`

2. Install the Python dependencies: `./venv/bin/pip install -r requirements.txt`

3. Compile the protobuf spec: `./venv/bin/python -m grpc_tools.protoc -I proto --python_out=. --grpc_python_out=. core.proto`

3. Install the R dependencies: `Rscript script/prep.R`

4. Run the server: `R_LIBS=./rlib ./venv/bin/python d3mLm-ta2.py`

5. Run the client: `./venv/bin/python client.py`
