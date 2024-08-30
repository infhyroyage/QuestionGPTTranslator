"""[GET] /healthcheck のモジュール"""

import azure.functions as func
from type.response import GetHealthcheckRes

bp_get_healthcheck = func.Blueprint()


@bp_get_healthcheck.route(
    route="healthcheck",
    methods=["GET"],
    auth_level=func.AuthLevel.FUNCTION,
)
def get_healthcheck(
    req: func.HttpRequest,  # pylint: disable=unused-argument
) -> func.HttpResponse:
    """
    ヘルスチェックの結果を取得する
    """

    body: GetHealthcheckRes = "OK"
    return func.HttpResponse(body, status_code=200)
