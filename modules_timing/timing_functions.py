import time
import types

def time_all_functions(module):
    """
    Wraps all functions in a module to print execution time.
    """
    for name in dir(module):
        obj = getattr(module, name)
        if isinstance(obj, types.FunctionType):
            setattr(module, name, timeit(obj))

def timeit(func):
    """
    Decorator that prints execution time of a function.
    """
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"[{func.__name__}] Elapsed time: {elapsed:.2f} seconds")
        return result
    return wrapper