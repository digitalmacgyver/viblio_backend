import datetime
from datetime import timedelta
import logging
import multiprocessing
import platform
import Queue
from sqlalchemy import *
import sys
import time

class Serialize( object ):
    '''Utility class to acquire and release locks in a shared
    database, with heartbeat / timeout functionality.'''

    def __init__( self, app, object_name, owner_id, app_config, heartbeat=None, timeout=None ):
        '''Constructor( app, object_name, owner_id, app_config, heartbeat=None, timeout=None
        app - A 64 character or less string that denotes the domain of the lock
        object_name - A 64 character or less string identifying the object that is locked
        owner_id - A unique caller string identifying the process owning this lock

        app_config - A Viblio AppConfig object with database
        connectivity and log file information

        heartbeat - Optional, if set establishes a default for this
        parameter to the acquire method (invocations of acquire can
        still override this default)

        timeout - Optional, if set establishes a default for this
        parameter to the acquire method (invocations of acquire can
        still override this default)
        '''

        # Mundane variables
        if not app or len( app ) > 64:
            raise Exception( "app argument must be a 64 character or less string." )
        self.app         = app

        if not object_name or len( object_name ) > 64:
            raise Exception( "app argument must be a 64 character or less string." )
        self.object_name = object_name

        if not owner_id or len( owner_id ) > 64:
            raise Exception( "app argument must be a 64 character or less string." )
        self.owner_id    = owner_id

        if heartbeat != None and heartbeat <= 0:
            raise Exception( "If heartbeat is provided it most be a positive number." )
        self.heartbeat   = heartbeat
        self.heartbeat_running = False

        if timeout != None and timeout <= 0:
            raise Exception( "If timeout is provided it most be a positive number." )
        self.timeout     = timeout

        if ( db_user not in app_config ) or ( db_pass not in app_config ) or ( db_conn not in app_config ) or ( db_name not in app_config ) or ( logfile not in app_config ) or ( loglevel not in app_config ):
            raise Exception( "app_config must have the following members: db_conn, db_name, db_pass, db_user, logfile, loglevel" ) 
        self.config      = app_config

        # How frequently we will check for a lock while blocking.
        # DEBUG - Set this to something reasonable like 60 seconds.
        self.polling_interval = 3

        # Get database connection
        try:
            self.engine      = create_engine( 'mysql+mysqldb://'+app_config.db_user+':'+app_config.db_pass+config.db_conn+config.db_name )
            self.conn        = _get_conn( engine )
            self.meta        = _get_meta( engine )
        except Exception as e:
            raise Exception( "Failed to extablish database connection, error was: " + str( e ) )

        # Set up logging
        try:
            logging.basicConfig( filename = app_config['logfile'], level = config.loglevel )
            self.log      = logging.getLogger( __name__ )
            screen_output = logging.StreamHandler( sys.stdout )
            self.log.addHandler( screen_output )
        except Exception as e:
            raise Exception( "Failed to set up logging, error was: " + str( e ) )

    def __del__( self ):
        '''Finalizer to clean things up:
        Stop heartbeating if it is happening.
        Release the lock if any.
        Close the database connection if it exists.'''
        print "DESTUCTOR CALLED"
        pass

    def acquire( self, blocking=True, heartbeat=None, timeout=None ):
        '''Acquire the lock for self.object_name, self.owner_id.  
        
        If blocking is set to true this method will wait until it
        acquires the lock and then returns true.  If blocking is set
        to false and the lock is not available, this method will
        return false immediately.

        Optionally establish a heartbeat to update the lock each
        heartbeat seconds.
        
        Optionally steal the lock for object if it is more than
        timeout seconds old.'''

        # DEBUG - Sqlalchemy behavior when a UK or PK is violated - does it throw an exception?

        try:
            if heartbeat == None:
                heartbeat = self.heartbeat
            if timeout == None:
                timeout = self.timeout

            # Check if the object is locked by anyone.
            self.log.info( "Checking the current lock status for %s, %s." % ( self.app, self.object_name ) )
            lock = conn.execute( select( [serialize] ).where( app == self.app and object_name == self.object_name ) ).fetch()

            if lock == None:
                # It appears this object has never been locked, try to
                # set up a lock.
                self.log.info( "Attempting to create lock for %s, %s." % ( self.app, self.object_name ) )
                conn.execute( serialize.insert(),
                              app = self.app,
                              object_name = self.object_name,
                              owner_id = self.owner_id,
                              server = platform.node(),
                              acquired_date = datetime.datetime.now() )
                              
            if lock['owner_id'] == None:
                # It appears no one has the row, try to acquire it.
                self.log.info( "Attempting to lock entry for %s, %s." % ( self.app, self.object_name ) )
                conn.execute( serialize
                              .update()
                              .where( serialize.c.app == app 
                                      and serialize.c.object_name == object_name 
                                      and serialize.c.owner_id == None )
                              .values( owner_id = self.owner_id, 
                                       acquired_date = datetime.datetime.now(), 
                                       server = platform.node() ) )

            # Check if we succesfully created / acquired the lock, or
            # lost a race:
            acquired = False

            while not acquired:
                self.log.info( "Checking who owns the lock for %s, %s." 
                               % ( self.app, self.object_name ) )
                lock = conn.execute( select( [serialize] )
                                     .where( app == self.app 
                                             and object_name == self.object_name 
                                             and owner_id == self.owner_id ) )

                if lock['owner_id'] == self.owner_id:
                    acquired = True
                    self.log.info( "Lock acquired for %s, %s, %s" 
                                   % ( self.app, self.object_name, self.owner_id ) )

                    if self.heartbeat_running:
                        self.log.info( "Stopping old heartbeat for %s, %s, %s." 
                                       % ( self.app, self.object_name, self.owner_id ) )
                        self._stop_heartbeat()

                    if heartbeat:
                        self.log.info( "Starting new heartbeat for %s, %s, %s." 
                                       % ( self.app, self.object_name, self.owner_id ) )
                        self._start_heartbeat( heartbeat )
                    return True
                else:
                    if timeout != None:
                        timeout_delta = timedelta( seconds=timeout )
                        # DEBUG - test timezone shenanigans.
                        if lock['acquired_date'] + time_delta < datetime.datetime.now():
                            self.log.warning( "Timeout of %s seconds exceeded, attempting to steal lock %s, %s from %s on server %s" 
                                              % ( timeout, self.app, self.object_name, lock['owner_id'], str( lock['server'] ) ) )
                            conn.execute( serialize
                                          .update()
                                          .where( serialize.c.app == app 
                                                  and serialize.c.object_name == object_name 
                                                  and serialize.c.owner_id == lock['owner_id']
                                                  and serialize.d.acquired_date == lock['acquired_date'] )
                                          .values( owner_id = self.owner_id, 
                                                   acquired_date = datetime.datetime.now(), 
                                                   server = platform.node() ) )
                            continue
                    if blocking:
                        self.log.info( "Waiting %s seconds for lock in blocking call for %s, %s, %s" 
                                       % ( self.polling_interval, self.app, self.object_name, self.owner_id ) )
                        time.sleep( self.polling_interval )
                        continue
                    else:
                        self.log.info( "Failed to acquire lock in non-blocking call for %s, %s, %s" 
                                       % ( self.app, self.object_name, self.owner_id ) )
                        return False
                        
        except Exception as e:
            self.log.error( "Failed to acquire lock, error was: " + str( e ) )
            
    def release( self ):
        '''If the owner_id is held for object_name it is released and
        true is returned.

        If the owner_id is not held for object_name false is returned.'''
        pass

    def force_global_release( self ):
        '''Note: Not intended for general use.  This method forcibly
        obliterates the lock for object_name.  If any other process
        was using the lock, this module can't be held responsible for
        the consequences.'''
        pass

    def _start_heartbeat( self, heartbeat ):
        '''Helper function, begin heartbeating the held lock object in
        a new process.'''
        self.queue = multiprocessing.Queue()
        p = multiprocessing.Process( target=_do_heartbeat, args=( self.queue, self.engine, self.app, self.object_name, self.owner_id, heartbeat ) )
        
        log.info( "Starting heartbeat for %s, %s, %s" % ( self.app, self.object_name, self.owner_id ) )
        p.start()
        self.heartbeat_running = True

    def _stop_heartbeat( self ):
        '''Helper function, stop heartbeating the object.'''
        if self.heartbeat_running:
            log.info( "Stopping heartbeat for %s, %s, %s" % ( self.app, self.object_name, self.owner_id ) )
            self.queue.put_nowait( True )
            self.heartbeat_running = False
        else:
            log.warning( "Got call to stop hearbeat, but no heartbeat was running for %s, %s, %s" % ( self.app, self.object_name, self.owner_id ) )


