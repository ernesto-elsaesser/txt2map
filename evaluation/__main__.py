import logging
from .gwn import GeoWebNewsEvaluator

logging.basicConfig(format='%(asctime)s %(message)s', 
                    level=logging.INFO, 
                    datefmt="%H:%M:%S")

evaluator = GeoWebNewsEvaluator()
evaluator.start()
#evaluator.test('100')
evaluator.test_all(6)
evaluator.finish()
