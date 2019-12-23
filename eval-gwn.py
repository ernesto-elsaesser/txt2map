from evaluation import GeoWebNewsEvaluator

evaluator = GeoWebNewsEvaluator(load_previous=True, keep_defaults=True)
evaluator.test_all()
#evaluator.test(30)
