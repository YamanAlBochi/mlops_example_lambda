import json
import os.path
import time
from datetime import datetime

import boto3
import joblib
from aws_embedded_metrics import metric_scope, MetricsLogger
from aws_embedded_metrics.config import get_config


class EmfMetrics:
    @staticmethod
    def setup():
        metrics_config = get_config()
        metrics_config.namespace = os.environ.get("AWS_LAMBDA_FUNCTION_NAME", metrics_config.namespace) + "_emf"

        # This speeds up unit tests; otherwise it auto-detects and tries to connect to HTTP sockets
        metrics_config.environment = os.environ.get("AWS_EXECUTION_ENV", "local")

    @staticmethod
    @metric_scope
    def put_duration(name: str, duration_seconds: float, metrics: MetricsLogger):
        metrics.put_metric(name, duration_seconds, "Seconds")

    @staticmethod
    @metric_scope
    def put_count(name: str, count: int, metrics: MetricsLogger):
        metrics.put_metric(name, count, "Count")


class Boto3Metrics:
    client = boto3.client('cloudwatch')
    namespace = os.environ.get("AWS_LAMBDA_FUNCTION_NAME", None)

    @staticmethod
    def put_metric_data(metric_name, value, unit):
        if Boto3Metrics.namespace:
            Boto3Metrics.client.put_metric_data(
                Namespace=Boto3Metrics.namespace + "_boto3",
                MetricData=[
                    {
                        'MetricName': metric_name,
                        'Timestamp': datetime.now(),
                        'Value': value,
                        'Unit': unit
                    },
                ])

    @staticmethod
    def put_duration(name: str, duration_seconds: float):
        Boto3Metrics.put_metric_data(name, duration_seconds, "Seconds")

    @staticmethod
    def put_count(name: str, count: int):
        Boto3Metrics.put_metric_data(name, count, "Count")


def load_model():
    start_time = time.time()
    model_path = os.path.join(os.path.dirname(__file__), "data/model.joblib.gz", )
    model = joblib.load(model_path)

    duration_seconds = time.time() - start_time
    Boto3Metrics.put_duration("load_model.duration", duration_seconds)

    return model


# EmfMetrics.setup()
model = load_model()


def lambda_handler(event, context):
    request_body = json.loads(event["body"])
    prediction = str(model.predict([request_body["text"]])[0])

    Boto3Metrics.put_count("input.num_chars", len(request_body["text"]))

    return {
        "statusCode": 200,
        "body": json.dumps({
            "response": prediction,
            "request": request_body
        })
    }
