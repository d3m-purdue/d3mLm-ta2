# d3mLm-ta2
A mock TA2 module that creates linear, quadratic, and loess models of input data

## Setup and testing instructions

1. Prepare the python virtual environment: `npm run pythonprep`

2. Prepare the R environment: `npm run rprep`

   You may need to install some R packages to your environment for this step.
Watch the error output from the step to see what needs to be installed.

3. Compile the protobuf spec: `npm run protobuf`

4. Create an output directory for the TA2 mock service: `mkdir -p <somedir>`

5. Run the server (using the output directory you just created): `npm run server
   -- --outdir <somedir>`

5. Run the client (specifying the directory where the D3M problem schemata are
   stored): `npm run client -- --datadir </path/to/data>`
