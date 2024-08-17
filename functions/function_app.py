"""
Entry Point of Functions Application
"""

import azure.functions as func
from src.answer import bp_answer
from src.healthcheck import bp_healthcheck
from src.import_items import bp_import_items
from src.test import bp_test
from src.tests import bp_tests

app = func.FunctionApp()

app.register_blueprint(bp_answer)
app.register_blueprint(bp_healthcheck)
app.register_blueprint(bp_import_items)
app.register_blueprint(bp_test)
app.register_blueprint(bp_tests)
