from evaluation import GeoWebNewsEvaluator, T2MAnnotator

annotator = T2MAnnotator(update=True, keep_defaults=True)
evaluator = GeoWebNewsEvaluator(annotator)
evaluator.test_all()
#evaluator.test(185)
