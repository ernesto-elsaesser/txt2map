import logging
from .gwn import GeoWebNewsEvaluator
from .tests import TestEvaluator

logging.basicConfig(format='%(asctime)s %(message)s', 
                    level=logging.INFO, 
                    datefmt="%H:%M:%S")

#evaluator = TestEvaluator()
#evaluator.test_all()

evaluator = GeoWebNewsEvaluator(True)
#evaluator.test_all(max_documents=100)
#evaluator.test('213')
evaluator.test('195')
