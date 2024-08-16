"""
Module of [GET] /healthcheck
"""

import azure.functions as func
from type.response import GetHealthcheckRes

bp_healthcheck = func.Blueprint()


@bp_healthcheck.route(
    route="healthcheck",
    methods=["GET"],
    auth_level=func.AuthLevel.FUNCTION,
)
def healthcheck(
    req: func.HttpRequest,  # pylint: disable=unused-argument
) -> func.HttpResponse:
    """
    Retrieve Health Check
    """

    body: GetHealthcheckRes = "OK"
    return func.HttpResponse(body, status_code=200)
