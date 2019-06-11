import json
import socket
import datetime
import logging
from .utils import clean_broken_json_text

logger = logging.getLogger(__name__)


def create_imu_session(host, port, username, password):
    """
    Handles the common initialisation process of connecting and
    logging in to an IMu service
    """
    imu_session = Session(host=host, port=int(port))
    imu_session.connect()
    imu_session.login(username=username, password=password)
    return imu_session


class ImuError(Exception):
    pass


class UnexpectedResponse(ImuError):
    pass


class LicenseError(ImuError):
    pass


class Session(object):
    # Extracted from the source code of the perl wrapper provided by the vendor
    block_size = 8192
    # Extracted from the source code of the perl wrapper provided by the vendor
    message_terminator = "\r\n"
    # Indent json payloads to improve log readability by mimicking the tabs that the server uses
    message_json_indent = 8
    # The vendor-provided libraries don't have any timeouts, so we'll default to a large wait
    socket_timeout = 60
    response_success_status = "ok"
    context = None

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.socket_timeout)

    def connect(self):
        logger.info("connecting to %s:%s" % (self.host, self.port))
        self.sock.connect((self.host, self.port))
        logger.info("connected")

    def disconnect(self):
        logger.info("disconnecting from %s:%s" % (self.host, self.port))
        self.sock.close()
        logger.info("disconnected")

    def send(self, message):
        if self.context:
            message["context"] = self.context

        message_bytes = (
            json.dumps(message, indent=self.message_json_indent)
            + self.message_terminator
        )

        self.sock.sendall(message_bytes.encode("utf8"))
        logger.debug('Sent: """%s"""' % message_bytes)

        # Large response come in blocks, so we need to buffer input before deserialization
        response = self.sock.recv(self.block_size)
        buff = [response]
        expected_end_of_message = ("\n}" + self.message_terminator).encode("utf8")
        while not response.endswith(expected_end_of_message):
            response = self.sock.recv(self.block_size)
            buff.append(response)
        response_bytes = bytes().join(buff)
        logger.debug('Received: """%s"""' % response_bytes)

        if not response_bytes:
            raise UnexpectedResponse(
                'No response bytes received.\nSent: """%s"""\n\nReceived: """%s"""'
                % (message_bytes, response_bytes)
            )

        # IMu can send malformed JSON
        cleaned_response_bytes = clean_broken_json_text(response_bytes)

        # Handle encoding issues
        decoded_cleaned_response_bytes = cleaned_response_bytes.encode("utf-8")

        try:
            response_data = json.loads(decoded_cleaned_response_bytes)
        except ValueError:
            raise UnexpectedResponse(
                'Cannot deserialize cleaned response. Sent: """%s"""\n\nCleaned response: """%s"""'
                % (message_bytes, decoded_cleaned_response_bytes)
            )
        if response_data.get("status") != self.response_success_status:
            if (
                response_data.get("status") == "error"
                and response_data.get("code") == 403
            ):
                raise LicenseError(response_data)
            raise UnexpectedResponse(
                "Unexpected response status. Response data: %s" % response_data
            )

        return response_data

    def login(self, username, password):
        if self.context:
            raise ImuError("A context has already been defined: %s" % self.context)

        logger.info('logging in as "%s"' % username)
        response = self.send(
            {
                "login": username,
                "password": password,
                # Not sure exactly what this flag does, but the perl wrapper sends it. From memory,
                # it has something to do with ensuring that the server persists the context
                "spawn": 1,
            }
        )
        # The `context` value seems to be equivalent to a session id
        self.context = response["context"]
        logger.info("logged in")

        return response

    def logout(self):
        if not self.context:
            raise ImuError(
                "Cannot logout as no context has been defined: %s" % self.context
            )

        logger.info('logging out from context "%s"' % self.context)
        response = self.send({"logout": 1, "context": self.context})
        self.context = None
        logger.info("logged out")

        return response


class Term(object):
    OR_OPERATOR = "or"
    AND_OPERATOR = "or"
    OPERATORS = (AND_OPERATOR, OR_OPERATOR)

    def __init__(self, operator=AND_OPERATOR, terms=None):
        if terms is None:
            terms = []
        self.terms = terms
        self.operator = operator
        assert operator.lower() in self.OPERATORS

    def __repr__(self):
        return "%s, operator: %s, terms: %s" % (
            super(Term, self).__repr__(),
            self.operator,
            self.terms,
        )

    def add(self, term, value, operator=None):
        self.terms.append([term, value, operator])

    def add_nested_term(self, operator=OR_OPERATOR):
        assert operator.lower() in self.OPERATORS
        nested_terms = []
        self.terms.append([operator, nested_terms])
        return Term(operator=operator, terms=nested_terms)


class Result(object):
    def __init__(self, mod, data):
        self.mod = mod
        assert isinstance(mod, Module)

        self.data = data
        if not data or "id" not in data:
            raise ImuError("Result data is missing `id`: %s" % data)

    def __repr__(self):
        return "%s [%s]" % (super(Result, self).__repr__(), self.data)

    def sort(self, columns, flags=None):
        assert isinstance(columns, list)
        assert flags is None or isinstance(flags, list)

        if len(columns) == 0:
            raise ImuError("No columns defined for sort")

        message = {
            "method": "sort",
            "id": self.data["id"],
            "params": {"columns": columns, "flags": flags},
        }
        return self._send(message)

    def fetch(self, flag, offset, count, columns=None):
        assert flag in ("start", "current", "end")
        assert isinstance(offset, int)
        assert isinstance(count, int)

        message = {
            "method": "fetch",
            "id": self.data["id"],
            "params": {
                "flag": flag,
                "offset": offset,
                "count": count,
                "columns": columns,
            },
        }
        return self._send(message)

    def fetch_all(self, columns, page_size=100, result_count_threshold=None):
        result_count = self.data["result"]
        if result_count_threshold:
            logger.info(
                "fetching %s of %s records..." % (result_count_threshold, result_count)
            )
        else:
            logger.info("fetching %s records..." % result_count)

        records = []

        fetched = self.fetch("current", 0, page_size, columns)
        imu_records = fetched.data["result"]["rows"]
        while imu_records:
            first_row_number = imu_records[0]["rownum"]
            last_row_number = imu_records[-1]["rownum"]
            logger.info(
                "fetched %s-%s of %s %s"
                % (
                    first_row_number,
                    last_row_number,
                    result_count_threshold or result_count,
                    self.mod.table,
                )
            )
            records += imu_records
            # IMu seems to persistently return the last result as the last page,
            # so we need to manually track the row numbers and bail when appropriate
            if last_row_number < result_count:
                fetched = self.fetch("current", 0, page_size, columns)
                imu_records = fetched.data["result"]["rows"]
            else:
                imu_records = None
            if result_count_threshold and last_row_number >= result_count_threshold:
                imu_records = None

        return records

    def _send(self, message):
        data = self.mod.session.send(message)
        return Result(self.mod, data)


class Module(object):
    def __init__(self, table, session):
        self.table = table
        self.session = session
        assert isinstance(self.session, Session)
        self.sort = []

    def find_terms(self, term):
        assert isinstance(term, Term)

        logger.debug("finding terms: %s" % term)
        message = {
            "name": "Module",
            "create": self.table,
            "method": "findTerms",
            "params": [term.operator, term.terms],
        }
        data = self.session.send(message)
        return Result(self, data)


def parse_datetime(datetime_string):
    return datetime.datetime.strptime(datetime_string, IMU_DATETIME_FORMAT)
