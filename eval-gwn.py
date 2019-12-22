import logging
from evaluation import GeoWebNewsEvaluator

logging.basicConfig(format='%(asctime)s %(message)s',
                    level=logging.INFO,
                    datefmt="%H:%M:%S")

evaluator = GeoWebNewsEvaluator(persist=True)
evaluator.test_all(doc_range=range(50))
#evaluator.test(1)
