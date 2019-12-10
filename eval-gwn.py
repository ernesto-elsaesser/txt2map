import logging
from evaluation import GeoWebNewsEvaluator

logging.basicConfig(format='%(asctime)s %(message)s', 
                    level=logging.INFO, 
                    datefmt="%H:%M:%S")

evaluator = GeoWebNewsEvaluator(True)
evaluator.test_all(doc_range=range(100, 150))
#evaluator.test('123')
#print(evaluator.eval.report_csv())

# 0, 1, 2, 132
