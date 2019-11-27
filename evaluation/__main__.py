import logging
from .gwn import GeoWebNewsEvaluator
from .samples import SampleEvaluator

logging.basicConfig(format='%(asctime)s %(message)s', 
                    level=logging.INFO, 
                    datefmt="%H:%M:%S")

evaluator = SampleEvaluator()  # GeoWebNewsEvaluator()
evaluator.start()
evaluator.test_osm_point()
#evaluator.test('100')
#evaluator.test_all(6)
evaluator.finish()
