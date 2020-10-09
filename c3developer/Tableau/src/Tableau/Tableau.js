
function flatten_eval_metrics (metrics, filter, start, end, interval, typeName, limit) {
  
  var results = Tableau.gen_metrics_table_as_json(metrics, filter, start, end, interval, typeName, limit);

  return {"result": JSON.parse(results)};

}