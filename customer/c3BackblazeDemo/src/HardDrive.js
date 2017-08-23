var log = C3.logger("backblaze");

function afterCreate(objs) {
    log.info("afterCreate___afterCreate");
    log.info(JSON.stringify(objs));
}
