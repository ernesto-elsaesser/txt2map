from evaluation import GeoWebNewsEvaluator

evaluator = GeoWebNewsEvaluator(persist=False)
evaluator.test_all(doc_range=range(50))
#evaluator.test(1)
