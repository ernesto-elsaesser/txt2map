from evaluation import GeoWebNewsEvaluator

evaluator = GeoWebNewsEvaluator(load_previous=True)
evaluator.test_all()
#evaluator.test(30)
