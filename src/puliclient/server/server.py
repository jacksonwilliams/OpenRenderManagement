#!/usr/bin/python
# -*- coding: utf8 -*-
from __future__ import absolute_import

"""
"""
__author__ = "Jerome Samson"
__copyright__ = "Copyright 2014, Mikros Image"

import logging
try:
    import simplejson as json
except ImportError:
    import json

import requests


class RequestTimeoutError(Exception):
    """ Raised when helper execution is too long. """


class RequestError(Exception):
    """"""


def request(host, port, url, method="get", *args, **kwargs):
    """
    | General wrapper around the "Request" methods
    | Used by Server object when sending request to the main server, can also
    | be used by any worker/specific requests.

    :param host: hostname to reach
    :param port: port to use
    :param url: end part of the url to reach
    :param method: a string indicating wich method to use [get,put,post,delete]

    :return: a json or text data depending of the webservice response
    :raise RequestError: for any error that occured related to the network
    :raise RequestTimeoutError: when a request timeout occur
    """
    try:
        baseUrl = "http://%s:%d" % (host, port)
        url = '/'.join([baseUrl, url])

        if method == "get":
            r = requests.get(url, *args, **kwargs)
        elif method == "post":
            r = requests.post(url, *args, **kwargs)
        elif method == "put":
            r = requests.put(url, *args, **kwargs)
        elif method == "delete":
            r = requests.delete(url, *args, **kwargs)
        else:
            msg = "Unkown HTTP method called: %s" % method
            logging.error(msg)
            raise RequestError(msg)

        if r.status_code in [requests.codes.ok,
                             requests.codes.created,
                             requests.codes.accepted]:
            #
            # Request returned successfully
            #
            try:
                result = r.json()
            except ValueError, e:
                result = r.text
            return result

        elif r.status_code in [requests.codes.bad,
                               requests.codes.unauthorized,
                               requests.codes.forbidden,
                               requests.codes.not_found,
                               requests.codes.not_allowed,
                               requests.codes.not_acceptable,
                               requests.codes.internal_server_error,
                               requests.codes.not_implemented,
                               requests.codes.unavailable,
                               requests.codes.conflict]:
            try:
                msg = r.text
            except:
                msg = ""

            errMsg = "Error return code: %s, response message: '%s'" % (r.status_code, msg)
            logging.error(errMsg)
            raise RequestError(errMsg)
        else:
            raise RequestError

    except requests.exceptions.Timeout as e:
        errMsg = "Timeout: %s" % e
        logging.error(errMsg)
        raise RequestTimeoutError(errMsg)

    except requests.exceptions.ConnectionError as e:
        errMsg = "Network problem occured: the host you're trying to reach is probably down (%s)" % baseUrl
        logging.error(errMsg)
        raise RequestError(errMsg)

    except requests.exceptions.RequestException as e:
        errMsg = "Unhandled request exception: %s" % e
        logging.error(errMsg)
        raise RequestError(errMsg)

    except RequestError as e:
        raise e

    except Exception as e:
        errMsg = "Unhandled exception: %s" % e
        logging.error(errMsg)
        raise e


class Server(object):
    __host = "vfxpc64"
    __port = 8004

    __baseUrl = "http://%s:%d" % (__host, __port)
    __query = ""

    @classmethod
    def setHostConnection(cls, host, port):
        cls.__port = port
        cls.__host = host
        cls.__baseUrl = "http://%s:%d" % (host, port)

    @classmethod
    def getBaseUrl(cls):
        return cls.__baseUrl

    @classmethod
    def request(cls, url, method, *args, **kwargs):
        return request(cls.__host, cls.__port, url, method, *args, **kwargs)

    @classmethod
    def get(cls, url, *args, **kwargs):
        return cls.request(url, "get", *args, **kwargs)

    @classmethod
    def post(cls, url, *args, **kwargs):
        return cls.request(url, "post", *args, **kwargs)

    @classmethod
    def put(cls, url, *args, **kwargs):
        return cls.request(url, "put", *args, **kwargs)

    @classmethod
    def delete(cls, url, *args, **kwargs):
        return cls.request(url, "delete", *args, **kwargs)
