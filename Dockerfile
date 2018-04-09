FROM amancevice/pandas:0.22.0-python3-alpine

RUN apk update && apk upgrade && \
    apk add --no-cache git

RUN apk add --update curl gcc g++

RUN apk add py-lxml 

RUN mkdir /hw2

WORKDIR /hw2

RUN pip3 install datetime json gdax seaborn pymongo matplotlib

COPY requirements.txt ./

RUN git clone https://github.com/sjv1030/data602-assignment2 ../hw2/data602-assignment2

CMD [ "python3