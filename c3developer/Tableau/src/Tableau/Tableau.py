import tableauhyperapi
import logging
import datetime
import json
from datetime import timedelta
from pathlib import Path
import tableauserverclient as TSC
from tableauhyperapi import HyperProcess, Telemetry, \
  Connection, CreateMode, \
  NOT_NULLABLE, NULLABLE, SqlType, TableDefinition, \
  Inserter, \
  escape_name, escape_string_literal, \
  TableName, \
  HyperException

logger = logging.getLogger('c3.tableau')
logger.setLevel(logging.INFO)


def datetime_converter(dt):
    if isinstance(dt, datetime.datetime):
        return dt.__str__()

def get_metric_results_as_collection(metrics, ids, start, end, interval, typeName):
    collection = []
    row = []
    met_list = list(metrics)
    num_metrics = len(met_list)
    
    typ = c3.__getattr__(typeName)
  
    spec1 = c3.EvalMetricsSpec(
        ids = ids,
        expressions = met_list,
        start = start,
        end = end,
        interval = interval
    )

    data_len = 0
    result1 = typ.evalMetrics(spec=spec1)        
    source_ids = list(result1.result.keys())
    
    try:
        data_len = len(result1.result[source_ids[0]][metrics[0]].data())
    except KeyError:
        data_len = 0

    for id in source_ids:
        start = result1.result[id][metrics[0]].m_start
        
        data_count=0
        while data_count < data_len:
            row.append(id)
            row.append(datetime_converter(start))
            met_count = 0
            while met_count < num_metrics:
                try:
                    row.append(result1.result[id][metrics[met_count]].data()[data_count])
                    met_count += 1  
                except KeyError:
                    row.append(0)
                    met_count += 1

            data_count += 1
            start = start + timedelta(days=1)
            collection.append(row.copy())
            row.clear()

    return collection

# Creates a hyper file in the local file system.  If the file exists it will be deleted.
def create_hyperfile(file_name, table_def, create_mode):
    path_to_database = Path(file_name)
    config = c3.Tableau.inst().getConfig();
    log_dir = config.log_dir

    if (create_mode == 0):
        tabl_create_mode = CreateMode.NONE
    elif (create_mode == 1):
        tabl_create_mode = CreateMode.CREATE
    elif (create_mode == 2):
        tabl_create_mode = CreateMode.CREATE_IF_NOT_EXISTS
    elif (create_mode == 3):
        tabl_create_mode = CreateMode.CREATE_AND_REPLACE
    else:
        raise Exception("Invalid CreateMode value.  Specify a value between 0 and 3")

    try: 
        path_to_database.unlink()
    except FileNotFoundError:
        logger.info("file does not exist")

    # Optional process parameters.
    process_parameters = {
        "log_dir": log_dir
    }

    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU, parameters=process_parameters) as hyper:

        with Connection(endpoint=hyper.endpoint,
                  database=path_to_database,
                  create_mode=tabl_create_mode) as connection:

            connection.catalog.create_schema(schema=table_def.table_name.schema_name)
            connection.catalog.create_table(table_definition=table_def)


# Inserts data into an existing hyper file.
# Inserts data into an existing hyper file.
def run_insert_data_into_single_table(file_name, data, table_def):
    path_to_database = Path(file_name)

    config = c3.Tableau.inst().getConfig();
    log_dir = config.log_dir

    # Optional process parameters.
    process_parameters = {
        "log_dir": log_dir
    }

    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU, parameters=process_parameters) as hyper:

        with Connection(endpoint=hyper.endpoint,
                    database=path_to_database,
                    create_mode=CreateMode.NONE) as connection:

            with Inserter(connection, table_def) as inserter:
                inserter.add_rows(rows=data)
                inserter.execute()

# publish hyper file to Tableau server
def publish_hyperfile_to_server(file_name):

    config = c3.Tableau.inst().getConfig();
    user_name = config.user_name
    site_id =  config.site_id
    server_url = config.server_url
    pwd = config.secretValue("password")

    # Step 1: Sign in to server.
    tableau_auth = TSC.TableauAuth(user_name, pwd, site_id)
    server = TSC.Server(server_url)

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
            new_datasource = server.datasources.publish(new_datasource, path_to_database, 'Overwrite')

            print("Workbook published. ID: {0}".format(new_datasource))
        else:
            error = "The default project could not be found."
            raise LookupError(error)


def get_metric_table_def(table_name, fields):

     columns = []
     columns.append(TableDefinition.Column(name='id', type=SqlType.text(), nullability=NOT_NULLABLE))
     columns.append(TableDefinition.Column(name='start', type=SqlType.text(), nullability=NOT_NULLABLE))

     for field in fields:
          columns.append(TableDefinition.Column(name=field, type=SqlType.double()))

     table = TableDefinition(
          table_name=TableName("Extract", table_name),
          columns=columns
     )

     return table

