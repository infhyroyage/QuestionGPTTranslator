"""
Module of [GET] /healthcheck
"""

import azure.functions as func

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

    return func.HttpResponse("OK", status_code=200)
