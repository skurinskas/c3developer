/*
 * Copyright 2009-2016 C3 IoT (http://www.c3iot.com).  All Rights Reserved.
 * This material, including without limitation any software, is the confidential trade secret
 * and proprietary information of C3 IoT and its licensors.  Reproduction, use and distribution
 * of this material in any form is strictly prohibited except as set forth in a written
 * license agreement with C3 IoT and/or its authorized distributors.
 *
 * @author Scott
 */

var log = C3.logger("FailureAlert");

function process(input) {
  var alertType, f;

  log.info("stringify " + JSON.stringify(input));
  
  // if the hard drive has failed, update the status and failureDate fields to indicate
  // that a failure has occurred.
  if (input.fail.data().at(0) > 0) {
    var fa = FixedAsset.make({
     id: input.source.id,
     status: "Failed",
     failureDate: input.start
    })

    FixedAsset.merge(fa);
  }
}


//@ sourceURL=AssetFailureAlert.js