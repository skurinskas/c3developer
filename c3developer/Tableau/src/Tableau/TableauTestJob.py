import sys
import logging
import datetime
from datetime import timedelta
import tableauhyperapi
import tableauserverclient as TSC
from pathlib import Path
from tableauhyperapi import HyperProcess, Telemetry, \
    Connection, CreateMode, \
    NOT_NULLABLE, NULLABLE, SqlType, TableDefinition, \
    Inserter, \
    escape_name, escape_string_literal, \
    TableName, \
    HyperException

from urllib.parse import urlparse, urlunparse
from pathlib import PosixPath
import json

logger = logging.getLogger('c3.tableau')
logger.setLevel(logging.INFO)

def eval_metrics(metrics, ids, start, end, interval):
  collection = []
  row = []
  num_metrics = len(metrics)
  spec1 = c3.EvalMetricsSpec(
    ids = ids,
    expressions = metrics,
    start = start,
    end = end,
    interval = interval
  )

  data_len = 0
  result1 = c3.SmartBulb.evalMetrics(spec=spec1).toJson()
  source_ids = list(result1['result'].keys())

  try:
    data_len = len(result1['result'][source_ids[0]][metrics[0]]['m_data'])
  except KeyError:
    data_len = 0

  for id in source_ids:
      start = datetime.datetime.strptime(result1['result'][id][metrics[0]]['m_start'], '%Y-%m-%dT%H:%M:%S')
      
      data_count=0
      while data_count < data_len:
          row.append(id)
          row.append(start)
          met_count = 0
          while met_count < num_metrics:
              row.append(result1['result'][id][metrics[met_count]]['m_data'][data_count])
              met_count += 1  
          
          data_count += 1
          start = start + + timedelta(days=1)
          collection.append(row.copy())
          row.clear()

  return collection

def get_table_def():
  table = TableDefinition(
    table_name=TableName("Extract", "Metric"),
    columns=[
        TableDefinition.Column(name='id', type=SqlType.text(), nullability=NOT_NULLABLE),
        TableDefinition.Column(name='start', type=SqlType.date(), nullability=NOT_NULLABLE),
        TableDefinition.Column(name='AverageTemperature', type=SqlType.double()),
        TableDefinition.Column(name='AverageLumens', type=SqlType.double()),
    ]
  )

  return table

def create_hyperfile(file_name, tableau_table_def, table_name):
  path_to_database = Path(file_name)
  
  try: 
    path_to_database.unlink()
  except FileNotFoundError:
    logger.info("file does not exist")

  # Optional process parameters.
  process_parameters = {
      "log_dir": "/tmp/"
  }

  with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU, parameters=process_parameters) as hyper:

      # Creates new Hyper file "customer.hyper".
      # Replaces file with CreateMode.CREATE_AND_REPLACE if it already exists.
      with Connection(endpoint=hyper.endpoint,
                      database=path_to_database,
                      create_mode=CreateMode.CREATE_IF_NOT_EXISTS) as connection:

          connection.catalog.create_schema(schema=tableau_table_def.table_name.schema_name)
          connection.catalog.create_table(table_definition=tableau_table_def)

def run_insert_data_into_single_table(file_name, tableau_table_def, table_name, data):
  path_to_database = Path(file_name)

  # Optional process parameters.
  process_parameters = {
      "log_dir": "/tmp/"
  }

  with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU, parameters=process_parameters) as hyper:
      with Connection(endpoint=hyper.endpoint,
                      database=path_to_database,
                      create_mode=CreateMode.NONE) as connection:

          with Inserter(connection, tableau_table_def) as inserter:
              inserter.add_rows(rows=data)
              inserter.execute()


def publish_hyperfile_to_server(file_name):

  # Step 1: Sign in to server.
  tableau_auth = TSC.TableauAuth("mohit.mahendra@c3.ai", "C3enterpriseAI", "c3ai")
  server = TSC.Server("https://us-west-2b.online.tableau.com/")
  path_to_database = Path(file_name)

  overwrite_true = TSC.Server.PublishMode.Overwrite
  
  with server.auth.sign_in(tableau_auth):
      all_workbooks_items, pagination_item = server.workbooks.get()

      # Step 2: Get all the projects on server, then look for the default one.
      all_projects, pagination_item = server.projects.get()
      default_project = next((project for project in all_projects if project.is_default()), None)

       # Step 3: If default project is found, form a new workbook item and publish.
      if default_project is not None:
          new_datasource = TSC.DatasourceItem(default_project.id)
          print(new_datasource.id)

          new_datasource = server.datasources.publish(new_datasource, path_to_database, 'Overwrite')

          print("Workbook published. ID: {0}".format(new_datasource))
      else:
          error = "The default project could not be found."
          raise LookupError(error)

def doStart(job, options):
  logger.info("Creating hyperfile")
  table_def = get_table_def()
  create_hyperfile("/tmp/metric_result.hyper", table_def,  "Extract.Metric")

  logger.info("fetching bulbs and submitting jobs")
  bulbs = c3.SmartBulb.fetch(c3.FetchSpec(limit=-1))
  for bulb in bulbs.objs:
    newjob = c3.TableauTestJobBatch(batchContext = bulb.id)
    c3.TableauTestJob.scheduleBatch(job, newjob )

def processBatch(batch, job, options):
  metrics = ["AverageTemperature", "AverageLumens"]
  ids = [batch.batchContext]

  logger.info("inProcessBatch")
  str1 = ''.join(ids)
  logger.info(str1)

  metric_result = eval_metrics(metrics, ids, "2012-01-01", "2012-01-10", "DAY")
  table_def = get_table_def()
  run_insert_data_into_single_table("/tmp/metric_result.hyper", table_def,  "Extract.Metric", metric_result)

