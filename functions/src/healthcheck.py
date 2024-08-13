"""
Module of [GET] /healthcheck
"""

import azure.functions as func

bp_healthcheck = func.Blueprint()


@bp_healthcheck.route(route="healthcheck")
def healthcheck(req: func.HttpRequest) -> func.HttpResponse:
    """
    Retrieve Health Check
    """

    # Avoid W0613(unused-argument)
    _ = req

    return func.HttpResponse("OK", status_code=200)
