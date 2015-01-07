// Generated by CoffeeScript 1.6.1
(function() {
  var ALLOWED_METHODS, ALLOWED_METHODS_STR, PATTERNS, commonHeaders, config, createFile, events, fs, getFile, headFile, http, httpStatus, initApp, optionsFile, patchFile, path, route, setup, setupLogger, startup, testUploadPage, tusHandler, upload, url, util, uuid, winston,
    __indexOf = [].indexOf || function(item) { for (var i = 0, l = this.length; i < l; i++) { if (i in this && this[i] === item) return i; } return -1; };
    http = require("http");
    url = require("url");
    fs = require("fs");
    path = require("path");
    util = require("util");
    events = require("events");
    uuid = require("node-uuid");
    winston = require("winston");
    request = require("request");
    upload = require("./upload");
    Config = require( "konphyg" )( __dirname );
    sys = require( "sys" );
    Mixpanel = require( "mixpanel" );
    formidable = require( "formidable" );
    useragent = require( "useragent" );

    setup = new events.EventEmitter();

    config = {};

    var mixpanel;  // set in initApp

    function getTech( req ) {
	var ua = useragent.parse( req.headers[ 'user-agent' ] );
	var device = ua.device.toString();
	var os = ua.os.toString();
	if ( device == 'Other' ) device = ua.family;
	if ( ua.source.match( /^Viblio/ ) ) {
	    device = 'ViblioApp';
	    os = ua.source;
	}
	return device + ' ' + os;
    }

    // Custom Transport so we can log into syslog, so it goes to loggly
    var SysLogger = winston.transports.SysLogger = function( options ) {
	this.name  = 'sysLogger';
	this.ident = options.app_name;
	this.level = options.level;
	this.Syslog = require('node-syslog');
	this.Syslog.init(this.ident, this.Syslog.LOG_NDELAY, this.Syslog.LOG_LOCAL0);
    };

    util.inherits( SysLogger, winston.Transport );

    SysLogger.prototype.log = function( level, msg, meta, callback ) {
	var lvl = 'log_' + level;
	if ( lvl == 'log_error' ) lvl = 'log_err';
	this.Syslog.log( this.Syslog[lvl.toUpperCase()], msg + ' ' + JSON.stringify( meta ) );
	callback( null, true );
    };
    ////////////////////////////////////////////////////////////////////

    testUploadPage = function(res) {
	return fs.readFile(path.join(__dirname, "/up.html"), "utf8", function(err, data) {
	    res.setHeader("Content-Type", "text/html");
	    if (!err) {
		return httpStatus(res, 200, "Ok", data);
	    }
	    winston.error(util.inspect(err));
	    return httpStatus(res, 405, "Not Allowed");
	});
    };

    optionsFile = function(req, res, query, matches) {
	return httpStatus(res, 200, "Ok");
    };

    getFile = function(req, res, query, matches) {
	var fileId, status, u;
	fileId = matches[2];
	if (fileId == null) {
	    return httpStatus(res, 404, "Not Found");
	}
	u = upload.Upload(config, fileId);
	status = u.load();
	if (status.error != null) {
	    return httpStatus(res, status.error[0], status.error[1]);
	}
	res.setHeader("Content-Length", status.info.finalLength);
	return u.stream().pipe(res);
    };

    deleteFile = function(req, res, query, matches) {
	fileId = matches[2];
	if (fileId == null) {
	    return httpStatus(res, 404, "Not Found");
	}
	winston.debug( 'Cancel upload ' + fileId );
	filePath = path.join(config.files, fileId);
	if (!fs.existsSync(filePath)) {
	    return httpStatus(res, 404, "Not Found");
	}
	infoPath = filePath + '.json';
	mdPath   = filePath + '_metadata.json';
	fs.unlinkSync( filePath );
	if ( fs.existsSync( infoPath ) ) 
	    fs.unlinkSync( infoPath );
	if ( fs.existsSync( mdPath ) ) 
	    fs.unlinkSync( mdPath );
	return httpStatus(res, 200, "Ok");
    };

    createFile = function(req, res, query, matches) {
	var fileId, fileExt, finalLength, status;
	fileId = matches[2];
	if (fileId != null) {
	    return httpStatus(res, 400, "Invalid Request");
	}
	if (req.headers["final-length"] == null) {
	    return httpStatus(res, 400, "Final-Length Required");
	}
	finalLength = parseInt(req.headers["final-length"]);
	if (isNaN(finalLength || finalLength < 0)) {
	    return httpStatus(res, 400, "Final-Length Must be Non-Negative");
	}
	fileId = uuid.v1();
	fileExt = '';

	// Capture the post body
	var body='';
	req.on( 'data', function( data ) {
	    body += data;
	});
	req.on( 'end', function() {
	    var uid='unknown';
	    if ( body != '' ) {
		try {
		    var metadata = JSON.parse( body );
		    uid = metadata['uuid'];
		    delete metadata['uuid'];

		    // Store the skip_faces directive, if any, in the
		    // metadata file.  Popeye will look to this file
		    // to set the value of skip_faces for the video
		    // processing pipeline.
		    if ( metadata['skip_faces'] ) {
			winston.info( "SKIP FACES IS TRUE" );
			metadata['skip_faces'] = true;
		    } else {
			winston.info( "SKIP FACES IS FALSE" );
			metadata['skip_faces'] = false;
		    }
		    
		    // Store the try_photos directive, if any, in the
		    // metadata file.  Popeye will look to this file
		    // to set the value of try_photos for the video
		    // processing pipeline.
		    if ( metadata['try_photos'] ) {
			if ( metadata['try_photos'] == 2 ) {
			    metadata['try_photos'] = 2;
			} else {
			    metadata['try_photos'] = 1;
			}
			winston.info( "TRY PHOTOS IS TRUE: " + metadata['try_photos'] );
		    } else {
			winston.info( "TRY PHOTOS IS FALSE" );
			metadata['try_photos'] = false;
		    }
		    
		    // Hopefully the original filename is in the
		    // metadata.  Use that to capture the file extension
		    var path = require( "path" );
		    if ( metadata['file'] && metadata['file']['Path'] ) {
			fileExt = path.extname( metadata['file']['Path'] );
		    }

		    body = JSON.stringify( metadata );
		} catch(e) {
		    winston.error( 'Failed to parse CREATE body: ' + util.inspect(e) );
		}
	    }
	    status = upload.Upload(config, fileId, uid, fileExt).create(finalLength, body);
	    var meta = {
		method: 'POST',
		fileId: fileId,
		uid: uid
	    };
	    if (status.error != null) {
		return httpStatus(res, status.error[0], status.error[1], null, meta);
	    }
	    mixpanel.track( 'upload_started', {
		distinct_id: meta.fileId,
		media_uuid: meta.fileId,
		user_uuid: meta.uid,
		activity: 'brewtus',
		tech: getTech( req ),
		deployment: process.env.NODE_ENV || 'local'
	    });
	    var proto = 'http';
	    if ( req.headers.port && req.headers.port == 443 )
		proto = 'https';
	    if ( config.force_https ) 
		proto = 'https';
	    res.setHeader("Location", proto + "://" + req.headers.host + "/files/" + fileId);
	    return httpStatus(res, 201, "Created", null, meta);
	});
    };

    headFile = function(req, res, query, matches) {
	var fileId, info, status;
	fileId = matches[2];
	if (fileId == null) {
	    return httpStatus(res, 404, "Not Found");
	}
	status = upload.Upload(config, fileId).load();
	if (status.error != null) {
	    winston.debug( "In HEAD: error" + status.error[1] );
	    return httpStatus(res, status.error[0], status.error[1]);
	}
	info = status.info;
	// winston.debug( "HEAD: info: " + util.inspect(info) );
	res.setHeader("Offset", info.offset);
	res.setHeader("Connection", "close");
	return httpStatus(res, 200, "Ok", null, { method: 'HEAD', fileId: fileId, uid: info.uid });
    };

    patchFile = function(req, res, query, matches) {
	var contentLength, fileId, filePath, info, offsetIn, status, u, ws;
	fileId = matches[2];
	if (fileId == null) {
	    return httpStatus(res, 404, "Not Found");
	}
	filePath = path.join(config.files, fileId);
	if (!fs.existsSync(filePath)) {
	    return httpStatus(res, 404, "Not Found");
	}
	if (req.headers["content-type"] == null) {
	    return httpStatus(res, 400, "Content-Type Required");
	}
	if (! (req.headers["content-type"].match( /application\/offset\+octet-stream/ ) ||
	       req.headers["content-type"].match( /multipart/ ) ) ) {
	    return httpStatus(res, 400, "Content-Type Invalid");
	}
	if (req.headers["offset"] == null) {
	    return httpStatus(res, 400, "Offset Required");
	}
	offsetIn = parseInt(req.headers["offset"]);
	if (isNaN(offsetIn || offsetIn < 0)) {
	    return httpStatus(res, 400, "Offset Invalid");
	}
	if (req.headers["content-length"] == null) {
	    return httpStatus(res, 400, "Content-Length Required");
	}
	contentLength = parseInt(req.headers["content-length"]);
	if (isNaN(contentLength || contentLength < 1)) {
	    return httpStatus(res, 400, "Invalid Content-Length");
	}
	u = upload.Upload(config, fileId);
	status = u.load();

	var meta = {
	    method: 'PATCH',
	    fileId: fileId,
	    uid: status.info.uid };

	if (status.error != null) {
	    return httpStatus(res, status.error[0], status.error[1], null, meta);
	}
	info = status.info;
	if (offsetIn > info.offset) {
	    return httpStatus(res, 400, "Invalid Offset", null, meta);
	}
	ws = fs.createWriteStream(filePath, {
	    flags: "r+",
	    start: offsetIn
	});
	if (ws == null) {
	    winston.error("unable to create file " + filePath);
	    return httpStatus(res, 500, "File Error", null, meta);
	}
	info.offset = offsetIn;
	info.state = "patched";
	info.patchedOn = Date.now();
	info.bytesReceived = 0;

	if ( req.headers["content-type"].match( /multipart/ ) ) {
	    // F'in IE again!!!
	    var form = new formidable.IncomingForm();
	    form.onPart = function(part) {
		part.addListener('data', function( buffer ) {
		    info.bytesReceived += buffer.length;
		    info.offset += buffer.length;
		    if (info.offset > info.finalLength) {
			return httpStatus(res, 500, "Exceeded Final-Length", null, meta);
		    }
		    if (info.received > contentLength) {
			return httpStatus(res, 500, "Exceeded Content-Length", null, meta);
		    }
		    // Do the write HERE
		    ws.write(buffer);
		});
		part.addListener('end', function() {
		    winston.debug( "Request end: bytes received=" +  info.offset );
		    if (!res.headersSent) {
			// httpStatus(res, 200, "Ok", JSON.stringify(info));
			httpStatus(res, 200, "Ok", null, meta);
		    }
		    return u.save( function() {
			mixpanel.track( 'upload_completed', {
			    distinct_id: info.fileId,
			    media_uuid: info.fileId,
			    user_uuid: info.uid,
			    activity: 'brewtus',
			    tech: getTech( req ),
			    deployment: process.env.NODE_ENV || 'local'
			});
			if ( config.popeye != "none" ) {
			    winston.info("\npcol popeye: " + config.popeye + "?path=" + filePath + "\n" );
			    request( {url: config.popeye, qs: { path: filePath, skip_faces: info.skip_faces, try_photos: info.try_photos } }, function( err, res, body ) {
				if ( err ) {
				    winston.error( "Popeye error: " + err.message );
				}
				else if ( res.statusCode != 200 ) {
				    winston.error( "Popeye error: " + res.statusCode );
				}
				else {
				    try {
					var r = JSON.parse( body );
					if ( r.error ) {
					    winston.error( "Popeye error: " + r.message );
					}
				    } catch( e ) {
					winston.error( "Popeye error: " + e.message );
				    }
				}
			    });
			}
			else {
			    winston.debug( "Popeye disabled, not sending message." );
			}
		    });
		});
		part.addListener("close", function() {
		    winston.error("client abort. close the file stream " + fileId);
		    return ws.end();
		});
	    }
	    form.parse( req, function( err, fields, files ) {
	    });
	}
	else {
	    //
	    // This req.pipe(ws) was finishing before the req.on(end was getting
	    // the last bytes.  So do the write in req.on(end to keep things in
	    // sync.
	    //
	    req.pipe(ws);
	    req.on("data", function(buffer) {
		info.bytesReceived += buffer.length;
		info.offset += buffer.length;
		if (info.offset > info.finalLength) {
		    return httpStatus(res, 500, "Exceeded Final-Length", null, meta);
		}
		if (info.received > contentLength) {
		    return httpStatus(res, 500, "Exceeded Content-Length", null, meta);
		}
		// Do the write HERE
		// ws.write(buffer);
	    });
	    req.on("end", function() {
		winston.debug( "Request end: bytes received=" +  info.offset );
		if (!res.headersSent) {
		    // httpStatus(res, 200, "Ok", JSON.stringify(info));
		    httpStatus(res, 200, "Ok", null, meta);
		}
		return u.save( function() {
		    mixpanel.track( 'upload_completed', {
			distinct_id: info.fileId,
			media_uuid: info.fileId,
			user_uuid: info.uid,
			activity: 'brewtus',
			tech: getTech( req ),
			deployment: process.env.NODE_ENV || 'local'
		    });
		    if ( config.popeye != "none" ) {
			winston.info("\npcol popeye: " + config.popeye + "?path=" + filePath + "\n" );
			request( {url: config.popeye, qs: { path: filePath, skip_faces: info.skip_faces, try_photos: info.try_photos } }, function( err, res, body ) {
			    if ( err ) {
				winston.error( "Popeye error: " + err.message );
			    }
			    else if ( res.statusCode != 200 ) {
				winston.error( "Popeye error: " + res.statusCode );
			    }
			    else {
				try {
				    var r = JSON.parse( body );
				    if ( r.error ) {
					winston.error( "Popeye error: " + r.message );
				    }
				} catch( e ) {
				    winston.error( "Popeye error: " + e.message );
				}
			    }
			});
		    }
		    else {
			winston.debug( "Popeye disabled, not sending message." );
		    }
		});
	    });
	    req.on("close", function() {
		winston.error("client abort. close the file stream " + fileId);
		return ws.end();
	    });
	    ws.on("close", function() {
		// winston.info("closed the file stream " + fileId);
	    });
	    return ws.on("error", function(e) {
		return httpStatus(res, 500, "File Error", null, meta);
	    });
	}
    };

    batchFile = function(req, res, fid) {
	var contentLength, fileId, filePath, info, offsetIn, status, u, ws;
	fileId = fid;
	if (fileId == null) {
	    return httpStatus(res, 404, "Not Found");
	}
	filePath = path.join(config.files, fileId);
	if (!fs.existsSync(filePath)) {
	    return httpStatus(res, 404, "Not Found");
	}
	offsetIn = 0;
	u = upload.Upload(config, fileId);
	status = u.load();

	var meta = {
	    method: 'PATCH',
	    fileId: fileId,
	    uid: status.info.uid };

	if (status.error != null) {
	    return httpStatus(res, status.error[0], status.error[1], null, meta);
	}
	info = status.info;

	info.offset = offsetIn;
	info.state = "patched";
	info.patchedOn = Date.now();
	info.bytesReceived = 0;

	var form = new formidable.IncomingForm();
	var myfile;
	form.uploadDir = config.files;
	form.keepExtensions = false;
	form.on( 'fileBegin', function( name, file ) {
	    file.path = filePath;
	    file.name = fileId;
	    myfile = file;
	});
	form.on( 'progress', function( recv, total ) {
	    if ( myfile ) {
		info.bytesReceived = myfile.size;
		info.offset = myfile.size;
	    }
	    if ( ! info.finalLength ) info.finalLength = total;
	    u.save();
	});
	form.on( 'error', function( err ) {
	    return httpStatus(res, 500, "File Error", null, meta);
	});
	form.on( 'aborted', function() {
	    winston.error("client abort. close the file stream " + fileId);
	});
	form.on( 'end', function() {
	    if (!res.headersSent) {
		httpStatus(res, 200, "Ok", null, meta);
	    }
	    info.bytesReceived = myfile.size;
	    info.offset = myfile.size;
	    info.finalLength = myfile.size;
	    return u.save( function() {
		mixpanel.track( 'upload_completed', {
		    distinct_id: info.fileId,
		    media_uuid: info.fileId,
		    user_uuid: info.uid,
		    activity: 'brewtus',
		    tech: getTech( req ),
		    deployment: process.env.NODE_ENV || 'local'
		});
		if ( config.popeye != "none" ) {
		    winston.info("\npcol popeye: " + config.popeye + "?path=" + filePath + "\n" );
		    request( {url: config.popeye, qs: { path: filePath, skip_faces: info.skip_faces, try_photos: info.try_photos } }, function( err, res, body ) {
			if ( err ) {
			    winston.error( "Popeye error: " + err.message );
			}
			else if ( res.statusCode != 200 ) {
			    winston.error( "Popeye error: " + res.statusCode );
			}
			else {
			    try {
				var r = JSON.parse( body );
				if ( r.error ) {
				    winston.error( "Popeye error: " + r.message );
				}
			    } catch( e ) {
				winston.error( "Popeye error: " + e.message );
			    }
			}
		    });
		}
		else {
		    winston.debug( "Popeye disabled, not sending message." );
		}
	    });
	});
	form.parse( req );
    };

    httpStatus = function(res, statusCode, reason, body, meta ) {

	if (res.headersSent)
	    return res.end();

	if ( statusCode > 205 ) {
	    winston.error( 'bad request: ' + statusCode + ': ' + reason, meta );
	}
	else {
	    if ( meta && meta.method ) {
		winston.info( meta.method + ': ' + meta.fileId, meta );
	    }
	}
	
	if (body == null) {
	    body = '';
	}
	
	try {
	    res.writeHead(statusCode, reason);
	} catch(error) {
	    winston.error(util.inspect(error));
	}
	return res.end(body);
    };

    ALLOWED_METHODS = ["HEAD", "PATCH", "POST", "OPTIONS", "GET", "DELETE"];

    ALLOWED_METHODS_STR = ALLOWED_METHODS.join(",");
    
    PATTERNS = [
	{
	    match: /files(\/(.+))*/,
	    HEAD: headFile,
	    PATCH: patchFile,
	    POST: createFile,
	    OPTIONS: optionsFile,
	    DELETE: deleteFile,
	    GET: getFile
	}
    ];

    route = function(req, res) {
	var matches, parsed, pattern, query, urlPath, _i, _len, _ref;
	//winston.debug(util.inspect(req));
	if (_ref = req.method, __indexOf.call(ALLOWED_METHODS, _ref) < 0) {
	    return httpStatus(res, 405, "Not Allowed");
	}
	parsed = url.parse(req.url, true);
	urlPath = parsed.pathname;

	var pmsg = "\n" +
	    "pcol -----------------------------------------------------------------------------------------------\n" +
	    "pcol " + req.method + " " + urlPath + "\n";
	for( var key in req.headers ) {
	    pmsg = pmsg + "pcol   " + key + ": " + req.headers[key] + "\n"
	}
	pmsg = pmsg + "pcol -----------------------------------------------------------------------------------------------\n";
	winston.info( pmsg );

	if (urlPath === "/") {
	    if (req.method !== "GET") {
		return httpStatus(res, 405, "Not Allowed");
	    }
	    return testUploadPage(res);
	}
	if (!(urlPath.length > 1)) {
	    return httpStatus(res, 405, "Not Allowed");
	}
	query = parsed.query;

	if ( query['_method'] && query['_method'] == 'PATCH' ) {
	    // This is an IE9 -style form-based upload.
	    var i = urlPath.match( /files(\/(.+))*/ );
	    return batchFile( req, res, i[2] );
	}

	for (_i = 0, _len = PATTERNS.length; _i < _len; _i++) {
	    pattern = PATTERNS[_i];
	    matches = urlPath.match(pattern.match);
	    // winston.debug("" + (util.inspect(matches)));
	    if (matches != null) {
		return pattern[req.method](req, res, query, matches);
	    }
	}
	return httpStatus(res, 405, "Not Allowed");
    };

    commonHeaders = function(res) {
	res.setHeader("Server", config.server);
	res.setHeader("Access-Control-Allow-Origin", "*");
	res.setHeader("Access-Control-Allow-Methods", ALLOWED_METHODS_STR);
	res.setHeader("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept, Final-Length, Offset, Content-Range, Content-Disposition");
	return res.setHeader("Access-Control-Expose-Headers", "Location, Offset");
    };

    tusHandler = function(req, res) {
	commonHeaders(res);
	return route(req, res);
    };

    setupLogger = function(logDir, logFileName, logRotateSize) {
	var logfw, opts;
	try {
	    fs.mkdirSync(logDir);
	} catch (error) {
	    if ((error != null) && error.code !== "EEXIST") {
		winston.error(util.inspect(error));
		process.exit(1);
	    }
	}
	opts = {
	    flags: 'a',
	    encoding: 'utf8',
	    bufferSize: 0
	};
	logfw = fs.createWriteStream(logFileName, opts);
	logfw.once("open", function(logfd) {
	    return fs.watchFile(logFileName, function(cur, prev) {
		if (cur.size > logRotateSize) {
		    fs.truncate(logfd, 0);
		    return winston.warn("Rotated logfile");
		}
	    });
	});
	process.on('uncaughtException', function(err) {
	    winston.error("uncaught exception " + (util.inspect(err)));
	    return logfw.once("drain", function() {
		return process.exit(1);
	    });
	});
	winston.add(winston.transports.File, {
	    stream: logfw,
	    level: config.logLevel,
	    json: false,
	    timestamp: true
	});
	winston.add( SysLogger, {
	    app_name: 'brewtus',
	    level: config.logLevel
	});
      
	return winston.remove(winston.transports.Console);
    };

    initApp = function(args) {
	var configFileName, fileNamePrefix, logDir, logFileName;
	fileNamePrefix = path.basename(__filename, path.extname(__filename));
	config = Config( 'brewtus' )
	winston.debug(util.inspect(config));
	logDir = config.logDir || path.join(__dirname, "logs");
	logFileName = path.join(logDir, "" + fileNamePrefix + ".log");
	setupLogger(logDir, logFileName, config.logRotateSize);
	mixpanel = Mixpanel.init('aaeab0c46192750b89eecddefd0331f4');
	try {
	    fs.mkdirSync(config.files);
	} catch (error) {
	    if ((error != null) && error.code !== "EEXIST") {
		console.log(util.inspect(error));
		winston.error(util.inspect(error));
		process.exit(1);
	    }
	}
	return setup.emit("setupComplete");
    };

    startup = function(args) {
	setup.once("setupComplete", function() {
	    var server;
	    server = http.createServer(tusHandler);
	    server.timeout = 30000;
	    winston.debug( 'Trying port ' + config.port );
	    server.listen(config.port);
	    return winston.info("Server running on port " + config.port );
	});
	return initApp(args);
    };
    
    startup(process.argv);

}).call(this);
