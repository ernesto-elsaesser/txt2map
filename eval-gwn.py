from evaluation import GeoWebNewsEvaluator

evaluator = GeoWebNewsEvaluator(load_previous=False)
#evaluator.test_all(doc_range=range(50))
evaluator.test(30)
