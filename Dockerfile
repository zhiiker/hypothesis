FROM node:alpine as build
FROM alpine:3.7

# Set metadata about the image.
LABEL maintainer="Hypothes.is Project and contributors"

# Set environment variables independent of dependencies.
ENV NODE_ENV production

# Expose the default port.
EXPOSE 5000

RUN npm ci --production && npm run build

# Install system build and runtime dependencies.
# Create the hypothesis user, group, home directory and package directory.
# Ensure nginx state and log directories writeable by unprivileged user.
# Install apk build deps (cleanup later after we use them to build packages).
# Install supervisor.
RUN apk add --no-cache \
    ca-certificates \
    collectd \
    collectd-disk \
    collectd-nginx \
    libffi \
    libpq \
    nginx \
    python2 \
    py2-pip \
    git \
    nodejs-npm \
 && addgroup -S hypothesis && adduser -S -G hypothesis -h /var/lib/hypothesis hypothesis \
 && mkdir /etc/collectd/collectd.conf.d \
 && mkdir /var/lib/hypothesis/scripts && mkdir /var/lib/hypothesis/scripts/gulp \
 && mkdir /var/lib/hypothesis/h && mkdir /var/lib/hypothesis/h/static \
 && chown hypothesis:hypothesis /etc/collectd/collectd.conf.d \
 && chown -R hypothesis:hypothesis /var/log/nginx /var/lib/nginx /var/tmp/nginx \
 && apk add --no-cache --virtual build-deps \
    build-base \
    libffi-dev \
    postgresql-dev \
    python-dev \
 && pip install --no-cache-dir -U pip supervisor 

# Set the application environment.
ENV PATH /var/lib/hypothesis/bin:$PATH
ENV PYTHONIOENCODING utf_8
ENV PYTHONPATH /var/lib/hypothesis:$PYTHONPATH

WORKDIR /var/lib/hypothesis

# Copy nginx config
COPY conf/nginx.conf /etc/nginx/nginx.conf

# Copy collectd config
COPY conf/collectd.conf /etc/collectd/collectd.conf

# Copy minimal data to allow installation of dependencies.
COPY requirements.txt package.json gulpfile.js ./

# Copy gulp scripts to allow installation of dependencies.
COPY  scripts/gulp/ ./scripts/gulp/
COPY  h/static/ ./h/static/

# Install node and python packages and cleanup build deps.
RUN npm install --production && npm run build \
  && pip install --no-cache-dir -r requirements.txt  

# Copy the rest of the application files.
COPY . .

# If we're building from a git clone, ensure that .git is writeable
RUN [ -d .git ] && chown -R hypothesis:hypothesis .git || :

RUN  pip install -r tox-requirements.txt

USER hypothesis
