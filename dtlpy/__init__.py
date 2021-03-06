#! /usr/bin/env python3
# This file is part of DTLPY.
#
# DTLPY is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# DTLPY is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with DTLPY.  If not, see <http://www.gnu.org/licenses/>.
import logging
import sys
import os

from .exceptions import PlatformException
from . import repositories, exceptions, entities, examples
from .__version__ import version as __version__
from .entities import (
    Box,
    Point,
    Segmentation,
    Polygon,
    Ellipse,
    Classification,
    Subtitle,
    Polyline,
    Filters,
    Trigger,
    AnnotationCollection,
    Annotation,
    Item,
    Codebase,
    Filters,
    Execution,
    Recipe,
    Ontology,
    Label,
    Similarity,
    MultiView,
    ItemLink,
    UrlLink,
    PackageModule,
    PackageFunction,
    FunctionIO,
    Modality,
    Model,
    Checkpoint,
    Workload,
    WorkloadUnit,
    FiltersKnownFields,
    FiltersResource,
    FiltersOperations,
    FiltersMethod,
    FiltersOrderByDirection,
    FiltersKnownFields as KnownFields,
    TriggerResource,
    TriggerAction,
    TriggerExecutionMode,
    PackageInputType
)
from .utilities import Converter, BaseServiceRunner, Progress
from .services import DataloopLogger, ApiClient, check_sdk
from .repositories.packages import PackageCatalog

# check python version
if sys.version_info.major != 3:
    if sys.version_info.minor not in [5, 6]:
        sys.stderr.write(
            'Error: Your Python version "{}.{}" is NOT supported by Dataloop SDK dtlpy. '
            "Supported version are 3.5, 3.6)\n".format(
                sys.version_info.major, sys.version_info.minor
            )
        )
        sys.exit(-1)

if os.name == "nt":
    # set encoding for windows printing
    os.environ["PYTHONIOENCODING"] = ":replace"

"""
Main Platform Interface module for Dataloop
"""
##########
# Logger #
##########
logger = logging.getLogger(name=__name__)
if len(logger.handlers) == 0:
    logger.setLevel(logging.DEBUG)
    log_filepath = DataloopLogger.get_log_filepath()
    # set file handler to save all logs to file
    formatter = logging.Formatter(
        fmt="%(asctime)s.%(msecs)03d [%(levelname)s]-[%(threadName)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh = DataloopLogger(log_filepath, maxBytes=(1048 * 1000 * 5))
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    sh = logging.StreamHandler()
    sh.setLevel(logging.WARNING)
    sh.setFormatter(formatter)
    # set handlers to main logger
    logger.addHandler(sh)
    logger.addHandler(fh)

################
# Repositories #
################
# Create repositories instances
client_api = ApiClient()
projects = repositories.Projects(client_api=client_api)
datasets = repositories.Datasets(client_api=client_api, project=None)
items = repositories.Items(client_api=client_api, datasets=datasets)
packages = repositories.Packages(client_api=client_api)
executions = repositories.Executions(client_api=client_api)
services = repositories.Services(client_api=client_api)
webhooks = repositories.Webhooks(client_api=client_api)
triggers = repositories.Triggers(client_api=client_api)
assignments = repositories.Assignments(client_api=client_api)
tasks = repositories.Tasks(client_api=client_api)
annotations = repositories.Annotations(client_api=client_api)
models = repositories.Models(client_api=client_api)
checkpoints = repositories.Checkpoints(client_api=client_api)

if client_api.token_expired():
    logger.error(
        "Token expired, Please login."
        "\nSDK login options: dl.login(), dl.login_token(), "
        "dl.login_secret()"
        "\nCLI login options: dlp login, dlp login-token, "
        "dlp login-secret"
    )

try:
    check_sdk.check(version=__version__, client_api=client_api)
except Exception:
    logger.debug("Failed to check SDK! Continue without")

verbose = client_api.verbose
login = client_api.login
login_token = client_api.login_token
login_secret = client_api.login_secret
add_environment = client_api.add_environment
setenv = client_api.setenv
token_expired = client_api.token_expired
info = client_api.info


def token():
    """
    token
    :return: token in use
    """
    return client_api.token


def environment():
    """
    environment
    :return: current environment
    """
    return client_api.environment


def init():
    """
    init current directory as a Dataloop working directory
    :return:
    """
    from .services import CookieIO

    client_api.state_io = CookieIO.init_local_cookie(create=True)
    assert isinstance(client_api.state_io, CookieIO)
    logger.info(".Dataloop directory initiated successfully in {}".format(os.getcwd()))


def checkout_state():
    """
    Return the current checked out state
    :return:
    """
    state = client_api.state_io.read_json()
    return state


class ModalityTypeEnum:
    """
    State enum
    """

    OVERLAY = "overlay"


class SimilarityTypeEnum:
    """
    State enum
    """
    ID = "id"
    URL = "url"


class LinkTypeEnum:
    """
    State enum
    """
    ID = "id"
    URL = "url"


class ExecutionStatus:
    SUCCESS = "success"
    FAILED = "failed"
    IN_PROGRESS = "inProgress"
    CREATED = "created"


class HttpMethod:
    GET = "GET"
    POST = "POST"
    DELETE = "DELETE"
    PATCH = "PATCH"


class AnnotationOptions:
    JSON = "json"
    MASK = "mask"
    INSTANCE = "instance"


class AnnotationFormat:
    COCO = "coco"
    VOC = "voc"
    YOLO = "yolo"
    DATALOOP = "dataloop"


class InstanceCatalog:
    REGULAR_XS = "regular-xs"
    REGULAR_S = "regular-s"
    REGULAR_M = "regular-m"
    REGULAR_L = "regular-l"
    REGULAR_XL = "regular-xl"
    HIGHMEM_MICRO = "highmem-micro"
    HIGHMEM_XS = "highmem-xs"
    HIGHMEM_S = "highmem-s"
    HIGHMEM_M = "highmem-m"
    HIGHMEM_L = "highmem-l"
    HIGHMEM_XL = "highmem-xl"
    GPU_K80_S = "gpu-k80-s"


class LoggingLevel:
    DEBUG = "debug"
    WARNING = "warning"
    CRITICAL = "critical"
    INFO = "info"


class ItemStatus:
    COMPLETED = "completed"
    APPROVED = "approved"
    DISCARDED = "discarded"

