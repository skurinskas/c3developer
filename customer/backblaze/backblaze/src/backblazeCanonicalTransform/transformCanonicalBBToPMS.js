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

	var pmsAry = [];
	var resp = [];
	var name;
	var goodNames = ColumnToMetricMapping.fetch();

	var assetId = hdMeasurements.serial_number;
	var fields = hdMeasurements.fields();

	fields.forEach(function (f) {

		if (f.name.includes("smart") || f.name.includes("failure") || f.name.includes("bytes")) {
			name = goodNames.objs.filter(function (d) {
	    		return d.id === f.name;
			})[0].name;

			var id = assetId + "_" + name;
			var pms = PhysicalMeasurementSeries.make({
				id: id,
				name: name,
				asset: {id : assetId},
				measurementType: name,
				treatment: "rate",
				unitConstraint: {id: "dimensionless"}
			});

			pmsAry.push(pms);
		}
	})

	return pmsAry;
  
}

//# sourceURL=transformCanonicalBBToPMS.js

