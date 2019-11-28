import logging
from .gwn import GeoWebNewsEvaluator
from .tests import TestEvaluator

logging.basicConfig(format='%(asctime)s %(message)s', 
                    level=logging.INFO, 
                    datefmt="%H:%M:%S")

evaluator = TestEvaluator()
evaluator.test_all()

#evaluator = GeoWebNewsEvaluator()
#evaluator.start()
#evaluator.test('100')
#evaluator.test_all(6)
#evaluator.finish()
