/*
 * Copyright 2009-2016 C3 IoT (http://www.c3iot.com). All Rights Reserved.
 * This material, including without limitation any software, is the confidential trade secret
 * and proprietary information of C3 IoT and its licensors. Reproduction, use and distribution
 * of this material in any form is strictly prohibited except as set forth in a written
 * license agreement with C3 IoT and/or its authorized distributors.
 */
/**
 * @author Scott Kurinskas
 */

c3Import("metadata", "metric");

var logger = C3.logger("skurinsk.RefreshAnalytics");

/*
 * MapReduce job to refresh the failure status for fixed assets.  This only should be run
 * after the initial load is complete
 */
function map(batch, objs, job) {

  var start = "2014-04-01";
  var end = "2016-07-01";
  var analytic = "AssetFailureAlert";

  objs.each(function (fa) {

    AnalyticsContainer.fireAnalytics(
        [{
          typeId:  Tag.getTypeId('structure','FixedAsset'),
          objId: fa.id,
          timeRanges: [{start: start, end: end}],
          metricGroup: analytic
        }],
        [],
        {forceReEval: true,ignoreThreshold:true}
    );

  })
  
}