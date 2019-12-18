import logging
from evaluation import GeoWebNewsEvaluator

logging.basicConfig(format='%(asctime)s %(message)s',
                    level=logging.INFO,
                    datefmt="%H:%M:%S")

evaluator = GeoWebNewsEvaluator()
evaluator.test_all()
#evaluator.test(6)
