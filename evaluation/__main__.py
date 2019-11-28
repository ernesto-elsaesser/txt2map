import logging
from .gwn import GeoWebNewsEvaluator
from .tests import TestEvaluator

logging.basicConfig(format='%(asctime)s %(message)s', 
                    level=logging.INFO, 
                    datefmt="%H:%M:%S")

#evaluator = TestEvaluator()
#valuator.test_all()

evaluator = GeoWebNewsEvaluator()
#evaluator.test_all(6)
evaluator.test('128')
