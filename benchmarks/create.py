from redisco import get_client
import timeit
from common import Event


def create_events():
    Event(name="Redis Meetup 1", location="London").save()


def load_events():
    Event.objects.get_by_id(1).name


def find_events():
    Event.objects.filter(name="Redis Meetup", location="London").first()


def display_results(results, name):
    print("%s: 5000 Loops, best of 3: %.02f sec" % (name, min(results)))


def profile():
    import cProfile
    import pstats
    stmt = """
for x in xrange(0, 5000):
    find_events()
    """
    cProfile.run(stmt, "b33f.prof")
    p = pstats.Stats("b33f.prof")
    p.strip_dirs().sort_stats('cumulative').print_stats(20)


db = get_client()
db.flushdb()
Event(name="Redis Meetup 1", location="London").save()

t = timeit.Timer('create_events()', 'from __main__ import create_events')
display_results(t.repeat(repeat=1, number=5000), 'create_events')

t = timeit.Timer('find_events()', 'from __main__ import find_events')
display_results(t.repeat(repeat=1, number=5000), 'find_events')

t = timeit.Timer('load_events()', 'from __main__ import load_events')
display_results(t.repeat(repeat=1, number=5000), 'load_events')
