import sys
sys.path[0:0] = [""]

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import datetime

import pymongo
from bson.tz_util import utc

from mongoengine import (
    connect, register_connection,
    Document, DateTimeField
)
import mongoengine.connection
from mongoengine.connection import get_db, get_connection, ConnectionError


class ConnectionTest(unittest.TestCase):

    def tearDown(self):
        mongoengine.connection._connection_settings = {}
        mongoengine.connection._connections = {}
        mongoengine.connection._dbs = {}

    def test_connect(self):
        """Ensure that the connect() method works properly.
        """
        connect('mongoenginetest')

        conn = get_connection()
        self.assertTrue(isinstance(conn, pymongo.mongo_client.MongoClient))

        db = get_db()
        self.assertTrue(isinstance(db, pymongo.database.Database))
        self.assertEqual(db.name, 'mongoenginetest')

        connect('mongoenginetest2', alias='testdb')
        conn = get_connection('testdb')
        self.assertTrue(isinstance(conn, pymongo.mongo_client.MongoClient))

    def test_sharing_connections(self):
        """Ensure that connections are shared when the connection settings are exactly the same
        """
        connect('mongoenginetest', alias='testdb1')

        expected_connection = get_connection('testdb1')

        connect('mongoenginetest', alias='testdb2')
        actual_connection = get_connection('testdb2')
        self.assertEqual(expected_connection, actual_connection)

    def test_connect_uri(self):
        """Ensure that the connect() method works properly with uri's
        """
        c = connect(db='mongoenginetest', alias='admin')
        c.admin.system.users.remove({})
        c.mongoenginetest.system.users.remove({})

        c.admin.add_user("admin", "password")
        c.admin.authenticate("admin", "password")
        c.mongoenginetest.add_user("username", "password")

        self.assertRaises(ConnectionError, connect, "testdb_uri_bad", host='mongodb://test:password@localhost')

        connect("testdb_uri", host='mongodb://username:password@localhost/mongoenginetest')

        conn = get_connection()
        self.assertTrue(isinstance(conn, pymongo.mongo_client.MongoClient))

        db = get_db()
        self.assertTrue(isinstance(db, pymongo.database.Database))
        self.assertEqual(db.name, 'mongoenginetest')

        c.admin.system.users.remove({})
        c.mongoenginetest.system.users.remove({})

    def test_connect_uri_without_db(self):
        """Ensure that the connect() method works properly with uri's
        without database_name
        """
        c = connect(db='mongoenginetest', alias='admin')
        c.admin.system.users.remove({})
        c.mongoenginetest.system.users.remove({})

        c.admin.add_user("admin", "password")
        c.admin.authenticate("admin", "password")
        c.mongoenginetest.add_user("username", "password")

        self.assertRaises(ConnectionError, connect, "testdb_uri_bad", host='mongodb://test:password@localhost')

        connect("mongoenginetest", host='mongodb://localhost/')

        conn = get_connection()
        self.assertTrue(isinstance(conn, pymongo.mongo_client.MongoClient))

        db = get_db()
        self.assertTrue(isinstance(db, pymongo.database.Database))
        self.assertEqual(db.name, 'mongoenginetest')

        c.admin.system.users.remove({})
        c.mongoenginetest.system.users.remove({})

    def test_connect_uri_with_authsource(self):
        """Ensure that the connect() method works well with
        the option `authSource` in URI.
        """
        # Create users
        c = connect('mongoenginetest')
        c.admin.system.users.remove({})
        c.admin.add_user('username', 'password')

        # Authentication fails without "authSource"
        self.assertRaises(
            ConnectionError, connect, 'mongoenginetest', alias='test1',
            host='mongodb://username:password@localhost/mongoenginetest'
        )
        self.assertRaises(ConnectionError, get_db, 'test1')

        # Authentication succeeds with "authSource"
        connect(
            'mongoenginetest', alias='test2',
            host=('mongodb://username:password@localhost/'
                  'mongoenginetest?authSource=admin')
        )
        db = get_db('test2')
        self.assertTrue(isinstance(db, pymongo.database.Database))
        self.assertEqual(db.name, 'mongoenginetest')

        # Clear all users
        c.admin.system.users.remove({})

    def test_register_connection(self):
        """Ensure that connections with different aliases may be registered.
        """
        register_connection('testdb', 'mongoenginetest2')

        self.assertRaises(ConnectionError, get_connection)
        conn = get_connection('testdb')
        self.assertTrue(isinstance(conn, pymongo.mongo_client.MongoClient))

        db = get_db('testdb')
        self.assertTrue(isinstance(db, pymongo.database.Database))
        self.assertEqual(db.name, 'mongoenginetest2')

    def test_register_connection_defaults(self):
        """Ensure that defaults are used when the host and port are None.
        """
        register_connection('testdb', 'mongoenginetest', host=None, port=None)

        conn = get_connection('testdb')
        self.assertTrue(isinstance(conn, pymongo.mongo_client.MongoClient))

    def test_connection_kwargs(self):
        """Ensure that connection kwargs get passed to pymongo.
        """
        connect('mongoenginetest', alias='t1', tz_aware=True)
        conn = get_connection('t1')

        self.assertTrue(conn.tz_aware)

        connect('mongoenginetest2', alias='t2')
        conn = get_connection('t2')
        self.assertFalse(conn.tz_aware)

    def test_datetime(self):
        connect('mongoenginetest', tz_aware=True)
        d = datetime.datetime(2010, 5, 5, tzinfo=utc)

        class DateDoc(Document):
            the_date = DateTimeField(required=True)

        DateDoc.drop_collection()
        DateDoc(the_date=d).save()

        date_doc = DateDoc.objects.first()
        self.assertEqual(d, date_doc.the_date)

    def test_multiple_connection_settings(self):
        connect('mongoenginetest', alias='t1', host="localhost")

        connect('mongoenginetest2', alias='t2', host="127.0.0.1")

        mongo_connections = mongoengine.connection._connections
        self.assertEqual(len(mongo_connections.items()), 2)
        self.assertTrue('t1' in mongo_connections.keys())
        self.assertTrue('t2' in mongo_connections.keys())
        self.assertEqual(mongo_connections['t1'].host, 'localhost')
        self.assertEqual(mongo_connections['t2'].host, '127.0.0.1')


if __name__ == '__main__':
    unittest.main()
