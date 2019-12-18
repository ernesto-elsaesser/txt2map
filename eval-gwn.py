import logging
from evaluation import GeoWebNewsEvaluator

logging.basicConfig(format='%(asctime)s %(message)s',
                    level=logging.INFO,
                    datefmt="%H:%M:%S")

evaluator = GeoWebNewsEvaluator(include_rec=True)
evaluator.test_all()
#evaluator.test(64)
