"""
A very thin wrapper around queue.LifoQueue providing
thread safe object pool functionality.
"""
try:
    import queue
except ImportError:
    import Queue as queue


class Empty(queue.Empty):
    """objpool.Empty is raised when block and/or timeout are set."""
    pass


_PlaceHolder = object()


class ObjectPool(object):

    def __init__(self, cfn, maxsize=0):

        self.__cfn = cfn
        self.__pool = queue.LifoQueue(maxsize=maxsize)
        self.__maxsize = maxsize

        # Pre-populate the pool with None objects if a max_size
        # is provided - this allows us to construct new objects
        # without the need of keeping a counter how many we have
        # already constructed...
        if self.__maxsize:
            for _ in range(self.__maxsize):
                self.__pool.put_nowait(_PlaceHolder)

    def get(self, block=True, timeout=None):
        """
        Get an instance from this pool, optionally constructing one
        if the pool is empty and maxsize has not been reached yet.

        :param block: as for queue.Queue. Note, a pool with an unset
                      maxsize never blocks. It will always construct
                      a new object for you.
        :param timeout: How long to wait in the case of an empty pool.
                        None will wait forever.
        """
        return self._get(block=block, timeout=timeout)

    def put(self, obj):
        return self._put(obj)

    def use(self, block=True, timeout=None):
        """
        For use with the with statement.

            with pool.use() as client:
                response = client.request("/users/123")
        """
        class _CtxManager(object):
            def __init__(self, obj, pool):
                self.__pool = pool
                self.__obj = obj

            def __enter__(self):
                return self.__obj

            def __exit__(self, exc_type, exc_value, traceback):
                self.__pool.put(self.__obj)

        obj = self.get(block=block, timeout=timeout)
        return _CtxManager(obj, self.__pool)

    def size(self):
        """
        Just forward to the underlying LifoQueue. The size may change
        at anytime.
        """
        return self.__pool.qsize()

    def _get(self, block=True, timeout=None):
        try:
            obj = self.__pool.get_nowait()
            # We are allowed to create a new instance if the pool
            # returned the PlaceHolder object without any checks.
            if obj is _PlaceHolder:
                return self.__cfn()
            return obj

        except queue.Empty:
            # If the pool was empty and no maxsize is set, we can
            # also just create a new instance.
            if not self.__maxsize:
                return self.__cfn()

        # In all other cases, we have to wait for someone else to
        # put back a previously created instance.
        try:
            return self.__pool.get(block=block, timeout=timeout)
        except queue.Empty:
            raise Empty()

    def _put(self, obj):
        """
        Put an object back into this pool. This may raise queue.Full,
        but then the user screwed up.
        """
        self.__pool.put_nowait(obj)
