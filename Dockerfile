# FROM amancevice/pandas:0.22.0-python3-alpine
FROM python:3.6

#RUN apk update && apk upgrade && apk add --no-cache git

#RUN apk add --update curl gcc g++ libpng freetype-dev

RUN mkdir /hw2

WORKDIR /hw2

# RUN pip install --upgrade pip

# RUN pip install datetime gdax seaborn pymongo matplotlib

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

RUN git clone https://github.com/sjv1030/data602-assignment2 ../hw2/data602-assignment2

EXPOSE 27017

CMD [ "python3", "/hw2/data602-assignment2/SVasquez_assignment2.py" ]
