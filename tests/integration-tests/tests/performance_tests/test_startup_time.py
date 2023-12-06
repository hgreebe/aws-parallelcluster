import logging
import statistics
from datetime import datetime

import boto3
import pytest
from dateutil.relativedelta import relativedelta
from utils import describe_cluster_instances

MINIMUM_DATASET_SIZE = 5

BASELINE = {"alinux2": {"c5.large": [92, 86, 70, 102, 104],
                        "m5.12xlarge": [101, 89, 100, 87, 70],
                        "g4dn.xlarge": [111, 103, 92, 121, 122]}}


def evaluate_data(value, data):
    standard_deviation = statistics.stdev(data)
    mean = statistics.mean(data)
    logging.info(f"Mean: {mean}")
    logging.info(f"Standard deviation: {standard_deviation}")

    distance = abs(mean - value) / standard_deviation
    if value < (mean + 2 * standard_deviation) or value > (mean - 2 * standard_deviation):
        return False, distance
    return True, distance


def get_data(instance_type, os, cw_client):
    data = []
    dimensions = [{"Name": "InstanceType", "Value": instance_type}, {"Name": "OS", "Value": os}]

    cluster_metrics = cw_client.list_metrics(
        Namespace="ParallelCluster", MetricName="StartupTime", Dimensions=dimensions
    )

    logging.info(f"Metrics: {cluster_metrics}")

    for metric in cluster_metrics["Metrics"]:
        result = cw_client.get_metric_statistics(
            Namespace="ParallelCluster",
            MetricName="StartupTime",
            Dimensions=metric["Dimensions"],
            StartTime=datetime.now() - relativedelta(years=1),
            EndTime=datetime.now(),
            Period=30000,
            Statistics=["Average"],
            Unit="None",
        )

        logging.info(f"Results: {result}")

        if result["Datapoints"]:
            value = result["Datapoints"][0].get("Average")
            data.append(value)
    return data


def get_metric(os, cluster, instance_type, instance_id, cw_client):
    startup_time_value = None

    dimensions = [
        {"Name": "OS", "Value": os},
        {"Name": "InstanceID", "Value": instance_id},
        {"Name": "ClusterName", "Value": cluster.name},
        {"Name": "InstanceType", "Value": instance_type},
    ]

    result = cw_client.get_metric_statistics(
        Namespace="ParallelCluster",
        MetricName="StartupTime",
        Dimensions=dimensions,
        StartTime=datetime.now() - relativedelta(years=1),
        EndTime=datetime.now(),
        Period=30000,
        Statistics=["Average"],
        Unit="None",
    )

    logging.info(f"Results: {result}")

    if result["Datapoints"]:
        startup_time_value = result["Datapoints"][0].get("Average")
    return startup_time_value


def test_startup_time(pcluster_config_reader, clusters_factory, test_datadir, region, instance, os, scheduler):
    cluster_config = pcluster_config_reader()
    cluster = clusters_factory(cluster_config)

    cw_client = boto3.client("cloudwatch", region_name=region)

    instances = describe_cluster_instances(
        cluster.name,
        region,
        filter_by_node_type="Compute",
    )

    performance_degradation = {}

    for instance in instances:
        instance_type = instance["InstanceType"]
        instance_id = instance["InstanceId"]
        logging.info(f"Type: {instance_type}")

        startup_time_value = get_metric(os, cluster, instance_type, instance_id, cw_client)
        logging.info(f"Observed Startup Time for instance ${instance_id} (${instance_type}) of cluster ${cluster.name}: ${startup_time_value} seconds")

        # get historical data
        #data = get_data(instance_type, os, cw_client)
        #if startup_time_value in data:
        #    data.remove(startup_time_value)

        #logging.info(f"Data of {instance_type}: {data}")

        # evaluate data
        #if len(data) > MINIMUM_DATASET_SIZE and startup_time_value:
        #    degradation, dist = evaluate_data(startup_time_value, data)
        #    if degradation:
        #        performance_degradation[instance_type] = dist

    #if performance_degradation:
        #message = "Performance test results show performance degradation for the following instances: "
        #for instance in performance_degradation.keys():
        #    message += f"{instance} ({performance_degradation[instance]} standard deviations from the mean), "
        #pytest.fail(message[:-2])
    #else:
        #logging.info("Performance test results show no performance degradation")
