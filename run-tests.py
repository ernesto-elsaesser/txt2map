import logging
from evaluation import TestEvaluator

logging.basicConfig(format='%(asctime)s %(message)s', 
                    level=logging.INFO, 
                    datefmt="%H:%M:%S")

evaluator = TestEvaluator()
evaluator.test_all()
