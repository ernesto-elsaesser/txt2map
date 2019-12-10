import logging
from evaluation import GeoWebNewsEvaluator

logging.basicConfig(format='%(asctime)s %(message)s', 
                    level=logging.INFO, 
                    datefmt="%H:%M:%S")

evaluator = GeoWebNewsEvaluator(True)
evaluator.test_all(max_documents=10)
#evaluator.test('213') # TODO: check!
#evaluator.test('195') # TODO: verify!
