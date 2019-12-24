from evaluation import GeoWebNewsEvaluator, T2MAnnotator

annotator = T2MAnnotator(update=True, keep_defaults=False)
evaluator = GeoWebNewsEvaluator(annotator)
evaluator.test_all(doc_range=range(10))
#evaluator.test(30)
