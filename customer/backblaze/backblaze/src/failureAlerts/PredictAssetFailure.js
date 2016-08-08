/*
 * Copyright 2009-2016 C3 IoT (http://www.c3iot.com).  All Rights Reserved.
 * This material, including without limitation any software, is the confidential trade secret
 * and proprietary information of C3 IoT and its licensors.  Reproduction, use and distribution
 * of this material in any form is strictly prohibited except as set forth in a written
 * license agreement with C3 IoT and/or its authorized distributors.
 *
 * @author Scott
 */

c3Import("tbd_machineLearning")
var log = C3.logger("skurinsk.PredictAssetFailure");


function loadContextAll() {
    var fres = HardDriveFailureClassifier.fetch({
        order:"descending(meta.updated)",
        limit:1
    });

    if (fres.count == 0) {
        throw new Error("No Hard Drive Model found");
    }

    return fres.objs.at(0);
}

function processSource(asset, inputs, context) {
    log.info("Processing asset="+asset.id);
    log.info(JSON.stringify(inputs));


    var input = inputs.at(inputs.size() - 1);
    var start = input.start,
        end = input.end;

    var extract = extractDataFromDFE(inputs);
    var dataset = extract.dataset
    var dates = extract.dates

    // Prediction using DS model
    var predictionDataset = context.predict(dataset);
    var predictionData = predictionDataset.extractColumns(["1.0"]).data;

    upsertPredictionResults(asset, dates, predictionData)

}

function upsertPredictionResults(asset, dates, predictionData){
    var header = HardDriveFailureScoreHistory.merge({
        id: asset.id
    })
    
    var scores = HardDriveFailureScore.array()
    _.each(_.zip(dates, predictionData), function (pair, i) {
        var inputTimestamp = pair[0];
        var prediction = pair[1];
        scores.push( 
            HardDriveFailureScore.make({
                parent: header,
                start: inputTimestamp,
                value: prediction
            })
        );
    });

    HardDriveFailureScore.upsertBatch(scores);
}

function extractDataFromDFE(inputs) {
    var data = Double.array();
    var index = Str.array();
    var inputDFEFieldTypes = getInputDFEFieldTypes();
    var expressions = getExpressions(inputDFEFieldTypes);

    // Initialize length and dates
    var dates = getDates(inputs, inputDFEFieldTypes);

    // Conversion of dates to index and data to dataset
    dates.each(function (date, i) {
        index.push(date.serialize())
    })


    inputs.each(function (input) {
    
        _.map(inputDFEFieldTypes, function (fieldType) {
            var fieldName = fieldType.fieldName();
            
            data = data.concat(input[fieldName].data());
        })
    })

    return {
        dataset : TBD_MachineLearningDataSet.make({
            columns: expressions,
            data: data,
            index: index,
            orient: "column" }),
        dates : dates }

}

function getDates(inputs, inputDFEFieldTypes){
    var n;
    var dates = DateTime.array();

    inputs.each(function(input) {
      if (n !== undefined) {
        return;
      }
      var dfe;
      _.each(inputDFEFieldTypes, function(fieldType) {
        if (dfe !== undefined) {
          return;
        }

        var fieldName = fieldType.fieldName();
        if (input[fieldName]) {
          dfe = input[fieldName];
        }
      });

      if (dfe && dfe.data().length) {
        n = dfe.data().length;
        dates = dfe.dates();
      }
    });

    return dates;
} 
    

function getInputDFEFieldTypes() {
    return _.filter(PredictAssetFailureInput.fieldTypes(), function (fieldType) {
      var valueType = fieldType.valueType();
      if (valueType.isReference()) {
        var type = valueType.dereference();
        return type.isA(DataFlowEvent);
      } else {
        return false;
      }
    });
}


function getExpressions(inputDFEFieldTypes) {
    return inputDFEFieldTypes.map(function (fieldType) {
      return fieldType.valueType().dereference().extensions().DFE.metric;
    });
}


//@ sourceURL=PredictAssetFailure.js
