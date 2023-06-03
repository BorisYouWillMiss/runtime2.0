"""VDOM storage module"""

import sqlite3
import cPickle
import traceback

from utils.semaphore import VDOM_semaphore
from utils.exception import VDOM_exception
from utils.mutex import VDOM_named_mutex_auto
import settings
from daemon import VDOM_storage_writer

_save_sql = "INSERT OR REPLACE INTO Resource_index (res_id, app_id, filename, name, res_type,res_format) VALUES (?, ?,?,?,?,?)"
#__update_sql = "UPDATE Resource_index filename=?, name =? , res_type = ?, res_format = ? WHERE res_id=? "
_clear_sql = "DELETE FROM Resource_index"
_create_sql = "CREATE TABLE IF NOT EXISTS Resource_index (res_id NOT NULL UNIQUE, app_id NOT NULL, filename NOT NULL, name NOT NULL, res_type,res_format)"
_list_sql = "SELECT app_id, res_id, res_format, name FROM Resource_index"
_list_res = "SELECT filename, name, res_type, res_format from Resource_index WHERE res_id = ?"
_delete_sql = "DELETE FROM Resource_index WHERE res_id = ?"


class VDOM_storage(object):
    """VDOM local database interface"""

    def __init__(self):
        
        """constructor"""
        self.__dir = settings.CACHE_LOCATION
        self.__fname = self.__dir + "/vdom.storage.db.sql"
        self.__sem = VDOM_semaphore()
        self.__queue = []
        if not self.init_db():
            raise VDOM_exception("Failed to initialize local server storage")
        # start write thread
        self.__daemon = None
        # check if need to write config_1
        if not VDOM_CONFIG["VDOM-CONFIG-1-RECORD"] in self.keys():
            self.write_object(VDOM_CONFIG["VDOM-CONFIG-1-RECORD"], VDOM_CONFIG_1)
        else:
            conf = self.read_object(VDOM_CONFIG["VDOM-CONFIG-1-RECORD"])
            for k in VDOM_CONFIG_1:
                if k not in conf:
                    conf[k] = VDOM_CONFIG_1[k]
                else:
                    VDOM_CONFIG_1[k] = conf[k]
            self.write_object(VDOM_CONFIG["VDOM-CONFIG-1-RECORD"], conf)


    def init_db(self):
        """open storage"""
        self.__sem.lock()
        try:
            conn = sqlite3.connect(self.__fname)
            # create storage table
            cur = conn.cursor()
            cur.execute("create table if not exists storage (name text, value text)")
            conn.close()
            return True
        except Exception as e:
            debug(str(e))
            return False
        finally:
            self.__sem.unlock()
            

    def __internal_write(self, key, value, cur=None): # Save file to storage (internal)
        """internal write method"""

        conn = None
        if not cur:
            conn = sqlite3.connect(self.__fname)
            cur = conn.cursor()

        if key == "createresindex":
            cur.execute(_create_sql)
        elif key == "clearresindex":
            cur.execute(_clear_sql)
        elif key == "deleteresindex":
            res_descriptor = value
            cur.execute(_delete_sql, (res_descriptor.id,))
        elif key == "saveresource":
            res_descriptor = value
            cur.execute(_save_sql, (res_descriptor.id, res_descriptor.application_id, res_descriptor.filename, res_descriptor.name, res_descriptor.res_type, res_descriptor.res_format))
        else:
            cur.execute("select count(value) from storage where name = ? limit 1", (key, ))
            if cur.fetchone()[0]:
                cur.execute("update storage set value = ? where name = ?", (value, key))
            else:
                cur.execute("insert into storage values (?, ?)", (key, value))
        if conn:
            conn.commit()

    def __internal_read(self, key):
        """internal read method"""
        with sqlite3.connect(self.__fname) as con:
            ret = con.execute("select value from storage where name = ?", (key, )).fetchone()
            return ret[0] if ret else None

    def __internal_keys(self):
        """internal read method"""
        with sqlite3.connect(self.__fname) as con:
            return [row[0] for row in con.execute("select name from storage")]

    def __internal_erase(self, key):
        """internal erase method"""
        with sqlite3.connect(self.__fname) as conn:
            conn.execute("delete from storage where name = ?", (key, ))
            #conn.commit() #

    def prepare(self):
        connection = sqlite3.connect(self.__fname)
        cursor = connection.cursor()
        return connection, cursor

    def work(self, connection, cursor):
        if self.__queue:
            try:
                self.__sem.lock()
                while self.__queue:
                    item = self.__queue.pop(0)
                    self.__internal_write(item[0], item[1], cursor)
                connection.commit()
            finally:
                self.__sem.unlock()

    def read(self, key):
        """read data from storage"""
        # self.__sem.lock()
        try:
            ret = self.__internal_read(key)
            return ret
        except Exception, e:
            debug("Read error, key '%s'" % str(key))
            debug(str(e))
            traceback.print_exc(file=debugfile)
        # finally:
        #	self.__sem.unlock()
        # return None

    def write(self, key, value):    
        """write data to storage"""
        self.__sem.lock()
        try:
            self.__internal_write(key, value)
            return True
        except Exception, e:
            debug("Write error, key '%s'" % str(key))
            debug(str(e))
            return False
        finally:
            self.__sem.unlock()

    def write_async(self, key, value): 
        """async write data to storage"""
        self.__sem.lock()
        if self.__daemon is None:
            self.__daemon = VDOM_storage_writer(self)
            self.__daemon.start()
        try:
            self.__queue.append((str(key), value))
            return True
        except Exception as e:
            debug(str(e))
            return False
        finally:
            self.__sem.unlock()

    def __execute_sql(self, sql, params):  # Temporary for debug only!!
        """execute sql to storage"""
        self.__sem.lock()
        try:
            conn = sqlite3.connect(self.__fname)
            cur = conn.cursor()
            cur.execute(sql, params)
            if conn:
                conn.commit()

            return cur.lastrowid or True

        except Exception, e:
            debug("SQL execute error")
            debug(str(e))
            return False
        finally:
            self.__sem.unlock()
        return True

    def __execute_sql_read(self, sql, params):  # Temporary for debug only!!
        """execute sql to storage"""
        # self.__sem.lock()
        try:
            return sqlite3.connect(self.__fname).execute(sql, params).fetchall()
        except Exception, e:
            debug("SQL execute read error")
            debug(str(e))
            return None
        # finally:
            # self.__sem.unlock()

    def make_resources_index(self):
        """Creation (if needed) index table for resources"""
        self.__internal_write("createresindex", ())
        return bool(self.__execute_sql_read("SELECT res_id FROM Resource_index LIMIT 1", ()))

    def clear_resources_index(self):
        """Creation (if needed) index table for resources"""
        self.__internal_write("clearresindex", ())

    def delete_resources_index(self, res_descriptor):
        """Creation (if needed) index table for resources"""
        self.write_async("deleteresindex", res_descriptor)

    def list_resource_index(self):
        """List resource records from DB"""
        return self.__execute_sql_read(_list_sql, ())

    def get_resource_record(self, res_descriptor):
        """Interface for access to DB records of resources"""
        rows = self.__execute_sql_read(list_all_res, (res_descriptor.id,))
        if len(rows) == 1:
            row = rows[0]
        else:
            raise VDOM_exception("Resource record (id = %s) not found" % res_descriptor.id)
        res_descriptor.filename = row[0]
        res_descriptor.name = row[1]
        res_descriptor.res_type = row[2]
        res_descriptor.res_format = row[3]

    def save_resource_record(self, res_descriptor):
        """Method for saving resources record to DB"""
        self.write_async("saveresource", res_descriptor)

    def create_resource_record(self, res_descriptor):
        """Interface for adding DB record of resources"""

        #params = (res_descriptor.id,res_descriptor.application_id,res_descriptor.filename,res_descriptor.name,res_descriptor.res_type,res_descriptor.res_format)
        #ret = self.__execute_sql(__insert_sql,params)
        # return ret if isinstance(ret,int) else None
        self.write_async("addresource", res_descriptor)

    def update_resource_record(self, res_descriptor):
        """Interface for updating DB record of resources"""
        #params = (res_descriptor.filename,res_descriptor.name,res_descriptor.res_type,res_descriptor.res_format,res_descriptor.res_id)
        #db_id = self.__execute_sql(__update_sql,params)
        # return db_id
        self.write_async("updateresource", res_descriptor)

    def erase(self, key):
        """remove data from storage"""
        self.__sem.lock()
        try:
            self.__internal_erase(key)
            return True
        finally:
            self.__sem.unlock()

    def __del__(self):
        """destructor"""
        pass

    def filename(self):
        """get db file name"""
        return self.__fname

    def keys(self):
        """get keys"""
        self.__sem.lock()
        ret = self.__internal_keys()
        self.__sem.unlock()
        return ret

