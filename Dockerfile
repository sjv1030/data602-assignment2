# Dockerizing MongoDB: Dockerfile for building MongoDB images
# Based on ubuntu:16.04, installs MongoDB following the instructions from:
# http://docs.mongodb.org/manual/tutorial/install-mongodb-on-ubuntu/

FROM       ubuntu:16.04

# Installation:
# Import MongoDB public GPG key AND create a MongoDB list file
RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv EA312927
RUN echo "deb http://repo.mongodb.org/apt/ubuntu $(cat /etc/lsb-release | grep DISTRIB_CODENAME | cut -d= -f2)/mongodb-org/3.2 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-3.2.list

# Update apt-get sources AND install MongoDB
RUN apt-get update && apt-get install -y mongodb-org

# Create the MongoDB data directory
RUN mkdir -p /data/db

# Expose port #27017 from the container to the host
EXPOSE 27017

# Set /usr/bin/mongod as the dockerized entry-point application
ENTRYPOINT ["/usr/bin/mongod"]

# --------------------------------------------------------
# Section above was borrowed. Section below is mine own.
# --------------------------------------------------------
RUN apt-get update && apt-get install -y git
RUN mkdir /hw2

WORKDIR /hw2

#RUN pip install datetime gdax seaborn pymongo matplotlib

COPY requirements.txt ./

RUN git clone https://github.com/sjv1030/data602-assignment2 ../hw2/data602-assignment2

CMD [ "python", "/hw2/data602-assignment2/final.py" ]
