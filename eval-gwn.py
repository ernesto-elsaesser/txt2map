from evaluation import GeoWebNewsEvaluator, T2MAnnotator

annotator = T2MAnnotator(update=False, keep_defaults=False)
evaluator = GeoWebNewsEvaluator(annotator)
evaluator.test_all()
#evaluator.test(30)