# Create metrics table file
# Generates the hyper file for a list of sources and metrics
# limit - number of rows to fetch in an individual request.  intended to be smallish
# num_sources - total number of rows to fetch
def gen_metrics_table(metrics, filter, start, end, interval, typeName, limit, num_sources, table_name, file_name, create_mode):
  
    ids = []
    has_more = True
    offset = 0
    met_list = list(metrics)
    num_metrics = len(met_list)
    include = "id"
    typ = c3.__getattr__(typeName)
    
    if (limit < 1 or num_sources < 1):
        raise Exception("limit and num_sources must be greater than or equal to 1")
    
    # Get table definition
    table_def = get_metric_table_def(table_name, metrics)

    # Create hyper file for the metrics table
    create_hyperfile(file_name, table_def, create_mode)
    
    while (has_more == True):
        
        if(offset == 0 and num_sources <= limit):
            limit = num_sources
        
        spec = c3.FetchSpec(filter=filter, include=include, limit=limit, offset=offset)
        results = typ.fetch(spec)
            
        for result in results.objs:
            ids.append(result.id)
    
        # get metric results for ids
        data = get_metric_results_as_collection(metrics, ids, start, end, interval, typeName)
                
        # Insert data into table
        run_insert_data_into_single_table(file_name, data, table_def)
                
        offset = offset + limit
        
        if (offset < num_sources):
            ids.clear()
            has_more = results.hasMore
        else:
            ids.clear()
            has_more = False


# fields are a json document of the following structure
# [{"fieldName": "value", "dataType: "sqlType", "nullable": true}]
def get_type_table_def(table_name, fields):

    columns = []
    json_field = json.dumps(fields)
    
    for field in fields:
        if (field['dataType'] == 'string'):
            fieldType = SqlType.text()
        elif (field['dataType'] == 'int'):
            fieldType = SqlType.int()
        elif (field['dataType'] == 'datetime'):
            fieldType = SqlType.date()
        elif (field['dataType'] == 'boolean'):
            fieldType = SqlType.bool()
        elif (field['dataType'] == 'double'):
            fieldType = SqlType.double()
        else:
            fieldType = SqlType.text()
            
        if (field['nullable'] == True):
            fieldNullable = NULLABLE
        else:
            fieldNullable = NOT_NULLABLE
            
        columns.append(TableDefinition.Column(name=field['fieldName'], type=fieldType, nullability=fieldNullable))
        

    table = TableDefinition(
        table_name=TableName("Extract", table_name),
        columns=columns
    )

    return table

# Flattens metric results from a map to a table
# Flattens metric results from a map to a table
def gen_fetch_table(fields, filter, typeName, limit, num_sources, table_name, file_name, create_mode):
  
    has_more = True
    offset = 0
    include = ""
    num_fields = len(fields)
    i = 0
    collection = []
    row = []
    
    # use fields to create include spec
    while (i < num_fields):
        include = include + fields[i]['fieldName'] + ","
        i += 1
    
    typ = c3.__getattr__(typeName)

    # Get table definition
    table_def = get_type_table_def(table_name, fields)

    # Create hyper file for the metrics table
    create_hyperfile(file_name, table_def, create_mode)

    # fetch data and generate file.  Supports reference fields (1 level)
    while (has_more == True):
        
        if(offset == 0 and num_sources <= limit):
            limit = num_sources
            
        spec = c3.FetchSpec(include=include, filter=filter, offset=offset, limit=limit)
        results = typ.fetch(spec)
    
        for result in results.objs:
            for field in fields:
                # limited reference field support.  one level of depth.
                x = field['fieldName'].split(".")
                if (len(x) > 1):
                    y = getattr(result, x[0])
                    z = getattr(y, x[1])

                    if (isinstance(z, datetime.datetime)):
                        row.append(z.strftime("%Y-%m-%d %H:%M:%S"))
                    else:
                        row.append(z)
                else:
                    if (isinstance( getattr(result, field['fieldName']), datetime.datetime)):
                        row.append(getattr(result, field['fieldName']).strftime("%Y-%m-%d %H:%M:%S"))
                    else:
                        row.append(getattr(result, field['fieldName']))
 
            collection.append(row.copy())
            row.clear()
        
        offset = offset + limit
        
        if (offset < num_sources):
            has_more = results.hasMore
        else:
            has_more = False

    # Insert data into table
    run_insert_data_into_single_table(file_name, collection, table_def)