###### object interface ############################################################################

    def read_object(self, key):
        """read object from the storage"""
        data = self.read(key)
        if not data:
            return None
        try:
            data = cPickle.loads(str(data))
            return data
        except Exception, e:
            debug("Error reading object '%s' from the storage" % str(key))
            debug(str(e))
            return None

    def write_object(self, key, object):    # Write object to the storage
        """save object to the storage"""
        data = None
        try:
            data = cPickle.dumps(object)
        except Exception, e:
            debug("Error writing object '%s' to the storage" % str(key))
            debug(str(e))
            return False
        return self.write(key, data)

    def write_object_async(self, key, object):  #suspect5
        """save object to the storage"""
        data = None
        try:
            data = cPickle.dumps(object)
        except Exception, e:
            debug("Error writing object '%s' to the storage" % str(key))
            debug(str(e))
            return False
        return self.write_async(key, data)


import managers


class VDOM_config:
    """class to read/save changeable config"""

    def get_opt(self, name):
        VDOM_named_mutex_auto(name)
        conf = managers.storage.read_object(VDOM_CONFIG["VDOM-CONFIG-1-RECORD"])
        if name in conf:
            return conf[name]
        return None

    def get_keys(self):
        conf = managers.storage.read_object(VDOM_CONFIG["VDOM-CONFIG-1-RECORD"])
        return conf.keys()

    def set_opt(self, name, val):
        VDOM_named_mutex_auto(name)
        conf = managers.storage.read_object(VDOM_CONFIG["VDOM-CONFIG-1-RECORD"])
        conf[name] = val
        managers.storage.write_object_async(VDOM_CONFIG["VDOM-CONFIG-1-RECORD"], conf)

    def set_opt_sync(self, name, val):
        VDOM_named_mutex_auto(name)
        conf = managers.storage.read_object(VDOM_CONFIG["VDOM-CONFIG-1-RECORD"])
        conf[name] = val
        managers.storage.write_object(VDOM_CONFIG["VDOM-CONFIG-1-RECORD"], conf)
