import datetime
from datetime import timedelta
import logging
import threading
import platform
import Queue
from sqlalchemy import *
import sys
import time

class Serialize( object ):
    '''Utility class to acquire and release locks in a shared
    database, with heartbeat / expirey functionality.'''

    def __init__( self, app, object_name, owner_id, app_config, expirey=None, heartbeat=None, timeout=None ):
        '''Constructor( app, object_name, owner_id, app_config, expirey=None, heartbeat=None, timeout=None
        app - A 64 character or less string that denotes the domain of the lock
        object_name - A 64 character or less string identifying the object that is locked
        owner_id - A unique caller string identifying the process owning this lock

        app_config - A Viblio AppConfig object with database
        connectivity and log file information

        expirey - Optional, the seconds that a lock is valid for.  If
        not set the lock expires in roughly 18 months. Setting this in
        the constructor establishes a default for future calls to
        acquire that may be overridden on a per call basis.

        heartbeat - Optional, if set overrides the expirey setting.
        The seconds between heartbeat updates of acquired locks.  Each
        heartbeat advances the expirey date to be 3 * heartbeat
        interval in the future.  If not set, no heartbeat
        occurs. Setting this in the constructor establishes a default
        for future calls to acquire that may be overridden on a per
        call basis.

        timeout - Optional, the seconds that a blocking acquire call
        should wait attempting to acquire the lock. Setting this in
        the constructor establishes a default for future calls to
        acquire that may be overridden on a per call basis.
        '''

        self.has_lock = False

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
            raise Exception( "If heartbeat is provided it must be a positive number." )
        self.heartbeat   = heartbeat
        self.heartbeat_running = False

        if expirey != None and expirey <= 0:
            raise Exception( "If expirey is provided it must be a positive number." )
        if expirey == None and heartbeat:
            self.expirey = heartbeat * 3
        elif expirey != None:
            self.expirey = expirey
        else:
            # Set the expiration to "forever" - or 18 months from now.
            self.expirey = int( 18*30.5*24*60*60 )

        if timeout != None and timeout <= 0:
            raise Exception( "If timeout is provided it must be a positive number." )
        self.timeout = timeout

        # How frequently we will check for a lock while blocking.
        t_time = 600
        e_time = 180
        if timeout: t_time = timeout
        if expirey: e_time = expirey
        # Check the minimum of 60 seconds, the largest of 2 and
        # timeout/10, and the largest of 2 and expirey / 3
        self.polling_interval = int( min( 60, max( 2, ( t_time + 0.0 ) / 10 ), max( 2, ( e_time + 0.0 ) / 3 ) ) )

        if ( 'db_user' not in app_config ) or ( 'db_pass' not in app_config ) or ( 'db_conn' not in app_config ) or ( 'db_name' not in app_config ) or ( 'logfile' not in app_config ) or ( 'loglevel' not in app_config ):
            raise Exception( "app_config must have the following members: db_conn, db_name, db_pass, db_user, logfile, loglevel" ) 
        self.config      = app_config

        # Get database connection
        try:
            self.engine      = create_engine( 'mysql+mysqldb://'+app_config.db_user+':'+app_config.db_pass+app_config.db_conn+app_config.db_name )
            self.conn        = _get_conn( self.engine )
            self.meta        = _get_meta( self.engine )
        except Exception as e:
            raise Exception( "Failed to establish database connection, error was: " + str( e ) )

        # Set up logging
        try:
            logging.basicConfig( filename = app_config['logfile'], level = app_config.loglevel )
            self.log      = logging.getLogger( __name__ )
        except Exception as e:
            raise Exception( "Failed to set up logging, error was: " + str( e ) )

    def __del__( self ):
        '''Finalizer to clean things up:
        Stop heartbeating if it is happening.
        Release the lock if any.
        Close the database connection if it exists.'''
        message = ""
        try:
            self.log.info( "Ensuring lock released in destructor." )
            if self.has_lock:
                self.release()
                self.has_lock = False
        except Exception as e:
            m = "Error occurred in destructor for Serialize while releasing lock for %s, %s, %s: %s" % ( self.app, self.object_name, self.owner_id, str( e ) )
            self.log.error( m )
            message += m

        try:
            self.log.info( "Closing database connection and disposing of engine." )
            self.conn.close()
            self.engine.dispose()
            if self.heartbeat_running:
                self.log.info( "Stopping heartbeat for %s, %s, %s in release." 
                                % ( self.app, self.object_name, self.owner_id ) )
                self._stop_heartbeat()
        except Exception as e:
            m = "Error occurred while stopping heartbeat for %s, %s, %s: %s" % ( self.app, self.object_name, self.owner_id, str( e ) )
            self.log.error( m )
            raise Exception( message + m )

    def acquire( self, blocking=True, expirey=None, heartbeat=None, timeout=None ):
        '''Acquire the lock for self.object_name, self.owner_id.  
        
        If blocking is set to true this method will wait until it
        acquires the lock and then returns true.  If blocking is set
        to false and the lock is not available, this method will
        return false immediately.

        Optionally establish an expiry time for the lock.

        Optionally establish a heartbeat to update the lock each
        heartbeat seconds.  If this is set the expiry is automatically
        rolled forward on each heartbeat.
        
        Optionally establish a timeout for blocking attempts to
        acquire the lock.
        '''

        try:
            begin_time = datetime.datetime.now()

            if heartbeat == None:
                heartbeat = self.heartbeat

            if expirey == None and heartbeat:
                expirey = heartbeat * 3
            elif expirey == None:
                expirey = self.expirey

            if timeout == None:
                timeout = self.timeout

            conn = self.conn
            meta = self.meta
            serialize = meta.tables['serialize']

            # Check if the object is locked by anyone.
            self.log.info( "Checking the current lock status for %s, %s." 
                           % ( self.app, self.object_name ) )
            
            result = conn.execute( select( [serialize] )
                                   .where( serialize.c.app == self.app 
                                           and serialize.c.object_name == self.object_name ).execution_options( autocommit=True ) )

            lock = result.fetchone()
            result.close()

            if lock == None:
                # It appears this object has never been locked, try to
                # set up a lock.
                self.log.info( "Attempting to create lock for %s, %s." 
                               % ( self.app, self.object_name ) )
                conn.execute( serialize.insert(),
                              app = self.app,
                              object_name = self.object_name,
                              owner_id = self.owner_id,
                              server = platform.node(),
                              expirey_date = datetime.datetime.now()+timedelta( seconds=expirey ) )
            elif lock['owner_id'] == None:
                # It appears no one has the row, try to acquire it.
                self.log.info( "Attempting to lock entry for %s, %s." 
                               % ( self.app, self.object_name ) )
                conn.execute( serialize
                              .update()
                              .where( serialize.c.app == self.app 
                                      and serialize.c.object_name == self.object_name 
                                      and serialize.c.owner_id == None )
                              .values( owner_id = self.owner_id, 
                                       expirey_date = datetime.datetime.now() + timedelta( seconds=expirey ), 
                                       server = platform.node() ) )

            # Check if we successfully created / acquired the lock, or
            # lost a race:
            acquired = False

            while not acquired:
                self.log.info( "Checking who owns the lock for %s, %s." 
                               % ( self.app, self.object_name ) )
                result = conn.execute( select( [serialize] )
                                       .where( serialize.c.app == self.app 
                                               and serialize.c.object_name == self.object_name 
                                               and serialize.c.owner_id == self.owner_id ).execution_options( autocommit=True ) )
                lock = result.fetchone()
                result.close()
                self.log.info( "Lock %s, %s owned by %s." 
                               % ( self.app, self.object_name, lock['owner_id'] ) )

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
                    self.has_lock = True
                    return True
                elif lock['owner_id'] == None:
                    # It appears no one has the row, try to acquire it.
                    self.log.info( "Attempting to lock entry for %s, %s." 
                                   % ( self.app, self.object_name ) )
                    conn.execute( serialize
                                  .update()
                                  .where( serialize.c.app == self.app 
                                          and serialize.c.object_name == self.object_name 
                                          and serialize.c.owner_id == None )
                                  .values( owner_id = self.owner_id, 
                                           expirey_date = datetime.datetime.now() + timedelta( seconds=expirey ), 
                                           server = platform.node() ) )
                    continue
                else:
                    if expirey != None:
                        if lock['expirey_date'] < datetime.datetime.now():
                            self.log.warning( "Lock expired at %s, attempting to steal lock %s, %s from %s on server %s" 
                                              % ( lock['expirey_date'], self.app, self.object_name, lock['owner_id'], str( lock['server'] ) ) )
                            conn.execute( serialize
                                          .update()
                                          .where( serialize.c.app == self.app 
                                                  and serialize.c.object_name == self.object_name 
                                                  and serialize.c.owner_id == lock['owner_id']
                                                  and serialize.d.expirey_date == lock['expirey_date'] )
                                          .values( owner_id = self.owner_id, 
                                                   expirey_date = datetime.datetime.now() + timedelta( seconds=expirey ), 
                                                   server = platform.node() ) )
                            continue
                    if blocking:
                        if timeout:
                            if begin_time + timedelta( seconds=timeout ) <= datetime.datetime.now():
                                self.log.info( "Timeout exceeded waiting for lock %s, %s, %s. Returning." % ( self.app, self.object_name, self.owner_id ) )
                                self.has_lock = False
                                return False
                            else:
                                wait_time = min( self.polling_interval, max( 1, int( ( begin_time + timedelta( seconds=timeout ) - datetime.datetime.now() ).total_seconds() ) ) ) 
                                self.log.info( "Waiting %s seconds for lock in blocking call for %s, %s, %s" 
                                               % ( wait_time, self.app, self.object_name, self.owner_id ) )
                                time.sleep( wait_time )
                                continue
                        else:
                            self.log.info( "Waiting %s seconds for lock in blocking call for %s, %s, %s" 
                                           % ( self.polling_interval, self.app, self.object_name, self.owner_id ) )
                            time.sleep( self.polling_interval )
                            continue
                            
                    else:
                        self.log.info( "Failed to acquire lock in non-blocking call for %s, %s, %s" 
                                       % ( self.app, self.object_name, self.owner_id ) )
                        self.has_lock = False
                        return False
                        
        except Exception as e:
            self.log.error( "Failed to acquire lock, error was: " + str( e ) )
            raise
            
    def release( self ):
        '''If the owner_id is held for object_name it is released and
        true is returned.

        If the owner_id is not held for object_name false is returned.'''
        message = ""
        try:
            if self.heartbeat_running:
                self.log.info( "Stopping heartbeat for %s, %s, %s in release." 
                                % ( self.app, self.object_name, self.owner_id ) )
                self._stop_heartbeat()
        except Exception as e:
            message = "Error occurred while stopping heartbeat for %s, %s, %s: %s" % ( self.app, self.object_name, self.owner_id, str( e ) )
            self.log.error( message )

        try:
            serialize = self.meta.tables['serialize'] 

            self.log.info( "Trying to release lock %s, %s on behalf of %s." 
                      % ( self.app, self.object_name, self.owner_id ) )
            result = self.conn.execute( select( [serialize] )
                                        .where( serialize.c.app == self.app 
                                                and serialize.c.object_name == self.object_name 
                                                and serialize.c.owner_id == self.owner_id ).execution_options( autocommit=True ) )
            
            lock = result.fetchone()
            result.close()

            if lock == None:
                self.log.info( "No need to release lock - lock %s, %s does not exist."
                               % ( self.app, self.object_name ) )
                self.has_lock = False
                return False
            elif lock['owner_id'] != self.owner_id:
                self.log.info( "We don't own the lock so can not release lock %s, %s, it is owned by %s."
                               % ( self.app, self.object_name, str( lock['owner_id'] ) ) )
                self.has_lock = False
                return False
            else:
                self.conn.execute( serialize
                                   .update()
                                   .where( serialize.c.app == self.app 
                                           and serialize.c.object_name == self.object_name 
                                           and serialize.c.owner_id == self.owner_id )
                                   .values( owner_id = None ) ) 
                self.log.info( "Lock %s, %s released by %s."
                               % ( self.app, self.object_name, self.owner_id ) )
                self.has_lock = False

        except Exception as e:
            self.log.error( "Failed to release lock %s, %s for %s. Error was: %s" 
                            % ( self.app, self.object_name, self.owner_id, str( e ) ) )
            raise

        if len( message ):
            raise Exception( message )

    def force_global_release( self ):
        '''Note: Not intended for general use.  This method forcibly
        obliterates the lock for object_name.  If any other process
        was using the lock, this module can't be held responsible for
        the consequences.'''
        pass

    def _start_heartbeat( self, heartbeat ):
        '''Helper function, begin heartbeating the held lock object in
        a new process.'''
        self.queue = Queue.Queue()
        t = threading.Thread( target=_do_heartbeat, args=( self.queue, self.config, self.app, self.object_name, self.owner_id, heartbeat ) )
        try:
            t.start()
        except Exception as e:
            self.log.info( "Error starting heartbeat: " + str( e ) )
            raise

        self.heartbeat_running = True

    def _stop_heartbeat( self ):
        '''Helper function, stop heartbeating the object.'''
        if self.heartbeat_running:
            self.queue.put_nowait( True )
            self.heartbeat_running = False
        else:
            self.log.warning( "Got call to stop heartbeat, but no heartbeat was running for %s, %s, %s" % ( self.app, self.object_name, self.owner_id ) )


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

def _do_heartbeat( queue, config, app, object_name, owner_id, heartbeat ):
    stop = False

    db_engine = create_engine( 'mysql+mysqldb://'+config.db_user+':'+config.db_pass+config.db_conn+config.db_name )

    conn = _get_conn( db_engine )
    meta = _get_meta( db_engine )

    serialize = meta.tables['serialize']

    log = logging.getLogger( __name__ )

    while not stop:
        try:
            stop = queue.get_nowait()
        except Queue.Empty as e:
            pass
        
        if stop:
            log.info( "Stopping heartbeat on %s, %s, %s" % ( app, object_name, owner_id ) )
            log.info( "Closing database connection and disposing of engine." )
            conn.close()
            db_engine.dispose()
            return True
        else:
            log.info( "Heartbeating %s, %s, %s" % ( app, object_name, owner_id ) )
            conn.execute( serialize.update().where( serialize.c.app == app and serialize.c.object_name == object_name and serialize.c.owner_id == owner_id ).values( expirey_date = datetime.datetime.now() + timedelta( seconds=heartbeat*3 ), server = platform.node() ) )
            time.sleep( heartbeat )


