import queue
import unittest

from tourmap.utils import objpool


class NumberMaker(object):

    def __init__(self):
        self.counter = 0

    def cfn(self):
        self.counter += 1
        return self.counter


class TestObjectPool(unittest.TestCase):

    def test_pool_construction_with_maxsize(self):
        pool = objpool.ObjectPool(NumberMaker().cfn, maxsize=3)
        self.assertEqual(1, pool.get())
        self.assertEqual(2, pool.get())
        self.assertEqual(3, pool.get())
        with self.assertRaises(objpool.Empty):
            pool.get(timeout=0.01)

    def test_pool_construction_without_maxsize(self):
        pool = objpool.ObjectPool(NumberMaker().cfn)
        for x in range(1, 100):
            self.assertEqual(x, pool.get())

    def test_pool_construction_get_put_sequences(self):
        pool = objpool.ObjectPool(NumberMaker().cfn)
        for x in range(1, 100):
            self.assertEqual(x, pool.get())
        for x in range(1, 100):
            pool.put(x)
        self.assertEqual(99, pool.size())

    def test_pool_construction_just_one(self):
        pool = objpool.ObjectPool(NumberMaker().cfn)
        for _ in range(1, 100):
            obj = pool.get()
            self.assertEqual(1, obj)
            pool.put(obj)
        self.assertEqual(1, pool.size())

    def test_pool_is_lifo_style(self):
        pool = objpool.ObjectPool(NumberMaker().cfn, maxsize=2)
        self.assertEqual(1, pool.get())
        self.assertEqual(2, pool.get())
        pool.put(1)
        pool.put(2)
        self.assertEqual(2, pool.get())

    def test_pool_error_when_using_put_on_full_pool(self):
        pool = objpool.ObjectPool(NumberMaker().cfn, maxsize=2)
        with self.assertRaises(queue.Full):
            pool.put(objpool._PlaceHolder)

    def test_ctx_manager(self):
        pool = objpool.ObjectPool(NumberMaker().cfn, maxsize=2)

        with pool.use() as obj1:
            self.assertEqual(1, obj1)

        with pool.use() as obj1:
            self.assertEqual(1, obj1)

        with pool.use() as obj1:
            self.assertEqual(1, obj1)
            with pool.use() as obj2:
                self.assertEqual(2, obj2)

        with pool.use() as obj1:
            self.assertEqual(1, obj1)

        with pool.use() as obj1:
            with pool.use() as obj2:
                with self.assertRaises(objpool.Empty):
                    with pool.use(block=False) as obj3:
                        self.assertEqual(3, obj3)
