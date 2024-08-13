"""
Entry Point of Functions Application
"""

import azure.functions as func
from src.answer import bp_answer
from src.healthcheck import bp_healthcheck

app = func.FunctionApp()

app.register_blueprint(bp_healthcheck)
app.register_blueprint(bp_answer)
