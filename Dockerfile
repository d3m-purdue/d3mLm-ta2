FROM r-base:3.4.1

EXPOSE 50001

RUN apt-get update
RUN apt-get install -y curl sudo python2.7 python2.7-dev python-pip gnupg1

# Install Node.js 6
RUN curl -sL https://deb.nodesource.com/setup_6.x | sudo -E bash - \
  && sudo apt-get install -y nodejs npm \
  && sudo npm install -g npm \
  && ln -s /usr/bin/nodejs /usr/local/bin/node

RUN mkdir /d3m-ta2
COPY . /d3m-ta2

WORKDIR /d3m-ta2

RUN pip install -r requirements.txt
RUN pip install virtualenv
RUN npm run pythonprep
RUN npm run rprep
RUN npm run protobuf

ENTRYPOINT npm run server