######################################################################
# Helper functions external to the class

def _get_conn( engine ):
    try:
        if not hasattr( _get_meta, 'conn' ):
            _get_conn.conn = engine.connect()
        return _get_conn.conn
    except Exception as e:
        raise

def _get_meta( engine ):
    try:
        if not hasattr( _get_meta, 'meta' ):
            _get_meta.meta = MetaData()
            _get_meta.meta.reflect( bind = engine )
        return _get_meta.meta
    except Exception as e:
        raise

def _do_heartbeat( queue, db_engine, app, object_name, owner_id, heartbeat ):
    stop = False

    conn = _get_conn( db_engine )
    meta = _get_meta( db_engine )

    serialize = meta.tables['serialize']

    while not stop:
        try:
            stop = queue.get_nowait()
        except Queue.Empty as e:
            pass
        
        if stop:
            print "Stopping heartbeat." + str( time.gmtime() )
            return True
        else:
            print "Heartbeating %s, %s - %s" % ( object_name, owner_id, str( time.gmtime() ) )
            conn.execute( serialize.update().where( serialize.c.app == app and serialize.c.object_name == object_name and serialize.c.owner_id == owner_id ).values( acquired_date = datetime.datetime.now(), server = platform.node() ) )
            time.sleep( heartbeat )


