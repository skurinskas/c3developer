/*
 * Copyright 2009-2016 C3 IoT (http://www.c3iot.com). All Rights Reserved.
 * This material, including without limitation any software, is the confidential trade secret
 * and proprietary information of C3 IoT and its licensors. Reproduction, use and distribution
 * of this material in any form is strictly prohibited except as set forth in a written
 * license agreement with C3 IoT and/or its authorized distributors.
 */
/*
 * @author: Scott Kurinskas
 */

c3Import('metadata');
var log = C3.logger("backblaze");

function transform(hdMeasurements) {

	var measAry = [];
	var name;
	var goodNames = ColumnToMetricMapping.fetch();

	log.info("datevalue = " + hdMeasurements.date);

	var assetId = hdMeasurements.serial_number;
	var startDate = new Date(hdMeasurements.date);
	var endDate = new Date(startDate).addDays(1);
	var fields = hdMeasurements.fields();

	log.info("startDate = " + startDate.serialize());
	log.info("endDate = " + endDate.serialize());

	fields.forEach(function (f) {
		
		if (f.name.includes("smart") || f.name.includes("failure") || f.name.includes("bytes")) {
			name = goodNames.objs.filter(function (d) {
	    		return d.id === f.name;
			})[0].name;

			var parentId = assetId + "_" + name;
			var meas = Measurement.make({
				parent: parentId,
				start: startDate,
				end: endDate,
				quantity: { value: hdMeasurements[f.name]}
			});

			measAry.push(meas);
		}
	})

	return measAry;
  
}

function parseDate(dateTime){
  if (dateTime) {
    var dt = dateTime.split(/\/| |:/);
    return new Date(dt[2], dt[0]-1, dt[1]);
  } else {
    return undefined;
  }
}

//# sourceURL=transformCanonicalBBToMeasurement.js
