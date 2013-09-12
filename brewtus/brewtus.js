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

  setup = new events.EventEmitter();

  config = {};

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
	  if (status.error != null) {
	      return httpStatus(res, status.error[0], status.error[1]);
	  }
	  winston.info( "Our Location header is: " + req.headers.host );
	  res.setHeader("Location", "http://" + req.headers.host + "/files/" + fileId);
	  return httpStatus(res, 201, "Created");
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
      winston.debug( "HEAD: info: " + util.inspect(info) );
    res.setHeader("Offset", info.offset);
    res.setHeader("Connection", "close");
    return httpStatus(res, 200, "Ok");
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
    if (req.headers["content-type"] !== "application/offset+octet-stream") {
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
    if (status.error != null) {
      return httpStatus(res, status.error[0], status.error[1]);
    }
    info = status.info;
    if (offsetIn > info.offset) {
      return httpStatus(res, 400, "Invalid Offset");
    }
    ws = fs.createWriteStream(filePath, {
      flags: "r+",
      start: offsetIn
    });
    if (ws == null) {
      winston.error("unable to create file " + filePath);
      return httpStatus(res, 500, "File Error");
    }
    info.offset = offsetIn;
    info.state = "patched";
    info.patchedOn = Date.now();
      winston.debug( "Setting bytes received to zero for new request" );
    info.bytesReceived = 0;
      // This req.pipe(ws) was finishing before the req.on(end was getting
      // the last bytes.  So do the write in req.on(end to keep things in
      // sync.
      //
      req.pipe(ws);
      req.on("data", function(buffer) {
	  winston.debug("old Offset " + info.offset + " of " + info.finalLength );
	  info.bytesReceived += buffer.length;
	  info.offset += buffer.length;
	  winston.debug("new Offset " + info.offset + " of " + info.finalLength);
	  if (info.offset > info.finalLength) {
              return httpStatus(res, 500, "Exceeded Final-Length");
	  }
	  if (info.received > contentLength) {
              return httpStatus(res, 500, "Exceeded Content-Length");
	  }
	  // Do the write HERE
	  // ws.write(buffer);
      });
      req.on("end", function() {
	  winston.debug( "Request end: bytes received=" +  info.offset );
	  if (!res.headersSent) {
              // httpStatus(res, 200, "Ok", JSON.stringify(info));
	      winston.debug( "Sending HEADERs..." );
              httpStatus(res, 200, "Ok");
	  }
	  return u.save( function() {
	      if ( config.popeye != "none" ) {
		  winston.debug( "Sending popeye request to: " + config.popeye );
		  request( {url: config.popeye, qs: { path: filePath }}, function( err, res, body ) {
		      if ( res.statusCode != 200 ) {
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
	winston.info("closed the file stream " + fileId);
	return winston.debug("ws.on(close)");
    });
    return ws.on("error", function(e) {
	winston.error("closed the file stream " + fileId + " " + (util.inspect(e)));
	return httpStatus(res, 500, "File Error");
    });
  };

  httpStatus = function(res, statusCode, reason, body) {
    if (body == null) {
      body = '';
    }
    res.writeHead(statusCode, reason);
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
    winston.info("URLPATH: " + urlPath + ", METHOD: " + req.method );
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
    for (_i = 0, _len = PATTERNS.length; _i < _len; _i++) {
      pattern = PATTERNS[_i];
      matches = urlPath.match(pattern.match);
      winston.debug("" + (util.inspect(matches)));
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
    return res.setHeader("Access-Control-Expose-Headers", "Location");
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
