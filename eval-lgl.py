import logging
from evaluation import LGLEvaluator

logging.basicConfig(format='%(asctime)s %(message)s',
                    level=logging.INFO,
                    datefmt="%H:%M:%S")

evaluator = LGLEvaluator()
#evaluator.test_all(doc_range=range(10))
evaluator.test(1)
