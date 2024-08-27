"""
Entry Point of Functions Application
"""

import azure.functions as func
from src.blob_triggered_import import bp_blob_triggered_import
from src.get_healthcheck import bp_get_healthcheck
from src.get_question import bp_get_question
from src.get_test import bp_get_test
from src.get_tests import bp_get_tests
from src.post_answer import bp_post_answer
from src.put_en2ja import bp_put_en2ja
from src.queue_triggered_answer import bp_queue_triggered_answer

app = func.FunctionApp()

app.register_blueprint(bp_blob_triggered_import)
app.register_blueprint(bp_get_healthcheck)
app.register_blueprint(bp_get_question)
app.register_blueprint(bp_get_test)
app.register_blueprint(bp_get_tests)
app.register_blueprint(bp_post_answer)
app.register_blueprint(bp_put_en2ja)
app.register_blueprint(bp_queue_triggered_answer)
